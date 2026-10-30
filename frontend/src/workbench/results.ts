export interface DatedResult {
  created_at: number;
  contract: { source_mode: string };
}
/** Match the calendar day displayed in the user's local timezone. */
export function resultDay(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}
export function filterResults<T extends DatedResult>(
  rows: T[],
  source: string,
  day: string,
): T[] {
  return rows.filter(
    (row) =>
      (source === "all" || row.contract.source_mode === source) &&
      (!day || resultDay(row.created_at) === day),
  );
}
