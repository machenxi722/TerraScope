import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { api, loadProjects, type Project } from "../api/client";
import { useSession } from "../stores/session";
export function useProject() {
  const session = useSession();
  const query = useQuery({
    queryKey: ["projects"],
    queryFn: () => loadProjects(),
  });
  const project = computed(() =>
    query.data.value?.find((p) => p.id === session.projectId),
  );
  const canAnalyze = computed(
    () =>
      !!project.value &&
      !project.value.archived &&
      ["admin", "analyst"].includes(project.value.role),
  );
  const canReview = computed(
    () =>
      !!project.value &&
      !project.value.archived &&
      ["admin", "reviewer"].includes(project.value.role),
  );
  const canReport = computed(
    () =>
      !!project.value &&
      !project.value.archived &&
      project.value.role !== "viewer",
  );
  return { session, project, canAnalyze, canReview, canReport };
}
