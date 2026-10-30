<script setup lang="ts">
import { ref, computed, watch } from "vue";
import PageNavigation from "../components/PageNavigation.vue";
import { useRouter, useRoute } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  api,
  post,
  newKey,
  fmtTime,
  statusLabels,
  sourceLabels,
  type Task,
} from "../api/client";
import { useProject } from "../composables/project";
import { useAction } from "../composables/actions";
const { session, canAnalyze } = useProject(),
  router = useRouter(),
  route = useRoute(),
  client = useQueryClient(),
  { busy, run } = useAction(),
  selected = ref(String(route.query.task || ""));
const page = ref(1);
watch(
  () => session.projectId,
  () => {
    page.value = 1;
    selected.value = "";
  },
);
const { data: tasks, error } = useQuery({
  queryKey: computed(() => ["tasks", session.projectId, page.value]),
  enabled: computed(() => !!session.projectId),
  queryFn: () =>
    api<Task[]>(
      `/analysis-tasks?project_id=${session.projectId}&limit=50&offset=${(page.value - 1) * 50}`,
    ),
  refetchInterval: 2000,
});
const terminal = ["SUCCEEDED", "FAILED", "CANCELED"];
const { data: selectedLive } = useQuery({
  queryKey: computed(() => ["task", selected.value]),
  enabled: computed(() => !!selected.value),
  queryFn: () => api<Task>(`/analysis-tasks/${selected.value}`),
  refetchInterval: (query) =>
    terminal.includes(query.state.data?.status || "") ? false : 2000,
});
async function act(t: Task, action: string) {
  await run(
    async () => {
      await post(
        `/analysis-tasks/${t.id}/${action}`,
        undefined,
        action === "retry" ? newKey() : undefined,
      );
      await client.invalidateQueries({ queryKey: ["tasks"] });
      await client.invalidateQueries({ queryKey: ["task", t.id] });
    },
    action === "cancel" ? "已提交取消申请" : "已创建新的重试任务",
  );
}
</script>
<template>
  <div class="page-head">
    <div>
      <h1>分析任务</h1>
      <span class="muted">任务进度、分析结果与运行日志</span>
    </div>
    <el-button @click="router.push('/images')">选择影像创建任务</el-button>
  </div>
  <p v-if="error" class="error">{{ error.message }}</p>
  <section class="panel">
    <el-table :data="tasks || []" empty-text="暂无任务"
      ><el-table-column label="任务" min-width="150"
        ><template #default="{ row }"
          ><span class="mono">{{ row.id.slice(0, 8) }}</span>
          <div class="small muted">第 {{ row.attempt }} 次执行</div></template
        ></el-table-column
      ><el-table-column label="来源 / 策略" min-width="180"
        ><template #default="{ row }"
          >{{ sourceLabels[String(row.config.mode)] }}
          <div class="small muted">{{ row.config.strategy }}</div></template
        ></el-table-column
      ><el-table-column label="状态" width="150"
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
          ></template
        ></el-table-column
      ><el-table-column label="提交时间" min-width="180"
        ><template #default="{ row }">{{
          fmtTime(row.created_at)
        }}</template></el-table-column
      ><el-table-column label="操作" min-width="240"
        ><template #default="{ row }"
          ><el-button size="small" @click="selected = row.id"
            >阶段日志</el-button
          ><el-button
            v-if="row.prediction_id"
            size="small"
            type="primary"
            @click="
              router.push(
                `/workbench/${row.image_id}?prediction=${row.prediction_id}`,
              )
            "
            >查看结果</el-button
          ><el-button
            v-if="canAnalyze && !terminal.includes(row.status)"
            size="small"
            :disabled="row.status === 'CANCEL_REQUESTED'"
            :loading="busy"
            @click="act(row, 'cancel')"
            >取消</el-button
          ><el-button
            v-if="
              canAnalyze &&
              ['FAILED', 'CANCELED'].includes(row.status) &&
              row.attempt < 3
            "
            size="small"
            :loading="busy"
            @click="act(row, 'retry')"
            >重试</el-button
          ></template
        ></el-table-column
      ></el-table
    >
  </section>
  <PageNavigation v-model="page" :count="tasks?.length || 0" :size="50" />
  <el-drawer
    :model-value="!!selected"
    title="阶段日志"
    class="task-log-drawer"
    size="500"
    @close="selected = ''"
    ><template v-if="selectedLive"
      ><p class="mono">{{ selectedLive.id }}</p>
      <p v-if="selectedLive.error" class="error">
        {{ selectedLive.error.message }}
      </p>
      <el-timeline
        ><el-timeline-item
          v-for="(log, index) in selectedLive.logs"
          :key="index"
          :timestamp="fmtTime(Number(log.at))"
          ><b>{{ statusLabels[String(log.stage)] }}</b>
          <p>{{ log.message }}</p></el-timeline-item
        ></el-timeline
      >
      <h3>执行配置</h3>
      <pre class="detail-json">{{
        JSON.stringify(selectedLive.config, null, 2)
      }}</pre>
    </template></el-drawer
  >
</template>
<style>
.task-log-drawer .el-timeline-item {
  padding-bottom: 8px;
}
.task-log-drawer .el-timeline-item__content p {
  margin: 2px 0;
  line-height: 1.3;
}
.task-log-drawer .el-timeline-item__timestamp {
  margin-top: 4px;
  font-size: 12px;
}
.task-log-drawer .el-drawer__header {
  margin-bottom: 12px;
}
</style>
