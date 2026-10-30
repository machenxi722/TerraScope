import { createApp } from "vue";
import { createPinia } from "pinia";
import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import "ol/ol.css";
import "./style.css";
import App from "./App.vue";
import { router } from "./router";
import { setUnauthorizedHandler } from "./api/client";
import { useSession } from "./stores/session";
const pinia = createPinia();
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 2000 },
  },
});
setUnauthorizedHandler(() => {
  const session = useSession(pinia);
  if (!session.user) return;
  const redirect = router.currentRoute.value.fullPath;
  session.expire();
  queryClient.clear();
  void router.replace({ path: "/login", query: { redirect } });
});
createApp(App)
  .use(pinia)
  .use(router)
  .use(VueQueryPlugin, {
    queryClient,
  })
  .use(ElementPlus, { locale: zhCn })
  .mount("#app");
