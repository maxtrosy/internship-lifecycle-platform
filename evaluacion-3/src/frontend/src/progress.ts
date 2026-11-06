import type { ProgressHoursEntry } from "./api";

export type HoursEntry = { id: number; occurredAt: string; hours: number };

export function hoursFromHistory(events: unknown): HoursEntry[] {
  if (!Array.isArray(events)) return [];
  return (events as Partial<ProgressHoursEntry>[])
    .flatMap((event) => {
      if (typeof event !== "object" || event === null || typeof event.id !== "number" ||
          typeof event.created_at !== "string") return [];
      const rawHours = (event as Record<string, unknown>).hours;
      const hours = typeof rawHours === "number" ? rawHours
        : typeof rawHours === "string" && rawHours.trim() ? Number(rawHours) : NaN;
      return Number.isFinite(hours) && hours > 0
        ? [{ id: event.id, occurredAt: event.created_at, hours }]
        : [];
    })
    .sort((a, b) => b.id - a.id);
}

export function totalHours(entries: HoursEntry[]): number {
  return entries.reduce((total, entry) => total + entry.hours, 0);
}
