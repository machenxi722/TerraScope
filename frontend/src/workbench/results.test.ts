import { describe, expect, it } from "vitest";
import { filterResults, resultDay } from "./results";

describe("结果时间与数据源筛选", () => {
  const today = new Date(2026, 9, 17, 0, 5).getTime() / 1000;
  const yesterday = new Date(2026, 9, 16, 23, 55).getTime() / 1000;
  const rows = [
    {
      id: "a",
      created_at: today,
      contract: { source_mode: "historical_replay" },
    },
    { id: "b", created_at: today, contract: { source_mode: "manual_import" } },
    {
      id: "c",
      created_at: yesterday,
      contract: { source_mode: "historical_replay" },
    },
  ];
  it("uses local calendar boundaries and intersects source with date", () => {
    expect(resultDay(today)).toBe("2026-10-17");
    expect(
      filterResults(rows, "historical_replay", "2026-10-17").map((r) => r.id),
    ).toEqual(["a"]);
  });
  it("keeps all results when cleared and returns an empty list without mutating rows", () => {
    expect(filterResults(rows, "all", "")).toEqual(rows);
    expect(filterResults(rows, "live_inference", "2026-10-17")).toEqual([]);
    expect(rows).toHaveLength(3);
  });
});
