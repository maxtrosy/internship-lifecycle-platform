import type { VisiblePlacement } from "./api";

export type RelatedPlacementsState = "loading" | "error" | "empty" | "ready";

export function getRelatedPlacementsState(
  placements: readonly VisiblePlacement[] | null,
  loading: boolean,
  failed: boolean,
): RelatedPlacementsState {
  if (loading) return "loading";
  if (failed) return "error";
  if (placements === null) return "loading";
  return placements.length === 0 ? "empty" : "ready";
}
