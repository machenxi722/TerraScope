<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { loadProjects } from "./api/client";
import { useSession } from "./stores/session";
import AppIcon from "./components/AppIcon.vue";
import { useAction } from "./composables/actions";
const route = useRoute(),
  router = useRouter(),
  session = useSession(),
  client = useQueryClient();
const { run } = useAction();
const { data: projects } = useQuery({
  queryKey: ["projects"],
  queryFn: () => loadProjects(),
  enabled: computed(() => !!session.user),
});
watch(
  projects,
  (rows) => {
    if (rows && !rows.length) session.chooseProject("");
    if (rows?.length && !rows.some((p) => p.id === session.projectId))
      session.chooseProject(rows[0].id);
  },
  { immediate: true },
);
const navigation = [
  ["/projects", "项目概览", "projects"],
  ["/images", "影像资料", "images"],
  ["/tasks", "分析任务", "tasks"],
  ["/experiments", "实验评估", "chart"],
  ["/reports", "报告中心", "report"],
  ["/settings", "系统设置", "settings"],
];
const isWorkbench = computed(() => route.path.startsWith("/workbench"));
async function logout() {
  await run(async () => {
    await session.logout();
    client.clear();
    await router.push("/login");
  });
}
function switchProject(id: string) {
  session.chooseProject(id);
  if (route.path.startsWith("/workbench")) router.push("/images");
}
</script>
<template>
  <router-view v-if="route.path === '/login'" />
  <div v-else class="shell" :class="{ 'workbench-shell': isWorkbench }">
    <header class="topbar">
      <router-link to="/projects" class="brand">
        <span class="brand-symbol"><AppIcon name="globe" :size="29" /></span>
        <span
          >Terra<span class="brand-light">Scope</span
          ><small>洪灾道路调查平台</small></span
        >
      </router-link>
      <div class="project-switch">
        <label for="project-select">当前项目</label
        ><el-select
          id="project-select"
          aria-label="选择项目"
          :model-value="session.projectId"
          @change="switchProject"
          placeholder="选择项目"
          class="project-select"
          ><el-option
            v-for="p in projects"
            :key="p.id"
            :label="p.name + (p.archived ? '（已归档）' : '')"
            :value="p.id"
        /></el-select>
      </div>
      <div class="account-menu">
        <span class="account-name"
          ><AppIcon name="user" :size="16" />{{ session.user?.username }}</span
        >
        <button class="logout-button" @click="logout">退出</button>
      </div>
    </header>
    <nav class="module-nav" aria-label="功能模块">
      <router-link
        v-for="item in navigation"
        :key="item[0]"
        :to="item[0]"
        :aria-label="item[1]"
        :title="item[1]"
        :class="{
          'module-context-active': isWorkbench && item[0] === '/images',
        }"
      >
        <AppIcon :name="item[2]" :size="17" />{{
          isWorkbench ? item[1].slice(0, 2) : item[1]
        }}
      </router-link>
    </nav>
    <div class="body-layout">
      <main :class="{ 'workbench-main': isWorkbench }"><router-view /></main>
    </div>
  </div>
</template>
