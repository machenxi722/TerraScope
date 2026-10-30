<script setup lang="ts">
import { ref, computed, watch } from "vue";
import CaseLibrary from "../components/CaseLibrary.vue";
import LocationMap, { type Locations } from "../components/LocationMap.vue";
import PageNavigation from "../components/PageNavigation.vue";
import { useRouter } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { api, post, assetUrl, type ImageAsset } from "../api/client";
import { useAction } from "../composables/actions";
import { useProject } from "../composables/project";
const { session, project, canAnalyze } = useProject(),
  router = useRouter(),
  client = useQueryClient(),
  { busy, run } = useAction();
const search = ref(""),
  page = ref(1),
  fileInput = ref<HTMLInputElement>(),
  file = ref<File | null>(null),
  casesOpen = ref(false);
watch([search, () => session.projectId], () => {
  page.value = 1;
});
const {
  data: images,
  error,
  isPending,
} = useQuery({
  queryKey: computed(() => [
    "images",
    session.projectId,
    search.value,
    page.value,
  ]),
  enabled: computed(() => !!session.projectId),
  queryFn: () =>
    api<ImageAsset[]>(
      `/projects/${session.projectId}/images?limit=48&offset=${(page.value - 1) * 48}&q=${encodeURIComponent(search.value)}`,
    ),
});
const filtered = images;
const viewMode = ref("list");
const { data: locations } = useQuery({
  queryKey: computed(() => ["project-locations", session.projectId]),
  enabled: computed(() => !!session.projectId && viewMode.value === "map"),
  queryFn: () => api<Locations>(`/projects/${session.projectId}/locations`),
});
function selected(e: Event) {
  file.value = (e.target as HTMLInputElement).files?.[0] || null;
}
async function refresh() {
  await client.invalidateQueries({ queryKey: ["images", session.projectId] });
  await client.invalidateQueries({ queryKey: ["projects"] });
}
async function upload() {
  await run(async () => {
    if (!file.value) throw new Error("请选择文件");
    const form = new FormData();
    form.append("file", file.value);
    const image = await api<ImageAsset>(
      `/projects/${session.projectId}/images`,
      {
        method: "POST",
        body: form,
      },
    );
    file.value = null;
    if (fileInput.value) fileInput.value.value = "";
    await refresh();
    await router.push(`/workbench/${image.id}`);
  }, "影像已保存，重复文件自动复用");
}
async function addCase(id: string) {
  await run(async () => {
    await post(`/projects/${session.projectId}/cases/${id}`);
    await refresh();
    await client.invalidateQueries({ queryKey: ["project-locations"] });
  }, "案例已导入当前项目");
}
</script>
<template>
  <div class="page-head">
    <div>
      <h1>影像资料</h1>
      <span class="muted">{{ project?.name || "请先选择项目" }}</span>
    </div>
    <el-button v-if="canAnalyze" @click="casesOpen = true"
      >从案例库导入</el-button
    >
  </div>
  <section v-if="canAnalyze" class="panel">
    <div class="row">
      <input
        ref="fileInput"
        aria-label="上传影像文件"
        class="file-input"
        type="file"
        accept="image/png,image/jpeg"
        @change="selected"
      /><el-button
        type="primary"
        :loading="busy"
        :disabled="!file"
        @click="upload"
        >上传影像</el-button
      ><span class="muted small">JPG / PNG · 最大 20 MB · 2500 万像素</span>
    </div>
  </section>
  <div class="row" style="margin-bottom: 18px">
    <el-input
      v-model="search"
      placeholder="搜索影像名称或样本 ID"
      clearable
      style="max-width: 360px"
    /><span class="muted">本页 {{ filtered?.length || 0 }} 幅</span
    ><el-radio-group v-model="viewMode"
      ><el-radio-button value="list">影像列表</el-radio-button
      ><el-radio-button value="map">GPS 拍摄点</el-radio-button></el-radio-group
    >
  </div>
  <p v-if="error" class="error">{{ error.message }}</p>
  <div v-if="!isPending && !images?.length" class="panel empty">
    {{
      search ? "没有匹配的影像。" : "当前项目没有影像，请上传或从案例库导入。"
    }}
  </div>
  <LocationMap
    v-if="viewMode === 'map' && locations"
    :locations="locations"
    @select="(id) => router.push(`/workbench/${id}`)"
  />
  <div v-if="viewMode === 'list'" class="images-grid">
    <article v-for="i in filtered" :key="i.id" class="panel image-card">
      <img :src="assetUrl(i.thumbnail_asset_id)" :alt="i.name" loading="lazy" />
      <div class="content">
        <h3>{{ i.name }}</h3>
        <div class="row">
          <el-tag size="small">{{ i.split }}</el-tag
          ><span class="muted small"
            >{{ i.width }} × {{ i.height }} px{{
              i.location ? " · GPS" : ""
            }}</span
          >
        </div>
        <p class="muted small">
          {{
            i.available_strategies.length ? "有匹配历史结果" : "无匹配历史结果"
          }}
          · {{ i.label_asset_id ? "有参考标签" : "无参考标签" }}
        </p>
        <el-button type="primary" @click="router.push(`/workbench/${i.id}`)"
          >打开工作台</el-button
        >
      </div>
    </article>
  </div>
  <PageNavigation v-model="page" :count="images?.length || 0" :size="48" />
  <el-dialog
    v-model="casesOpen"
    title="实验影像库"
    top="4vh"
    width="1040"
    destroy-on-close
  >
    <CaseLibrary :busy="busy" @import="addCase" />
  </el-dialog>
</template>
