<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount, nextTick } from "vue";
import { useRouter } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import {
  api,
  post,
  newKey,
  percent,
  type ImageAsset,
  type Task,
} from "../api/client";
import { useProject } from "../composables/project";
import { useAction } from "../composables/actions";
echarts.use([
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
]);
interface Summary {
  n: number;
  n_positive: number;
  global_iou: number;
  coverage_mae_pp: number;
  scene_tp: number;
  scene_fn: number;
  scene_fp: number;
  scene_tn: number;
  strategy?: string;
}
interface Row {
  id: string;
  image_id: string | null;
  prediction_id: string | null;
  case_available: boolean;
  tp: number;
  fp: number;
  fn: number;
  coverage_percent: number;
  iou: number | null;
  gt_pixels: number;
}
interface Experiment {
  summary: Summary;
  comparison: Summary[];
  records: Row[];
  total: number;
  boundary: string;
  baselines: Record<string, unknown>[];
}
const { session, canAnalyze } = useProject(),
  client = useQueryClient(),
  { busy, run } = useAction(),
  router = useRouter(),
  split = ref("test"),
  strategy = ref("tta4"),
  search = ref(""),
  page = ref(1),
  chartEl = ref<HTMLElement>();
let chart: echarts.ECharts | undefined, observer: ResizeObserver | undefined;
watch(
  [split, strategy, search, () => session.projectId],
  () => (page.value = 1),
);
const exportUrl = computed(
  () =>
    `/api/v1/experiments/floodnet/export?${new URLSearchParams({
      project_id: session.projectId,
      split: split.value,
      strategy: strategy.value,
      q: search.value,
    })}`,
);
async function openRecord(row: Row) {
  await run(async () => {
    const chosenStrategy = strategy.value;
    let imageId = row.image_id;
    if (!imageId) {
      const image = await post<ImageAsset>(
        `/projects/${session.projectId}/cases/${row.id}`,
      );
      imageId = image.id;
    }
    const query: Record<string, string> = { strategy: chosenStrategy };
    if (row.prediction_id) query.prediction = row.prediction_id;
    else if (canAnalyze.value && row.case_available) {
      const task = await post<Task>(
        "/analysis-tasks",
        {
          image_id: imageId,
          mode: "historical_replay",
          strategy: chosenStrategy,
        },
        newKey(),
      );
      query.task = task.id;
    }
    await Promise.all([
      client.invalidateQueries({ queryKey: ["experiment"] }),
      client.invalidateQueries({ queryKey: ["projects"] }),
      client.invalidateQueries({ queryKey: ["images"] }),
    ]);
    await router.push({ path: `/workbench/${imageId}`, query });
  });
}
const { data, error, isPending } = useQuery({
  queryKey: computed(() => [
    "experiment",
    session.projectId,
    split.value,
    strategy.value,
    search.value,
    page.value,
  ]),
  enabled: computed(() => !!session.projectId),
  queryFn: () =>
    api<Experiment>(
      `/experiments/floodnet/metrics?project_id=${session.projectId}&split=${split.value}&strategy=${strategy.value}&q=${encodeURIComponent(search.value)}&offset=${(page.value - 1) * 30}`,
    ),
});
watch([data, chartEl], async () => {
  await nextTick();
  if (chart && chart.getDom() !== chartEl.value) {
    observer?.disconnect();
    chart.dispose();
    chart = undefined;
  }
  if (!chartEl.value || !data.value) return;
  if (!chart) {
    chart = echarts.init(chartEl.value);
    observer = new ResizeObserver(() => chart?.resize());
    observer.observe(chartEl.value);
  }
  chart.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 50, right: 20, bottom: 30, top: 20 },
    xAxis: { type: "category", data: ["单视图", "四视图"] },
    yAxis: { type: "value", name: "IoU %", max: 100 },
    series: [
      {
        type: "bar",
        data: data.value.comparison.map((s) =>
          Number((s.global_iou * 100).toFixed(2)),
        ),
        itemStyle: { color: "#094393", borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 80,
        label: { show: true, position: "top", formatter: "{c}%" },
      },
    ],
  });
});
onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
});
</script>
<template>
  <div class="page-head">
    <div>
      <h1>实验评估</h1>
      <span class="muted">FloodNet · 分区统计与策略对比</span>
    </div>
    <a v-if="session.projectId" :href="exportUrl" class="el-button"
      >导出逐景 CSV</a
    >
  </div>
  <section class="panel">
    <div class="row">
      <el-select v-model="split" style="width: 190px" aria-label="评估分区"
        ><el-option label="测试集 · 448 幅" value="test" /><el-option
          label="留出集 · 370 幅"
          value="holdout" /><el-option
          label="验证集 · 80 幅"
          value="val" /></el-select
      ><el-select v-model="strategy" style="width: 150px" aria-label="评估策略"
        ><el-option label="最终四视图" value="tta4" /><el-option
          label="优化单视图"
          value="single_view"
      /></el-select>
    </div>

    <p v-if="error" class="error">{{ error.message }}</p>
    <div v-if="data" class="grid">
      <div>
        <div class="stats">
          <div>
            <div class="stat">{{ percent(data.summary.global_iou, true) }}</div>
            全局 IoU
          </div>
          <div>
            <div class="stat">
              {{ data.summary.coverage_mae_pp.toFixed(4) }}
            </div>
            覆盖率 MAE / pp
          </div>
        </div>
        <dl class="metric-list">
          <dt>样本数 / 真实阳性</dt>
          <dd>{{ data.summary.n }} / {{ data.summary.n_positive }}</dd>
          <dt>场景命中 / 漏检</dt>
          <dd>{{ data.summary.scene_tp }} / {{ data.summary.scene_fn }}</dd>
          <dt>场景误报 / 正确排除</dt>
          <dd>{{ data.summary.scene_fp }} / {{ data.summary.scene_tn }}</dd>
        </dl>
        <p class="muted small">场景筛查阈值：覆盖率 ≥1%</p>
      </div>
      <div
        ref="chartEl"
        style="height: 240px"
        role="img"
        aria-label="单视图与四视图全局 IoU 对比"
      />
    </div>
  </section>
  <section class="panel">
    <div class="page-head">
      <h2>逐景记录</h2>
      <el-input
        v-model="search"
        placeholder="按样本 ID 搜索"
        clearable
        style="width: 240px"
      />
    </div>
    <el-table v-loading="isPending" :data="data?.records || []"
      ><el-table-column prop="id" label="样本 ID" /><el-table-column
        label="预测覆盖率"
        ><template #default="{ row }">{{
          percent(row.coverage_percent)
        }}</template></el-table-column
      ><el-table-column label="IoU"
        ><template #default="{ row }">{{
          percent(row.iou, true)
        }}</template></el-table-column
      ><el-table-column prop="tp" label="TP" /><el-table-column
        prop="fp"
        label="FP"
      /><el-table-column prop="fn" label="FN" /><el-table-column
        label="可用资料"
        width="160"
        ><template #default="{ row }"
          ><el-button
            v-if="row.image_id || (row.case_available && canAnalyze)"
            size="small"
            :loading="busy"
            @click="openRecord(row)"
            >{{
              row.prediction_id
                ? "查看结果"
                : row.case_available && canAnalyze
                  ? row.image_id
                    ? "加载结果"
                    : "导入并分析"
                  : "打开影像"
            }}</el-button
          ><span v-else class="muted">仅统计记录</span></template
        ></el-table-column
      ></el-table
    ><el-pagination
      v-model:current-page="page"
      :page-size="30"
      :total="data?.total || 0"
      layout="total, prev, pager, next"
      style="margin-top: 18px"
    />
  </section>
  <section v-if="data" class="panel">
    <h2>历史方案对照</h2>
    <el-table :data="data.baselines"
      ><el-table-column prop="方案" label="方案" /><el-table-column
        prop="评估集"
        label="评估集" /><el-table-column label="IoU"
        ><template #default="{ row }"
          >{{ Number(row["IoU百分比"]).toFixed(2) }}%</template
        ></el-table-column
      ><el-table-column label="覆盖率 MAE"
        ><template #default="{ row }"
          >{{ Number(row["覆盖率MAE百分点"]).toFixed(4) }} pp</template
        ></el-table-column
      ><el-table-column prop="命中TP" label="命中" /><el-table-column
        prop="误报FP"
        label="误报"
    /></el-table>
  </section>
</template>
