<script setup lang="ts">
import { ref, computed, watch } from "vue";
import PageNavigation from "../components/PageNavigation.vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  api,
  post,
  fmtTime,
  type Capabilities,
  type User,
} from "../api/client";
import { useProject } from "../composables/project";
import { useAction } from "../composables/actions";
const { session, project } = useProject(),
  client = useQueryClient(),
  { busy, run } = useAction();
const auditPage = ref(1);
watch(
  () => session.projectId,
  () => {
    auditPage.value = 1;
    memberName.value = "";
  },
);
const { data: capabilities } = useQuery({
  queryKey: ["capabilities"],
  queryFn: () => api<Capabilities>("/system/capabilities"),
  refetchInterval: 15000,
});
const { data: models } = useQuery({
  queryKey: ["models"],
  queryFn: () => api<Record<string, unknown>[]>("/system/models"),
});
const { data: members } = useQuery({
  queryKey: computed(() => ["members", session.projectId]),
  enabled: computed(() => !!session.projectId),
  queryFn: () =>
    api<{ user_id: string; username: string; role: string }[]>(
      `/projects/${session.projectId}/members`,
    ),
});
const { data: users } = useQuery({
  queryKey: ["users"],
  enabled: computed(() => !!session.user?.is_admin),
  queryFn: () => api<User[]>("/users"),
});
const { data: audit } = useQuery({
  queryKey: computed(() => ["audit", session.projectId, auditPage.value]),
  enabled: computed(() => !!session.projectId),
  queryFn: () =>
    api<
      {
        id: string;
        action: string;
        actor: string;
        object_id: string;
        request_id: string;
        created_at: number;
      }[]
    >(
      `/projects/${session.projectId}/audit?limit=50&offset=${(auditPage.value - 1) * 50}`,
    ),
});
const username = ref(""),
  password = ref(""),
  memberName = ref(""),
  role = ref("viewer");
