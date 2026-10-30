<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { api } from "../api/client";
import LocationMap, { type Locations } from "./LocationMap.vue";
import PageNavigation from "./PageNavigation.vue";
const props = defineProps<{ busy: boolean }>();
const emit = defineEmits<{ import: [id: string] }>();
const search = ref(""),
  split = ref(""),
  gps = ref(false),
  page = ref(1),
  mode = ref("list");
const params = computed(
  () =>
    `q=${encodeURIComponent(search.value)}&split=${split.value}&gps_only=${gps.value}`,
);
watch([search, split, gps], () => {
  page.value = 1;
});
interface Case {
  sample_id: string;
  split: string;
  width: number;
  height: number;
  strategies: string[];
  location: unknown;
}
const { data: rows, error } = useQuery({
  queryKey: computed(() => ["cases", params.value, page.value]),
  queryFn: () =>
    api<Case[]>(
      `/cases?${params.value}&limit=12&offset=${(page.value - 1) * 12}`,
    ),
});
const { data: summary } = useQuery({
  queryKey: computed(() => ["cases-summary", params.value]),
  queryFn: () =>
    api<{ total: number; gps_count: number }>(`/cases/summary?${params.value}`),
});
const { data: locations } = useQuery({
  queryKey: computed(() => ["case-locations", params.value]),
  enabled: computed(() => mode.value === "map"),
  queryFn: () => api<Locations>(`/cases/locations?${params.value}`),
});
function selectPoint(id: string) {
  search.value = id;
  mode.value = "list";
}
</script>
<template>
  <div class="library-toolbar">
    <el-input
      v-model="search"
      placeholder="搜索样本 ID"
      aria-label="搜索案例 ID"
      clearable
    />
    <el-select v-model="split" aria-label="案例分区" placeholder="全部分区"
      ><el-option label="全部分区" value="" /><el-option
        v-for="s in ['train', 'val', 'test', 'holdout']"
        :key="s"
        :label="s"
        :value="s"
    /></el-select>
    <el-checkbox v-model="gps">仅含 GPS</el-checkbox>
    <el-radio-group v-model="mode"
      ><el-radio-button value="list">影像</el-radio-button
      ><el-radio-button value="map">拍摄点</el-radio-button></el-radio-group
    >
  </div>
  <div class="library-summary">
    {{ summary?.total.toLocaleString() || 0 }} 幅影像
    <span
      >· {{ summary?.gps_count.toLocaleString() || 0 }} 幅含 GPS · RGB / 标签 /
      策略结果</span
    >
  </div>
  <p v-if="error" class="error">{{ error.message }}</p>
  <template v-if="mode === 'list'">
    <div class="case-grid">
      <article v-for="row in rows" :key="row.sample_id" class="case-tile">
        <img
          :src="`/api/v1/cases/${row.sample_id}/thumbnail`"
          :alt="`样本 ${row.sample_id}`"
          loading="lazy"
        />
        <div>
          <strong>{{ row.sample_id }}</strong
          ><span>{{ row.split }} · {{ row.width }} × {{ row.height }}</span
          ><span
            >{{ row.strategies.length ? "单视图 / 四视图" : "RGB / 标签"
            }}{{ row.location ? " · GPS" : "" }}</span
          >
        </div>
        <el-button
          type="primary"
          :loading="props.busy"
          @click="emit('import', row.sample_id)"
          >导入</el-button
        >
      </article>
    </div>
    <p v-if="rows?.length === 0" class="muted">没有匹配的样本。</p>
    <PageNavigation v-model="page" :count="rows?.length || 0" :size="12" />
  </template>
  <LocationMap
    v-else-if="locations"
    :locations="locations"
    @select="selectPoint"
  />
</template>
<style scoped>
.library-toolbar {
  display: grid;
  grid-template-columns: 1fr 145px 110px auto;
  gap: 12px;
  align-items: center;
}
.library-summary {
  margin: 12px 0;
  color: #114a91;
  font-size: 17px;
  font-weight: 600;
}
.library-summary span {
  font-size: 14px;
  color: #637487;
  font-weight: 400;
}
.case-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.case-tile {
  border: 1px solid #dce3e9;
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 10px;
  padding: 8px;
  background: #fafcfe;
}
.case-tile img {
  width: 92px;
  height: 70px;
  object-fit: cover;
  grid-row: span 2;
}
.case-tile strong {
  display: block;
  font-size: 16px;
  color: #104a92;
}
.case-tile span {
  display: block;
  color: #607184;
  font-size: 12px;
  line-height: 1.6;
}
.case-tile .el-button {
  margin: 0;
  width: fit-content;
  height: 27px;
}
@media (max-width: 900px) {
  .case-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
