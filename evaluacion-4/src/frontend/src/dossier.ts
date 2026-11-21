import type { ProgressHoursEntry } from "./api";

export function canDisplayDossierHours(
  canReadHours: boolean,
  hours: ProgressHoursEntry[] | null,
): boolean {
  return canReadHours && hours !== null;
}
