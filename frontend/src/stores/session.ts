import { defineStore } from "pinia";
import { ref } from "vue";
import { api, post, setCsrf, ApiError, type User } from "../api/client";
export const useSession = defineStore("session", () => {
  const user = ref<User | null>(null);
  const ready = ref(false);
  const projectId = ref(localStorage.getItem("terra_project") || "");
  function chooseProject(id: string) {
    projectId.value = id;
    localStorage.setItem("terra_project", id);
  }
  async function restore() {
    try {
      const data = await api<{ user: User; csrf_token: string }>("/auth/me");
      user.value = data.user;
      setCsrf(data.csrf_token);
    } catch {
      user.value = null;
      setCsrf("");
    }
    ready.value = true;
  }
  async function login(username: string, password: string) {
    const data = await post<{ user: User; csrf_token: string }>("/auth/login", {
      username,
      password,
    });
    user.value = data.user;
    setCsrf(data.csrf_token);
    ready.value = true;
  }
  async function logout() {
    try {
      await post("/auth/logout");
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
    }
    expire();
  }
  function expire() {
    user.value = null;
    setCsrf("");
    chooseProject("");
  }
  return {
    user,
    ready,
    projectId,
    chooseProject,
    restore,
    login,
    logout,
    expire,
  };
});
