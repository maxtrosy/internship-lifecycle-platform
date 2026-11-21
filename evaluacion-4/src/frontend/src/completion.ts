import type { CompletionRequirement } from "./api";

export function completionRequirementsSatisfied(
  configured: boolean,
  requirements: readonly CompletionRequirement[] | null,
): boolean {
  return configured && requirements !== null && requirements.every((item) => !item.mandatory || item.satisfied);
}
