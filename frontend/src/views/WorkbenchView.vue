<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  api,
  assetUrl,
  percent,
  post,
  newKey,
  fmtTime,
  sourceLabels,
  decisionLabels,
  statusLabels,
  loadPredictions,
  type ImageAsset,
  type Prediction,
  type Task,
  type Capabilities,
  type Report,
  type Annotation,
} from "../api/client";
import { useProject } from "../composables/project";
import { useAction } from "../composables/actions";
import ImageViewer from "../workbench/ImageViewer.vue";
import ResultStatistics from "../workbench/ResultStatistics.vue";
import LocationMap, { type Locations } from "../components/LocationMap.vue";
import AppIcon from "../components/AppIcon.vue";
import { filterResults, resultDay } from "../workbench/results";
const route = useRoute(),
  router = useRouter(),
  client = useQueryClient(),
  { session, canAnalyze, canReview, canReport } = useProject(),
  { busy, run } = useAction();
const imageId = computed(() => String(route.params.imageId)),
  viewer = ref<InstanceType<typeof ImageViewer>>();
const { data: image, error: imageError } = useQuery({
  queryKey: computed(() => ["image", imageId.value]),
  queryFn: () => api<ImageAsset>(`/images/${imageId.value}`),
});
watch(
  image,
  (i) => {
    if (i && session.projectId !== i.project_id)
      session.chooseProject(i.project_id);
  },
  { immediate: true },
);
const { data: results, error: resultsError } = useQuery({
  queryKey: computed(() => ["predictions", imageId.value]),
  queryFn: () => loadPredictions(imageId.value),
  refetchInterval: 2000,
});
const { data: capabilities } = useQuery({
  queryKey: ["capabilities"],
  queryFn: () => api<Capabilities>("/system/capabilities"),
  refetchInterval: 15000,
});
const selected = ref(String(route.query.prediction || "")),
  comparison = ref(""),
  strategy = ref<"single_view" | "tta4">(
    route.query.strategy === "single_view" ? "single_view" : "tta4",
  ),
  source = ref("historical_replay");
watch(
  () => image.value?.id,
  () => {
    if (image.value)
      source.value = image.value.available_strategies.length
        ? "historical_replay"
        : "live_inference";
  },
  { immediate: true },
);
const lastTask = ref(String(route.query.task || "")),
  autoSelected = ref("");
watch(
  results,
  (rows) => {
    const completed = rows?.find((p) => p.task_id === lastTask.value);
    if (completed && autoSelected.value !== completed.id) {
      selected.value = completed.id;
      autoSelected.value = completed.id;
      showParameters("visualise");
    } else if (rows?.length && !rows.some((p) => p.id === selected.value))
      selected.value = rows[0].id;
  },
  { immediate: true },
);
const prediction = computed(() =>
    results.value?.find((p) => p.id === selected.value),
  ),
  comparePrediction = computed(() =>
    results.value?.find((p) => p.id === comparison.value),
  );
const mode = ref("overlay"),
  layer = ref("prediction"),
  opacity = ref(65),
  swipe = ref(50);
const annotations = ref<Annotation[]>([]),
  note = ref(""),
  decision = ref("confirmed"),
  baseRevision = ref(0);
watch(
  () => prediction.value?.id,
  () => {
    const p = prediction.value;
    baseRevision.value = p?.review_revision || 0;
    annotations.value = p?.reviews[0]?.annotations.map((a) => ({ ...a })) || [];
    decision.value = p?.reviews[0]?.decision || "confirmed";
    note.value = "";
    layer.value = p ? "prediction" : "original";
  },
  { immediate: true },
);
const pixel = ref<{
  x: number;
  y: number;
  rgb: number[];
  predicted: boolean;
  label: number | null;
  valid: boolean;
} | null>(null);
async function submit() {
  await run(async () => {
    const task = await post<Task>(
      "/analysis-tasks",
      {
        image_id: imageId.value,
        mode: source.value,
        strategy: strategy.value,
        model_version: "long_bce_lovasz",
      },
      newKey(),
    );
    lastTask.value = task.id;
    await router.replace({ query: { ...route.query, task: task.id } });
    await client.invalidateQueries({ queryKey: ["tasks"] });
  }, "任务已入队，完成后结果自动显示");
}
async function queryPixel(point: [number, number]) {
  const id = prediction.value?.id;
  if (id)
    await run(async () => {
      const result = await api<NonNullable<typeof pixel.value>>(
        `/predictions/${id}/pixel?x=${point[0]}&y=${point[1]}`,
      );
      if (prediction.value?.id === id) pixel.value = result;
    });
}
async function saveReview() {
  await run(async () => {
    if (!note.value.trim()) throw new Error("请填写复核依据");
    await post(`/predictions/${prediction.value!.id}/reviews`, {
      base_revision: baseRevision.value,
      decision: decision.value,
      note: note.value,
      annotations: annotations.value,
    });
    baseRevision.value += 1;
    note.value = "";
    await client.invalidateQueries({
      queryKey: ["predictions", imageId.value],
    });
    await client.invalidateQueries({ queryKey: ["projects"] });
  }, "复核版本已保存");
}
async function report() {
  await run(async () => {
    await post<Report>(
      "/reports",
      {
        prediction_id: prediction.value!.id,
        review_revision: prediction.value!.review_revision,
      },
      newKey(),
    );
    await client.invalidateQueries({ queryKey: ["reports"] });
    router.push("/reports");
  }, "报告快照已固定，正在生成");
}
const importOpen = ref(false),
  importMask = ref<File | null>(null),
  importMetadata = ref("");
