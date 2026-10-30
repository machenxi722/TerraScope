import { createRouter, createWebHistory } from "vue-router";
import { useSession } from "./stores/session";
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("./views/LoginView.vue") },
    { path: "/", redirect: "/projects" },
    { path: "/projects", component: () => import("./views/ProjectsView.vue") },
    { path: "/images", component: () => import("./views/ImagesView.vue") },
    { path: "/tasks", component: () => import("./views/TasksView.vue") },
    {
      path: "/workbench/:imageId",
      component: () => import("./views/WorkbenchView.vue"),
    },
    {
      path: "/experiments",
      component: () => import("./views/ExperimentsView.vue"),
    },
    { path: "/reports", component: () => import("./views/ReportsView.vue") },
    { path: "/settings", component: () => import("./views/SettingsView.vue") },
    { path: "/:pathMatch(.*)*", redirect: "/projects" },
  ],
});
router.beforeEach(async (to) => {
  const session = useSession();
  if (!session.ready) await session.restore();
  if (!session.user && to.path !== "/login")
    return { path: "/login", query: { redirect: to.fullPath } };
  if (session.user && to.path === "/login") return "/projects";
});
