import { describe, it, expect } from "vitest";
import { percent, sourceLabels, statusLabels } from "./client";
describe("界面证据状态", () => {
  it("未定义准确性指标显示空缺，零覆盖率仍显示零", () => {
    expect(percent(null, true)).toBe("—");
    expect(percent(0)).toBe("0.00%");
    expect(percent(0.7335, true)).toBe("73.35%");
  });
  it("三个来源标签互不混淆，取消申请不显示完成", () => {
    expect(new Set(Object.values(sourceLabels)).size).toBe(3);
    expect(sourceLabels.historical_replay).toBe("历史结果");
    expect(statusLabels.CANCEL_REQUESTED).not.toBe(statusLabels.CANCELED);
  });
});

import { afterEach, vi } from "vitest";
import { api, loadPredictions, setUnauthorizedHandler } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(() => {});
});
describe("接口连接", () => {
  it("结果超过一页时继续读取旧版本", async () => {
    const first = Array.from({ length: 100 }, (_, i) => ({ id: String(i) }));
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(first)))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "oldest" }])));
    vi.stubGlobal("fetch", fetcher);
    const rows = await loadPredictions("scene");
    expect(rows).toHaveLength(101);
    expect(rows[100].id).toBe("oldest");
    expect(fetcher.mock.calls[1][0]).toContain("offset=100");
  });
  it("业务接口的 401 通知会话失效，登录失败保留表单", async () => {
    const expired = vi.fn();
    setUnauthorizedHandler(expired);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation(() =>
          Promise.resolve(
            new Response(
              JSON.stringify({ code: "UNAUTHENTICATED", message: "请登录" }),
              { status: 401 },
            ),
          ),
        ),
    );
    await expect(api("/projects")).rejects.toMatchObject({ status: 401 });
    expect(expired).toHaveBeenCalledTimes(1);
    await expect(api("/auth/login", { method: "POST" })).rejects.toMatchObject({
      status: 401,
    });
    expect(expired).toHaveBeenCalledTimes(1);
  });
});