function openImport() {
  importOpen.value = true;
  importMask.value = null;
  importMetadata.value = JSON.stringify(
    {
      input_sha256: image.value?.input_sha256,
      mask_sha256: "填写掩膜文件的 SHA256",
      width: image.value?.width,
      height: image.value?.height,
      model_version: "external-model",
      strategy: "single_view",
      preprocess_version: "external-v1",
      threshold: 0,
      source: "填写外部来源和生成说明",
    },
    null,
    2,
  );
}
async function setMask(event: Event) {
  importMask.value = (event.target as HTMLInputElement).files?.[0] || null;
  if (importMask.value) {
    const buffer = await crypto.subtle.digest(
      "SHA-256",
      await importMask.value.arrayBuffer(),
    );
    try {
      const meta = JSON.parse(importMetadata.value);
      meta.mask_sha256 = Array.from(new Uint8Array(buffer))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
      importMetadata.value = JSON.stringify(meta, null, 2);
    } catch {
      /* user is editing */
    }
  }
}
async function importResult() {
  await run(async () => {
    if (!importMask.value) throw new Error("请选择二值掩膜");
    const form = new FormData();
    form.append("mask", importMask.value);
    form.append("metadata", importMetadata.value);
    const task = await api<Task>(`/images/${imageId.value}/import-result`, {
      method: "POST",
      body: form,
      headers: { "Idempotency-Key": newKey() },
    });
    lastTask.value = task.id;
    await router.replace({ query: { ...route.query, task: task.id } });
    await client.invalidateQueries({ queryKey: ["tasks"] });
    importOpen.value = false;
  }, "外部结果已入队校验");
}
const leftTab = ref("visualise"),
  activeTool = ref(""),
  panelCollapsed = ref(false),
  resultSource = ref("all"),
  resultDate = ref("");
