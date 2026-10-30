import { ref } from "vue";
import { ElMessage } from "element-plus";
import { ApiError } from "../api/client";
export function useAction() {
  const busy = ref(false);
  const error = ref("");
  async function run<T>(
    fn: () => Promise<T>,
    success?: string,
  ): Promise<T | undefined> {
    busy.value = true;
    error.value = "";
    try {
      const value = await fn();
      if (success) ElMessage.success(success);
      return value;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "操作失败";
      if (e instanceof ApiError && e.requestId)
        error.value += `（请求 ${e.requestId.slice(0, 12)}）`;
      ElMessage.error(error.value);
    } finally {
      busy.value = false;
    }
  }
  return { busy, error, run };
}
