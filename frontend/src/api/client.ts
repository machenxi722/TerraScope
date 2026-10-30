import type { components } from "./schema";
export type User = components["schemas"]["UserOut"];
export type Project = components["schemas"]["ProjectOut"];
export type ImageAsset = components["schemas"]["ImageOut"];
export type Task = components["schemas"]["TaskOut"];
export type Review = components["schemas"]["ReviewOut"];
export type Report = components["schemas"]["ReportOut"];
export type Annotation = components["schemas"]["Annotation"];
export type Metrics = components["schemas"]["MetricsOut"];
export type Evaluation = components["schemas"]["EvaluationOut"];
export type Contract = components["schemas"]["PredictionContract"];
export type Prediction = components["schemas"]["PredictionOut"];
export interface Capabilities {
  version: string;
  data_version: string;
  live_inference: {
    available: boolean;
    reason: string;
    state?: string;
    device?: string;
    queue_depth?: number;
    running_jobs?: number;
  };
  geographic: {
    available: boolean;
    reason: string;
    gps_count: number;
    scene_count: number;
  };
  deployment: { database: string; worker: string };
}
let csrfToken = "";
let onUnauthorized: (() => void) | undefined;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}
export function setCsrf(value: string) {
  csrfToken = value;
}
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (options.method && !["GET", "HEAD"].includes(options.method))
    headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch("/api/v1" + path, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/"))
      onUnauthorized?.();
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      error.code || "HTTP_ERROR",
      error.message || `请求失败 (${response.status})`,
      error.request_id,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export async function loadPredictions(imageId: string): Promise<Prediction[]> {
  const rows: Prediction[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await api<Prediction[]>(
      `/predictions?image_id=${encodeURIComponent(imageId)}&offset=${offset}&limit=100`,
    );
    rows.push(...page);
    if (page.length < 100)
      return [...new Map(rows.map((p) => [p.id, p])).values()];
  }
}
export function post<T>(path: string, body?: unknown, key?: string) {
  return api<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: key ? { "Idempotency-Key": key } : {},
  });
}
export const assetUrl = (id: string, inline = true) =>
  `/api/v1/assets/${encodeURIComponent(id)}/download?inline=${inline}`;
export const newKey = () => crypto.randomUUID();
export async function loadProjects(): Promise<Project[]> {
  const rows: Project[] = [];
  for (let offset = 0; ; offset += 200) {
    const page = await api<Project[]>(`/projects?offset=${offset}&limit=200`);
    rows.push(...page);
    if (page.length < 200)
      return [...new Map(rows.map((p) => [p.id, p])).values()];
  }
}
export const sourceLabels: Record<string, string> = {
  historical_replay: "历史结果",
  live_inference: "本次推理",
  manual_import: "外部导入",
};
export const decisionLabels: Record<string, string> = {
  confirmed: "确认结果",
  returned: "退回分析",
  needs_investigation: "需补充调查",
};
export const statusLabels: Record<string, string> = {
  QUEUED: "排队中",
  VALIDATING: "校验输入",
  LOADING_ARTIFACT: "加载结果",
  INFERENCING: "推理中",
  POSTPROCESSING: "后处理",
  SUCCEEDED: "已完成",
  FAILED: "失败",
  CANCELED: "已取消",
  CANCEL_REQUESTED: "等待安全取消",
  RUNNING: "生成中",
};
export const fmtTime = (value: number) =>
  new Date(value * 1000).toLocaleString("zh-CN", { hour12: false });
export const percent = (value: number | null | undefined, ratio = false) =>
  value == null ? "—" : `${(value * (ratio ? 100 : 1)).toFixed(2)}%`;
