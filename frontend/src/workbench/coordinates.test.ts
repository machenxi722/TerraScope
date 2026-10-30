import { describe, it, expect } from "vitest";
import { pixelAt, toMap, toPixel, clampPolygon } from "./coordinates";
describe("原始影像坐标与 OpenLayers 方向变换", () => {
  it("四角和像素中心往返不偏移", () => {
    for (const p of [
      [0, 0],
      [1024, 0],
      [0, 685],
      [1024, 685],
      [511.5, 342.5],
    ])
      expect(toPixel(toMap(p))).toEqual(p);
  });
  it("边界像素查值不访问图外", () => {
    expect(pixelAt([0.5, -0.5], 1024, 685)).toEqual([0, 0]);
    expect(pixelAt([1023.5, -684.5], 1024, 685)).toEqual([1023, 684]);
    expect(pixelAt([1024, 0], 1024, 685)).toBeNull();
    expect(pixelAt([0, -685], 1024, 685)).toBeNull();
    expect(pixelAt([-0.1, 0], 1024, 685)).toBeNull();
  });
  it("圈选约束到原始像素边界", () => {
    expect(
      clampPolygon(
        [
          [-2, -2],
          [1028, 690],
        ],
        1024,
        685,
      ),
    ).toEqual([
      [0, 0],
      [1024, 685],
    ]);
  });
});