const roleLabels: Record<string, string> = {
  admin: "项目管理员",
  analyst: "分析员",
  reviewer: "复核员",
  viewer: "只读",
};
async function createUser() {
  await run(async () => {
    await post("/users", {
      username: username.value,
      password: password.value,
    });
    username.value = "";
    password.value = "";
    await client.invalidateQueries({ queryKey: ["users"] });
  }, "账号已创建");
}
async function member() {
  await run(async () => {
    await api(`/projects/${session.projectId}/members`, {
      method: "PUT",
      body: JSON.stringify({ username: memberName.value, role: role.value }),
    });
    await client.invalidateQueries({ queryKey: ["members"] });
    await client.invalidateQueries({ queryKey: ["audit"] });
    memberName.value = "";
  }, "项目成员权限已保存");
}
async function removeMember(userId: string) {
  await run(async () => {
    await api(`/projects/${session.projectId}/members/${userId}`, {
      method: "DELETE",
    });
    await client.invalidateQueries({ queryKey: ["members"] });
    await client.invalidateQueries({ queryKey: ["audit"] });
  }, "已移除项目访问权限");
}
</script>
<template>
  <div class="page-head">
    <div>
      <h1>系统设置</h1>
      <span class="muted">服务、模型与项目权限</span>
    </div>
    <el-button @click="client.invalidateQueries({ queryKey: ['capabilities'] })"
      >检查服务状态</el-button
    >
  </div>
  <div class="grid">
    <section class="panel">
      <h2>系统能力</h2>
      <dl v-if="capabilities" class="metric-list">
        <dt>软件 / 数据版本</dt>
        <dd>{{ capabilities.version }} / {{ capabilities.data_version }}</dd>
        <dt>实验影像 / GPS</dt>
        <dd>
          {{ capabilities.geographic.scene_count.toLocaleString() }} /
          {{ capabilities.geographic.gps_count.toLocaleString() }}
        </dd>
        <dt>数据库</dt>
        <dd>{{ capabilities.deployment.database }}</dd>
        <dt>任务执行</dt>
        <dd>{{ capabilities.deployment.worker }}</dd>
        <dt>真实推理</dt>
        <dd>
          {{ capabilities.live_inference.available ? "已连接" : "未连接" }}
        </dd>
        <template v-if="capabilities.live_inference.available">
          <dt>GPU</dt>
          <dd>{{ capabilities.live_inference.device }}</dd>
          <dt>推理作业</dt>
          <dd>
            执行 {{ capabilities.live_inference.running_jobs || 0 }} · 排队
            {{ capabilities.live_inference.queue_depth || 0 }}
          </dd>
        </template>
      </dl>
      <p class="muted">{{ capabilities?.live_inference.reason }}</p>
      <p class="muted">{{ capabilities?.geographic.reason }}</p>
      <a href="/api/v1/openapi.json" target="_blank" rel="noopener"
        >查看 OpenAPI 契约</a
      >
    </section>
    <section class="panel">
      <h2>注册模型</h2>
      <div v-for="m in models" :key="String(m.id)">
        <b>{{ m.name }}</b>
        <p class="small">预处理 {{ m.preprocess_version }} · 单视图 / 四视图</p>
        <p class="mono">增量 SHA256：{{ m.delta_sha256 }}</p>
        <p class="muted small">历史回放 / GPU 推理</p>
      </div>
    </section>
  </div>
  <div class="grid">
    <section class="panel">
      <h2>当前项目成员</h2>
      <el-table :data="members || []"
        ><el-table-column prop="username" label="用户" /><el-table-column
          label="角色"
          ><template #default="{ row }">{{
            roleLabels[row.role]
          }}</template></el-table-column
        ><el-table-column
          v-if="project?.role === 'admin' && !project.archived"
          label="操作"
          width="150"
        >
          <template #default="{ row }">
            <template v-if="row.user_id !== session.user?.id">
              <el-button
                size="small"
                @click="
                  memberName = row.username;
                  role = row.role;
                "
                >编辑</el-button
              >
              <el-popconfirm
                title="移除该成员的项目访问权限？"
                confirm-button-text="移除"
                cancel-button-text="取消"
                @confirm="removeMember(row.user_id)"
              >
                <template #reference
                  ><el-button size="small" :loading="busy"
                    >移除</el-button
                  ></template
                >
              </el-popconfirm>
            </template>
          </template>
        </el-table-column></el-table
      ><el-form
        v-if="project?.role === 'admin' && !project.archived"
        label-position="top"
        style="margin-top: 20px"
        @submit.prevent="member"
        ><el-form-item label="已有用户名"
          ><el-input
            v-model="memberName"
            placeholder="填写已有账号" /></el-form-item
        ><el-form-item label="项目角色"
          ><el-select v-model="role"
            ><el-option
              v-for="(label, key) in roleLabels"
              :key="key"
              :label="label"
              :value="key" /></el-select></el-form-item
        ><el-button type="primary" :loading="busy" native-type="submit"
          >保存成员权限</el-button
        ></el-form
      >
    </section>
    <section v-if="session.user?.is_admin" class="panel">
      <h2>创建用户</h2>
      <el-form label-position="top" @submit.prevent="createUser"
        ><el-form-item label="用户名"
          ><el-input v-model="username" autocomplete="off" /></el-form-item
        ><el-form-item label="初始密码（至少 12 位）"
          ><el-input
            v-model="password"
            type="password"
            autocomplete="new-password"
            show-password /></el-form-item
        ><el-button type="primary" :loading="busy" native-type="submit"
          >创建账号</el-button
        ></el-form
      >
      <p class="muted small">
        账号创建后，分配项目角色才能访问项目资料。系统管理员拥有所有项目权限。
      </p>
      <p class="muted small">
        现有账号：{{ users?.map((u) => u.username).join("、") }}
      </p>
    </section>
  </div>
  <section class="panel">
    <h2>当前项目审计记录</h2>
    <el-table :data="audit || []"
      ><el-table-column prop="action" label="操作" /><el-table-column
        prop="actor"
        label="操作人"
      /><el-table-column
        prop="object_id"
        label="对象 ID"
        show-overflow-tooltip
      /><el-table-column
        prop="request_id"
        label="请求 ID"
        show-overflow-tooltip
      /><el-table-column label="时间"
        ><template #default="{ row }">{{
          fmtTime(row.created_at)
        }}</template></el-table-column
      ></el-table
    >
  </section>
  <PageNavigation v-model="auditPage" :count="audit?.length || 0" :size="50" />
</template>
