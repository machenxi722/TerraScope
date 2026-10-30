export function toMap([x, y]: number[]): [number, number] {
  return [x, -y];
}
export function toPixel([x, y]: number[]): [number, number] {
  return [x, -y];
}
export function pixelAt(
  coordinate: number[],
  width: number,
  height: number,
): [number, number] | null {
  const [x, y] = toPixel(coordinate);
  if (x < 0 || y < 0 || x >= width || y >= height) return null;
  return [Math.floor(x), Math.floor(y)];
}
export function clampPolygon(
  points: number[][],
  width: number,
  height: number,
): [number, number][] {
  return points.map((p) => [
    Math.min(width, Math.max(0, p[0])),
    Math.min(height, Math.max(0, p[1])),
  ]);
}