const filteredResults = computed(() =>
  filterResults(results.value || [], resultSource.value, resultDate.value),
);
const selectedOutsideFilter = computed(
  () =>
    !!prediction.value &&
    !filteredResults.value.some((p) => p.id === selected.value),
);
const imageLocations = computed<Locations>(() => ({
  type: "FeatureCollection",
  features: image.value?.location
    ? [
        {
          type: "Feature",
          id: image.value.id,
          geometry: {
            type: "Point",
            coordinates: [
              image.value.location.longitude,
              image.value.location.latitude,
            ],
          },
          properties: {
            ...image.value.location,
            sample_id: image.value.sample_id,
          },
        },
      ]
    : [],
}));
const tools = [
  { id: "location", icon: "pin", label: "GPS 定位" },
  { id: "statistics", icon: "chart", label: "统计分析" },
  { id: "region", icon: "region", label: "区域选择" },
  { id: "review", icon: "review", label: "人工复核" },
  { id: "info", icon: "info", label: "来源详情" },
];
const toolTitle = computed(
  () => tools.find((t) => t.id === activeTool.value)?.label,
);
function toggleTool(id: string) {
  panelCollapsed.value = false;
  activeTool.value = activeTool.value === id ? "" : id;
}
function showParameters(tab: string) {
  activeTool.value = "";
  leftTab.value = tab;
  panelCollapsed.value = false;
}
function stepResult(direction: number) {
  const rows = filteredResults.value;
  const index = rows.findIndex((p) => p.id === selected.value);
  const next = rows[index + direction];
  if (index >= 0 && next) selected.value = next.id;
}
const resultIndex = computed(() =>
  filteredResults.value.findIndex((p) => p.id === selected.value),
);
function drawRegion() {
  mode.value = "overlay";
  viewer.value?.startDrawing();
}
function resetFilters() {
  resultDate.value = "";
  resultSource.value = "all";
}
watch(selected, () => {
  pixel.value = null;
  viewer.value?.stopDrawing();
  if (selected.value && results.value?.some((p) => p.id === selected.value)) {
    const query = { ...route.query };
    if (
      results.value.find((p) => p.id === selected.value)?.task_id ===
      lastTask.value
    )
      delete query.task;
    void router.replace({ query: { ...query, prediction: selected.value } });
  }
});
watch(
  () => route.query.prediction,
  (id) => {
    if (id) selected.value = String(id);
  },
);
watch(imageId, () => {
  selected.value = String(route.query.prediction || "");
  comparison.value = "";
  lastTask.value = String(route.query.task || "");
  autoSelected.value = "";
  strategy.value =
    route.query.strategy === "single_view" ? "single_view" : "tta4";
  importOpen.value = false;
  resetFilters();
});
const terminal = ["SUCCEEDED", "FAILED", "CANCELED"];
const { data: taskState, error: taskError } = useQuery({
  queryKey: computed(() => ["task", lastTask.value]),
  enabled: computed(() => !!lastTask.value),
  queryFn: () => api<Task>(`/analysis-tasks/${lastTask.value}`),
  refetchInterval: (query) =>
    terminal.includes(query.state.data?.status || "") ? false : 1500,
});
watch(
  () => taskState.value?.status,
  (status) => {
    if (status && terminal.includes(status)) {
      void client.invalidateQueries({
        queryKey: ["predictions", imageId.value],
      });
      void client.invalidateQueries({ queryKey: ["projects"] });
    }
  },
);
async function taskAction(action: "cancel" | "retry") {
  await run(async () => {
    const task = await post<Task>(
      `/analysis-tasks/${lastTask.value}/${action}`,
      undefined,
      action === "retry" ? newKey() : undefined,
    );
    lastTask.value = task.id;
    await router.replace({ query: { ...route.query, task: task.id } });
    await client.invalidateQueries({ queryKey: ["task", task.id] });
    await client.invalidateQueries({ queryKey: ["tasks"] });
  });
}
</script>
<template>
  <div
    class="geo-workspace"
    :class="{ 'parameters-collapsed': panelCollapsed }"
  >
    <aside
      class="parameter-panel"
      aria-label="影像参数面板"
      v-show="!panelCollapsed"
    >
      <div class="parameter-heading">
        <div>
          <h1>解译工作台</h1>
        </div>
        <button
          class="icon-button on-blue"
          aria-label="收起参数面板"
          title="收起参数面板"
          @click="panelCollapsed = true"
        >
          <AppIcon name="left" />
        </button>
      </div>
      <div class="parameter-tabs" role="tablist" aria-label="工作台参数">
        <button
          role="tab"
          :aria-selected="!activeTool && leftTab === 'visualise'"
          :class="{ active: !activeTool && leftTab === 'visualise' }"
          @click="showParameters('visualise')"
        >
          <AppIcon name="layers" :size="17" />可视化
        </button>
        <button
          role="tab"
          :aria-selected="!activeTool && leftTab === 'analyse'"
          :class="{ active: !activeTool && leftTab === 'analyse' }"
          @click="showParameters('analyse')"
        >
          <AppIcon name="settings" :size="17" />分析设置
        </button>
        <button
          role="tab"
          :aria-selected="activeTool === 'statistics'"
          :class="{ active: activeTool === 'statistics' }"
          @click="activeTool = 'statistics'"
        >
          <AppIcon name="chart" :size="18" />统计
        </button>
        <button
          role="tab"
          :aria-selected="activeTool === 'review' || activeTool === 'region'"
          :class="{
            active: activeTool === 'review' || activeTool === 'region',
          }"
          @click="activeTool = 'review'"
        >
          <AppIcon name="review" :size="18" />复核
        </button>
      </div>
      <div v-if="!activeTool" class="parameter-scroll">
        <section class="parameter-section scene-section">
          <div class="scene-overview">
            <img
              v-if="image"
              :src="assetUrl(image.thumbnail_asset_id)"
              alt="当前影像缩略图"
            />
            <div>
              <strong class="scene-name">{{
                image?.name || "正在加载影像…"
              }}</strong>
              <div class="scene-meta">
                <span>{{ image?.split || "—" }}</span
                ><span>{{ image?.width }} × {{ image?.height }} px</span>
              </div>
            </div>
            <router-link
              to="/images"
              class="icon-button"
              title="切换影像"
              aria-label="切换影像"
              ><AppIcon name="images"
            /></router-link>
            <button
              class="icon-button"
              title="影像信息"
              aria-label="查看影像信息"
              @click="toggleTool('info')"
            >
              <AppIcon name="info" />
            </button>
          </div>
          <p v-if="imageError || resultsError" class="error" role="alert">
            {{ imageError?.message || resultsError?.message }}
          </p>
          <div v-if="lastTask" class="task-status" aria-label="当前分析任务">
            <span>{{
              taskState ? statusLabels[taskState.status] : "读取任务…"
            }}</span>
            <router-link :to="`/tasks?task=${lastTask}`"
              >阶段日志 ↗</router-link
            >
            <p v-if="taskError || taskState?.error" class="error" role="alert">
              {{ taskError?.message || taskState?.error?.message }}
            </p>
            <template v-if="canAnalyze && taskState">
              <el-button
                v-if="!terminal.includes(taskState.status)"
                size="small"
                :loading="busy"
                :disabled="taskState.status === 'CANCEL_REQUESTED'"
                @click="taskAction('cancel')"
                >取消任务</el-button
              >
              <el-button
                v-if="
                  ['FAILED', 'CANCELED'].includes(taskState.status) &&
                  taskState.attempt < 3
                "
                size="small"
                :loading="busy"
                @click="taskAction('retry')"
                >重试任务</el-button
              >
            </template>
          </div>
        </section>
        <div
          v-if="leftTab === 'visualise'"
          role="tabpanel"
          aria-label="可视化参数"
        >
          <section class="parameter-section">
            <div class="section-heading">
              <span><AppIcon name="calendar" :size="18" />结果筛选</span
              ><button class="text-button" @click="resetFilters">
                重置筛选
              </button>
            </div>
            <div class="filter-grid">
              <label class="filter-field" for="result-date"
                ><span>生成日期</span
                ><input
                  id="result-date"
                  v-model="resultDate"
                  class="date-field"
                  type="date"
                  aria-label="筛选结果日期"
              /></label>
              <label class="filter-field"
                ><span>数据来源</span
                ><el-select v-model="resultSource" aria-label="筛选数据来源"
                  ><el-option label="全部数据来源" value="all" /><el-option
                    v-for="(label, key) in sourceLabels"
                    :key="key"
                    :value="key"
                    :label="label" /></el-select
              ></label>
            </div>
            <div class="section-heading result-heading">
              <span><AppIcon name="layers" :size="18" />结果版本</span
              ><span class="count-badge">{{ filteredResults.length }} 个</span>
            </div>
            <div class="result-list" aria-label="结果版本列表">
              <button
                v-for="p in filteredResults"
                :key="p.id"
                class="result-option"
                :class="{ selected: selected === p.id }"
                :aria-pressed="selected === p.id"
                @click="selected = p.id"
              >
                <span class="result-radio" /><span class="result-copy"
                  ><strong
                    >{{
                      p.contract.strategy === "tta4" ? "四视图增强" : "单视图"
                    }}
                    <small>{{
                      sourceLabels[p.contract.source_mode]
                    }}</small></strong
                  ><span
                    >{{ resultDay(p.created_at) }}
                    <span class="mono">/ {{ p.id.slice(0, 8) }}</span></span
                  ></span
                >
              </button>
            </div>
            <p v-if="!filteredResults.length" class="field-hint">
              {{
                results?.length
                  ? "没有符合筛选条件的结果。"
                  : "暂无结果，请在「分析设置」中提交任务。"
              }}
            </p>
            <p v-if="selectedOutsideFilter" class="filter-notice">
              当前版本不在筛选范围内。
            </p>
          </section>
          <section class="parameter-section">
            <div class="section-heading">
              <span><AppIcon name="images" :size="17" />图层显示</span>
            </div>
            <div class="layer-options">
              <button
                :class="{ active: layer === 'original' }"
                :aria-pressed="layer === 'original'"
                @click="layer = 'original'"
              >
                <span class="layer-swatch original"
                  ><img
                    v-if="image"
                    class="layer-base"
                    :src="assetUrl(image.thumbnail_asset_id)"
                    alt="" /></span
                ><span>原始影像</span>
              </button>
              <button
                :disabled="!prediction"
                :class="{ active: layer === 'prediction' }"
                :aria-pressed="layer === 'prediction'"
                @click="layer = 'prediction'"
              >
                <span class="layer-swatch prediction"
                  ><img
                    v-if="image"
                    class="layer-base"
                    :src="assetUrl(image.thumbnail_asset_id)"
                    alt="" /><img
                    v-if="prediction?.layer_asset_id"
                    class="layer-overlay"
                    :src="assetUrl(prediction?.layer_asset_id!)"
                    alt="" /></span
                ><span>预测图层</span>
              </button>
              <button
                :disabled="!prediction?.gt_layer_asset_id"
                :class="{ active: layer === 'reference' }"
                :aria-pressed="layer === 'reference'"
                @click="layer = 'reference'"
              >
                <span class="layer-swatch reference"
                  ><img
                    v-if="image"
                    class="layer-base"
                    :src="assetUrl(image.thumbnail_asset_id)"
                    alt="" /><img
                    v-if="prediction?.gt_layer_asset_id"
                    class="layer-overlay"
                    :src="assetUrl(prediction?.gt_layer_asset_id!)"
                    alt="" /></span
                ><span>参考标签</span>
              </button>
              <button
                :disabled="!prediction?.difference_asset_id"
                :class="{ active: layer === 'difference' }"
                :aria-pressed="layer === 'difference'"
                @click="layer = 'difference'"
              >
                <span class="layer-swatch difference"
                  ><img
                    v-if="image"
                    class="layer-base"
                    :src="assetUrl(image.thumbnail_asset_id)"
                    alt="" /><img
                    v-if="prediction?.difference_asset_id"
                    class="layer-overlay"
                    :src="assetUrl(prediction?.difference_asset_id!)"
                    alt="" /></span
                ><span>误差分布</span>
              </button>
            </div>
            <div class="slider-label">
              <span>图层不透明度</span><span>{{ opacity }}%</span>
            </div>
            <el-slider
              v-model="opacity"
              :disabled="layer === 'original'"
              aria-label="图层透明度"
            />
          </section>
          <section class="parameter-section">
            <div class="section-heading">
              <span><AppIcon name="compare" :size="17" />影像对比</span>
            </div>
            <el-radio-group v-model="mode" class="view-modes" size="small"
              ><el-radio-button value="overlay">叠加</el-radio-button
              ><el-radio-button value="swipe">卷帘</el-radio-button
              ><el-radio-button value="compare"
                >同步对比</el-radio-button
              ></el-radio-group
            >
            <template v-if="mode === 'swipe'"
              ><div class="slider-label">
                <span>卷帘位置</span><span>{{ swipe }}%</span>
              </div>
              <el-slider v-model="swipe" aria-label="卷帘位置"
            /></template>
            <template v-if="mode === 'compare'"
              ><label class="control-label">右侧对比结果</label
              ><el-select
                v-model="comparison"
                clearable
                placeholder="原始影像"
                aria-label="右侧对比结果"
                ><el-option
                  v-for="p in results"
                  :key="p.id"
                  :value="p.id"
                  :label="
                    p.contract.strategy + ' / ' + p.id.slice(0, 8)
                  " /></el-select
            ></template>
          </section>
          <section
            v-if="prediction"
            class="parameter-section summary-section"
            aria-label="结果概览"
          >
            <div class="section-heading">
              <span><AppIcon name="chart" :size="18" />结果概览</span
              ><button class="text-button" @click="toggleTool('statistics')">
                详细统计 <span aria-hidden="true">↗</span>
              </button>
            </div>
            <div class="summary-grid">
              <div>
                <span>影像内预测覆盖率</span
                ><strong data-testid="coverage">{{
                  percent(prediction.metrics.coverage_percent)
                }}</strong>
              </div>
              <div>
                <span>受淹道路像素</span
                ><strong>{{
                  prediction.metrics.pred_pixels.toLocaleString()
                }}</strong>
              </div>
              <div>
                <span>有效像素</span
                ><strong>{{
                  prediction.metrics.valid_pixels.toLocaleString()
                }}</strong>
              </div>
            </div>
            <div class="summary-footer">
              <span
                >{{
                  prediction.reviews[0]
                    ? decisionLabels[prediction.reviews[0].decision]
                    : "待复核"
                }}
                · v{{ prediction.review_revision }}</span
              ><button class="text-button" @click="toggleTool('review')">
                打开复核 <span aria-hidden="true">→</span>
              </button>
            </div>
          </section>
        </div>
        <div
          v-show="leftTab === 'analyse'"
          role="tabpanel"
          aria-label="分析参数"
        >
          <section v-if="canAnalyze && image" class="parameter-section">
            <div class="section-heading">
              <span><AppIcon name="settings" :size="17" />分析配置</span>
            </div>
            <label class="control-label">分析来源</label>
            <el-select v-model="source" aria-label="分析来源"
              ><el-option
                label="历史结果"
                value="historical_replay"
                :disabled="!image.available_strategies.length" /><el-option
                label="本次推理"
                value="live_inference"
                :disabled="!capabilities?.live_inference.available"
            /></el-select>
            <label class="control-label">推理策略</label>
            <el-select v-model="strategy" aria-label="推理策略"
              ><el-option label="四视图增强 · tta4" value="tta4" /><el-option
                label="单视图 · single_view"
                value="single_view"
            /></el-select>
            <div class="configuration-card">
              <span class="small muted">模型版本</span
              ><strong>long_bce_lovasz</strong>
            </div>
            <p class="field-hint">
              {{
                source === "historical_replay"
                  ? image.available_strategies.length
                    ? "匹配策略：" + image.available_strategies.join(" / ")
                    : "暂无匹配结果，可导入外部掩膜。"
                  : capabilities?.live_inference.reason
              }}
            </p>
            <el-button
              type="primary"
              class="full-button"
              :loading="busy"
              :disabled="
                source === 'historical_replay'
                  ? !image.available_strategies.includes(strategy)
                  : !capabilities?.live_inference.available
              "
              @click="submit"
              ><AppIcon name="play" :size="16" />提交分析</el-button
            >
          </section>
          <section v-else class="parameter-section">
            <p class="field-hint">当前项目只读。</p>
          </section>
          <section v-if="canAnalyze" class="parameter-section">
            <div class="section-heading">
              <span><AppIcon name="download" :size="17" />外部结果</span>
            </div>
            <p class="field-hint">二值 PNG · 与原图同尺寸</p>
            <el-button class="full-button" @click="openImport"
              >导入外部结果</el-button
            >
          </section>
          <section class="parameter-section">
            <div class="section-heading"><span>服务状态</span></div>
            <div class="service-status">
              <i
                :class="{ available: capabilities?.live_inference.available }"
              />GPU 推理
              {{ capabilities?.live_inference.available ? "已连接" : "未连接" }}
            </div>
            <p class="field-hint">{{ capabilities?.live_inference.reason }}</p>
            <p v-if="capabilities?.live_inference.available" class="field-hint">
              {{ capabilities.live_inference.device }} · 排队
              {{ capabilities.live_inference.queue_depth || 0 }}
            </p>
          </section>
        </div>
      </div>
      <section
        v-if="activeTool"
        class="inspector-panel"
        :aria-label="toolTitle"
      >
        <div class="inspector-heading">
          <h2>
            <AppIcon
              :name="tools.find((t) => t.id === activeTool)?.icon || 'info'"
              :size="18"
            />{{ toolTitle }}
          </h2>
          <button
            class="icon-button"
            aria-label="关闭工具面板"
            @click="activeTool = ''"
          >
            <AppIcon name="close" :size="18" />
          </button>
        </div>
        <div class="inspector-scroll">
          <template v-if="activeTool === 'statistics'">
            <template v-if="prediction">
              <ResultStatistics
                :prediction="prediction"
                @review="activeTool = 'review'"
              />
            </template>
            <div v-else class="tool-empty">
              <AppIcon name="chart" :size="36" />
              <h3>等待分析结果</h3>
              <p>选择影像并提交分析。</p>
              <el-button
                v-if="canAnalyze"
                type="primary"
                @click="showParameters('analyse')"
                >配置分析任务</el-button
              >
            </div>
          </template>
          <template v-if="activeTool === 'region' || activeTool === 'review'">
            <section class="inspector-section region-section">
              <h3>
                调查区域<span>{{ annotations.length }} 个</span>
              </h3>

              <div v-if="prediction && canReview" class="region-actions">
                <el-button
                  type="primary"
                  class="full-button"
                  @click="drawRegion"
                  ><AppIcon name="region" :size="16" />圈选复核区域</el-button
                >
                <div class="actions">
                  <el-button
                    size="small"
                    :disabled="!annotations.length"
                    @click="viewer?.undo()"
                    >撤销最后区域</el-button
                  ><el-button
                    size="small"
                    :disabled="!annotations.length"
                    @click="annotations = []"
                    >清空草稿区域</el-button
                  >
                </div>
                <p class="field-hint">单击设点 · 双击完成 · Esc 取消</p>
              </div>
              <p v-else class="field-hint">
                {{
                  prediction
                    ? "当前角色仅可查看复核记录。"
                    : "请先生成或选择分析结果。"
                }}
              </p>
              <div v-for="(a, i) in annotations" :key="i" class="region-item">
                <AppIcon name="region" :size="16" /><span
                  >区域 {{ String(i + 1).padStart(2, "0") }}</span
                ><small>{{ a.coordinates.length - 1 }} 个顶点</small>
              </div>
            </section>
            <section v-if="prediction" class="inspector-section">
              <h3>
                人工复核<span>版本 v{{ baseRevision }}</span>
              </h3>
              <el-form
                v-if="canReview"
                label-position="top"
                @submit.prevent="saveReview"
                ><el-form-item label="复核结论"
                  ><el-select v-model="decision"
                    ><el-option
                      v-for="(label, key) in decisionLabels"
                      :key="key"
                      :value="key"
                      :label="label" /></el-select></el-form-item
                ><el-form-item label="判断依据"
                  ><el-input
                    v-model="note"
                    type="textarea"
                    :rows="3"
                    maxlength="5000"
                    aria-label="复核判断依据"
                    placeholder="填写判读依据"
                /></el-form-item>
                <p
                  v-if="baseRevision !== prediction.review_revision"
                  class="error"
                >
                  已有新复核版本。请先比较记录，再加载最新版本。
                </p>
                <el-button
                  v-if="baseRevision !== prediction.review_revision"
                  @click="baseRevision = prediction.review_revision"
                  >基于最新版本继续</el-button
                ><el-button
                  type="primary"
                  class="full-button"
                  native-type="submit"
                  :loading="busy"
                  >保存复核</el-button
                ></el-form
              >
              <div
                v-for="r in prediction.reviews"
                :key="r.id"
                class="review-history"
              >
                <b>v{{ r.revision }} · {{ decisionLabels[r.decision] }}</b>
                <p>{{ r.note }}</p>
                <p class="muted small">
                  {{ r.author }} · {{ fmtTime(r.created_at) }}
                </p>
                <el-button
                  size="small"
                  @click="annotations = r.annotations.map((a) => ({ ...a }))"
                  >查看圈选 {{ r.annotations.length }}</el-button
                >
              </div>
              <p v-if="!prediction.reviews.length" class="field-hint">
                尚未复核
              </p>
            </section>
          </template>
          <template v-if="activeTool === 'location'">
            <section class="inspector-section">
              <h3>拍摄位置 <span>WGS 84</span></h3>
              <template v-if="image?.location">
                <LocationMap :locations="imageLocations" style="--location-map-height: 280px" />
                <dl class="metric-list" style="margin-top: 16px">
                  <dt>纬度</dt>
                  <dd>{{ image.location.latitude.toFixed(6) }}°</dd>
                  <dt>经度</dt>
                  <dd>{{ image.location.longitude.toFixed(6) }}°</dd>
                  <dt>采集时间</dt>
                  <dd>{{ image.acquired_at || "未记录" }}</dd>
                  <dt>坐标来源</dt>
                  <dd>原始 EXIF · 相机拍摄点</dd>
                </dl>
              </template>
              <p v-else class="muted">该影像未记录 GPS。</p>
            </section>
          </template>
          <template v-if="activeTool === 'info'"
            ><section class="inspector-section">
              <h3>影像信息</h3>
              <dl class="metric-list">
                <dt>影像名称</dt>
                <dd>{{ image?.name }}</dd>
                <dt>实验影像尺寸</dt>
                <dd>{{ image?.width }} × {{ image?.height }}</dd>
                <dt>数据分区</dt>
                <dd>{{ image?.split }}</dd>
                <dt>坐标系</dt>
                <dd>影像像素坐标</dd>
                <dt>采集时间</dt>
                <dd>{{ image?.acquired_at || "未记录" }}</dd>
                <template v-if="image?.native_size"
                  ><dt>原始采集尺寸</dt>
                  <dd>
                    {{ image.native_size[0] }} × {{ image.native_size[1] }}
                  </dd></template
                >
              </dl>
            </section>
            <section v-if="prediction" class="inspector-section">
              <h3>来源与版本详情</h3>
              <el-tag>{{
                sourceLabels[prediction.contract.source_mode]
              }}</el-tag>

              <pre class="detail-json">{{
                JSON.stringify(prediction.contract, null, 2)
              }}</pre>
            </section></template
          >
        </div>
        <div v-if="prediction && canReport" class="inspector-footer">
          <span
            ><AppIcon name="report" :size="16" />当前结果 · 复核 v{{
              prediction.review_revision
            }}</span
          ><el-button :loading="busy" @click="report">导出报告</el-button>
        </div>
      </section>
      <footer class="parameter-footer">
        <span class="coordinate-mode"
          ><AppIcon name="images" :size="15" />影像坐标 · px</span
        ><button class="text-button" @click="toggleTool('info')">
          来源与版本 <AppIcon name="info" :size="15" />
        </button>
      </footer>
    </aside>
    <div class="geo-stage">
      <header class="scene-toolbar">
        <div class="scene-toolbar-title">
          <button
            v-if="panelCollapsed"
            class="icon-button"
            aria-label="展开参数面板"
            @click="panelCollapsed = false"
          >
            <AppIcon name="right" /></button
          ><AppIcon name="images" :size="18" /><strong>{{
            image?.name || "加载中"
          }}</strong
          ><span class="toolbar-split">{{ image?.split }}</span>
        </div>
        <div class="scene-badges">
          <span v-if="prediction" class="source-badge">{{
            sourceLabels[prediction.contract.source_mode]
          }}</span
          ><span class="small muted">{{
            prediction ? "复核 v" + prediction.review_revision : "原始影像"
          }}</span>
        </div>
      </header>
      <div class="geo-stage-body">
        <div class="map-column">
          <div class="map-surface">
            <ImageViewer
              v-if="image"
              :key="image.id"
              ref="viewer"
              :image="image"
              :prediction="prediction"
              :compare-prediction="comparePrediction"
              :mode="mode"
              :layer="layer"
              :opacity="opacity"
              :swipe="swipe"
              :annotations="annotations"
              @annotations="annotations = $event"
              @pixel="queryPixel"
            />
            <div v-else class="map-loading">
              {{
                imageError
                  ? "影像加载失败，请返回影像资料重试。"
                  : "正在加载影像…"
              }}
            </div>
            <div class="map-tool-rail" role="toolbar" aria-label="地图工具栏">
              <div class="tool-group">
                <button
                  v-for="tool in tools"
                  :key="tool.id"
                  class="map-tool"
                  :class="{ active: activeTool === tool.id }"
                  :aria-label="tool.label"
                  :aria-pressed="activeTool === tool.id"
                  :title="tool.label"
                  @click="toggleTool(tool.id)"
                >
                  <AppIcon :name="tool.icon" /><span>{{ tool.label }}</span>
                </button>
              </div>
              <div class="tool-group">
                <button
                  class="map-tool"
                  aria-label="填充视图"
                  title="填充视图"
                  @click="viewer?.fillView()"
                >
                  <AppIcon name="expand" /><span>填充视图</span>
                </button>
                <button
                  class="map-tool"
                  aria-label="适配全图"
                  title="适配全图 F"
                  @click="viewer?.fit()"
                >
                  <AppIcon name="fit" /><span>适配全图 F</span></button
                ><button
                  class="map-tool"
                  aria-label="放大影像"
                  title="放大"
                  @click="viewer?.zoom(1)"
                >
                  <AppIcon name="plus" /></button
                ><button
                  class="map-tool"
                  aria-label="缩小影像"
                  title="缩小"
                  @click="viewer?.zoom(-1)"
                >
                  <AppIcon name="minus" />
                </button>
              </div>
              <div v-if="canReport" class="tool-group">
                <button
                  class="map-tool"
                  aria-label="生成报告"
                  title="生成报告"
                  :disabled="!prediction || busy"
                  @click="report"
                >
                  <AppIcon name="download" /><span>生成报告</span>
                </button>
              </div>
            </div>
            <div class="map-legend" aria-label="图层图例">
              <span class="legend-title">图例</span
              ><template v-if="layer === 'difference'"
                ><span
                  ><i class="dot" style="background: #3ca069" />TP 命中</span
                ><span
                  ><i class="dot" style="background: #dc5046" />FP 误报</span
                ><span
                  ><i class="dot" style="background: #ebb93c" />FN 漏检</span
                ></template
              ><template v-else
                ><span v-if="layer === 'prediction'"
                  ><i
                    class="dot"
                    style="background: #e65d3e"
                  />预测受淹道路</span
                ><span v-if="layer === 'reference'"
                  ><i class="dot" style="background: #3c8cdc" />参考标签</span
                ><span
                  ><i class="dot" style="background: #f0c942" />复核区域</span
                ></template
              >
            </div>
            <span class="map-coordinate-badge">IMAGE / PX</span>
          </div>
          <footer class="map-status">
            <span v-if="pixel"
              >X {{ pixel.x }} · Y {{ pixel.y }}
              <span class="status-divider">|</span> RGB
              {{ pixel.rgb.join(", ") }} <span class="status-divider">|</span>
              {{ pixel.valid ? "有效像素" : "无效标签区" }} ·
              {{ pixel.predicted ? "受淹道路" : "背景" }} · 参考
              {{ pixel.label ?? "未提供" }}</span
            ><span v-else>滚轮缩放 · 拖动平移 · 点击查询像素</span
            ><span class="region-counter"
              >已圈选 {{ annotations.length }} 个区域</span
            >
          </footer>
          <div class="result-timebar">
            <AppIcon name="calendar" :size="17" />
            <div>
              <span class="small muted">当前结果时间</span
              ><strong>{{
                prediction ? fmtTime(prediction.created_at) : "尚未生成结果"
              }}</strong>
            </div>
            <div class="result-stepper">
              <button
                class="icon-button"
                aria-label="上一个结果"
                :disabled="resultIndex <= 0"
                @click="stepResult(-1)"
              >
                <AppIcon name="left" :size="17" /></button
              ><span
                >{{ resultIndex < 0 ? "—" : resultIndex + 1 }} /
                {{ filteredResults.length }}</span
              ><button
                class="icon-button"
                aria-label="下一个结果"
                :disabled="
                  resultIndex < 0 || resultIndex >= filteredResults.length - 1
                "
                @click="stepResult(1)"
              >
                <AppIcon name="right" :size="17" />
              </button>
            </div>
            <span class="small muted">{{
              prediction?.contract.strategy || "—"
            }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <el-dialog
    v-model="importOpen"
    title="导入外部结果"
    width="650"
    destroy-on-close
    ><p>选择与原图网格一致的二值 PNG，填写来源与模型信息。</p>
    <input
      type="file"
      accept="image/png"
      aria-label="外部掩膜"
      @change="setMask"
    /><el-input
      v-model="importMetadata"
      type="textarea"
      :rows="14"
      style="margin: 15px 0"
      aria-label="外部结果元数据"
    /><el-button type="primary" :loading="busy" @click="importResult"
      >校验并导入</el-button
    ></el-dialog
  >
</template>
