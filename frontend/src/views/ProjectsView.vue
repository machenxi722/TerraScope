<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { api, loadProjects, post, fmtTime, type Project } from "../api/client";
import { useSession } from "../stores/session";
import { useAction } from "../composables/actions";
const session = useSession(),
  router = useRouter(),
  client = useQueryClient(),
  { busy, run } = useAction();
const {
  data: projects,
  isPending,
  error,
} = useQuery({
  queryKey: ["projects"],
  queryFn: () => loadProjects(),
});
const dialog = ref(false),
  editing = ref<Project | null>(null),
  name = ref(""),
  description = ref("");
const { data: activities } = useQuery({
  queryKey: computed(() => ["audit", session.projectId]),
  enabled: computed(() => !!session.projectId),
  queryFn: () =>
    api<{ id: string; action: string; actor: string; created_at: number }[]>(
      `/projects/${session.projectId}/audit`,
    ),
});
function open(p: Project | null = null) {
  editing.value = p;
  name.value = p?.name || "";
  description.value = p?.description || "";
  dialog.value = true;
}
async function save() {
  await run(async () => {
    if (!name.value.trim()) throw new Error("请输入项目名称");
    const body = { name: name.value, description: description.value };
    const p = editing.value
      ? await api<Project>(`/projects/${editing.value.id}`, {
          method: "PATCH",
          body: JSON.stringify({ ...body, archived: editing.value.archived }),
        })
      : await post<Project>("/projects", body);
    session.chooseProject(p.id);
    dialog.value = false;
    await client.invalidateQueries({ queryKey: ["projects"] });
  }, "项目已保存");
}
async function archive(p: Project) {
  await run(
    async () => {
      await api(`/projects/${p.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: p.name,
          description: p.description,
          archived: !p.archived,
        }),
      });
      await client.invalidateQueries({ queryKey: ["projects"] });
    },
    p.archived ? "项目已恢复" : "项目已归档，可随时恢复",
  );
}
async function demo() {
  await run(async () => {
    const p = await post<Project>("/system/demo");
    session.chooseProject(p.id);
    await client.invalidateQueries({ queryKey: ["projects"] });
  }, "示范项目已就绪");
}
function enter(p: Project) {
  session.chooseProject(p.id);
  router.push("/images");
}
</script>
<template>
  <div class="page-head">
    <div>
      <h1>项目概览</h1>
      <span class="muted">影像、分析任务与调查成果</span>
    </div>
    <div class="actions">
      <el-button v-if="session.user?.is_admin" @click="demo" :loading="busy"
        >初始化示范项目</el-button
      ><el-button type="primary" @click="open()">创建项目</el-button>
    </div>
  </div>
  <p v-if="error" class="error">{{ error.message }}</p>
  <p v-if="isPending">正在加载项目…</p>
  <div v-if="!isPending && !projects?.length" class="panel empty">
    暂无项目。创建项目或初始化真实案例。
  </div>
  <div class="grid">
    <section v-for="p in projects" :key="p.id" class="panel">
      <div class="row">
        <h2>{{ p.name }}</h2>
        <el-tag v-if="p.archived" type="info">已归档</el-tag
        ><el-tag v-if="p.is_demo" type="info">示范</el-tag>
      </div>
      <p class="muted">{{ p.description || "—" }}</p>
      <div class="stats">
        <div>
          <div class="stat">{{ p.image_count }}</div>
          影像
        </div>
        <div>
          <div class="stat">{{ p.queued_count }}</div>
          处理中
        </div>
        <div>
          <div class="stat">{{ p.pending_review_count }}</div>
          待复核
        </div>
      </div>
      <div class="actions">
        <el-button type="primary" @click="enter(p)">进入项目</el-button
        ><el-button v-if="p.role === 'admin'" @click="open(p)">编辑</el-button
        ><el-button v-if="p.role === 'admin'" @click="archive(p)">{{
          p.archived ? "恢复" : "归档"
        }}</el-button>
      </div>
    </section>
  </div>
  <section v-if="activities?.length" class="panel">
    <h2>当前项目最近活动</h2>
    <el-table :data="activities.slice(0, 8)"
      ><el-table-column prop="action" label="操作" /><el-table-column
        prop="actor"
        label="操作人"
      /><el-table-column label="时间"
        ><template #default="{ row }">{{
          fmtTime(row.created_at)
        }}</template></el-table-column
      ></el-table
    >
  </section>
  <el-dialog
    v-model="dialog"
    :title="editing ? '编辑项目' : '创建项目'"
    width="500"
    ><el-form label-position="top" @submit.prevent="save"
      ><el-form-item label="项目名称"
        ><el-input
          v-model="name"
          maxlength="120"
          aria-label="项目名称" /></el-form-item
      ><el-form-item label="事件说明"
        ><el-input
          v-model="description"
          type="textarea"
          :rows="4"
          maxlength="5000" /></el-form-item
      ><el-button type="primary" native-type="submit" :loading="busy"
        >保存项目</el-button
      ></el-form
    ></el-dialog
  >
</template>
