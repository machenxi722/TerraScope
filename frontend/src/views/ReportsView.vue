<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import PageNavigation from "../components/PageNavigation.vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  api,
  post,
  assetUrl,
  fmtTime,
  statusLabels,
  type Report,
} from "../api/client";
import { useProject } from "../composables/project";
import { useAction } from "../composables/actions";
const { session, canReport } = useProject(),
  router = useRouter(),
  client = useQueryClient(),
  { busy, run } = useAction(),
  selected = ref<Report | null>(null);
const page = ref(1);
watch(
  () => session.projectId,
  () => {
    page.value = 1;
    selected.value = null;
  },
);
const { data: reports, error } = useQuery({
  queryKey: computed(() => ["reports", session.projectId, page.value]),
  enabled: computed(() => !!session.projectId),
  queryFn: () =>
    api<Report[]>(
      `/reports?project_id=${session.projectId}&limit=50&offset=${(page.value - 1) * 50}`,
    ),
  refetchInterval: 2000,
});
async function retry(r: Report) {
  await run(async () => {
    await post(`/reports/${r.id}/retry`);
    await client.invalidateQueries({ queryKey: ["reports"] });
  }, "已重新排队生成同一快照");
}
</script>
<template>
  <div class="page-head">
    <div>
      <h1>报告中心</h1>
      <span class="muted">报告版本与成果下载</span>
    </div>
  </div>
  <p v-if="error" class="error">{{ error.message }}</p>
  <section class="panel">
    <el-table
      :data="reports || []"
      empty-text="暂无报告，请在解译工作台生成报告"
      ><el-table-column label="报告" min-width="160"
        ><template #default="{ row }"
          ><span class="mono">{{ row.id.slice(0, 8) }}</span>
          <div class="muted small">
            复核 v{{ row.snapshot.review_revision }}
          </div></template
        ></el-table-column
      ><el-table-column label="生成时间" min-width="180"
        ><template #default="{ row }">{{
          fmtTime(row.created_at)
        }}</template></el-table-column
      ><el-table-column label="状态" width="130"
        ><template #default="{ row }"
          ><el-tag
            :type="
              row.status === 'FAILED'
                ? 'danger'
                : row.status === 'SUCCEEDED'
                  ? 'success'
                  : 'info'
            "
            >{{ statusLabels[row.status] }}</el-tag
          >
          <p class="error small" v-if="row.error">{{ row.error }}</p></template
        ></el-table-column
      ><el-table-column label="下载成果" min-width="340"
        ><template #default="{ row }"
          ><div class="actions">
            <template v-if="row.status === 'SUCCEEDED'"
              ><a
                :href="assetUrl(row.files['evidence.zip'], false)"
                class="el-button el-button--primary el-button--small"
                >ZIP 证据包</a
              ><a
                :href="assetUrl(row.files['report.pdf'], false)"
                class="el-button el-button--small"
                >PDF</a
              ><a
                :href="assetUrl(row.files['statistics.csv'], false)"
                class="el-button el-button--small"
                >CSV</a
              ><a
                :href="assetUrl(row.files['mask.png'], false)"
                class="el-button el-button--small"
                >掩膜</a
              ><a
                :href="assetUrl(row.files['overlay.png'], false)"
                class="el-button el-button--small"
                >叠加图</a
              ><a
                :href="assetUrl(row.files['metadata.json'], false)"
                class="el-button el-button--small"
                >JSON</a
              ><a
                v-if="row.files['location.geojson']"
                :href="assetUrl(row.files['location.geojson'], false)"
                class="el-button el-button--small"
                >GPS</a
              ></template
            ><el-button
              size="small"
              @click="
                router.push(
                  `/workbench/${row.snapshot.image.id}?prediction=${row.prediction_id}`,
                )
              "
              >查看结果</el-button
            ><el-button size="small" @click="selected = row">元数据</el-button
            ><el-button
              v-if="row.status === 'FAILED' && canReport"
              :loading="busy"
              size="small"
              @click="retry(row)"
              >重试</el-button
            >
          </div></template
        ></el-table-column
      ></el-table
    >
  </section>
  <PageNavigation v-model="page" :count="reports?.length || 0" :size="50" />
  <el-drawer
    :model-value="!!selected"
    title="固定快照"
    size="600"
    @close="selected = null"
  >
    <pre class="detail-json" style="max-height: none">{{
      JSON.stringify(selected?.snapshot, null, 2)
    }}</pre>
  </el-drawer>
</template>
