export type EligibilityState = "eligible" | "ineligible" | "unknown";

export type EligibilityPresentation = {
  state: EligibilityState;
  label: "Elegible" | "No elegible" | "Estado no disponible";
  criteria: { label: string; value: number }[];
  reasons: string[];
  hasDetails: boolean;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseStringList(value: string): string[] | null {
  const trimmed = value.trim();
  if (trimmed === "[]") return [];
  if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) return null;
  const inner = trimmed.slice(1, -1).trim();
  if (!inner) return [];
  const values = inner.split(",").map((part) => part.trim().replace(/^(?:'([^']*)'|"([^"]*)")$/, "$1$2"));
  return values.every(Boolean) ? values : null;
}

function presentReason(reason: string): string {
  const threshold = /^(credits|academic_level)\s+(None|null|-?\d+(?:\.\d+)?)\s*<\s*(-?\d+(?:\.\d+)?)$/i.exec(reason.trim());
  if (threshold) {
    const current = threshold[2] === "None" || threshold[2] === "null" ? "no disponible" : threshold[2];
    const required = threshold[3];
    return threshold[1].toLowerCase() === "credits"
      ? `Créditos: ${current}; mínimo exigido: ${required}.`
      : `Nivel académico: ${current}; mínimo exigido: ${required}.`;
  }

  const program = /^program\s+(.+?)\s+not in\s+(\[.*\])$/i.exec(reason.trim());
  if (program) {
    const allowed = parseStringList(program[2]);
    if (allowed) return `El programa ${program[1]} no está entre los admitidos: ${allowed.join(", ") || "ninguno"}.`;
  }

  const prerequisites = /^missing prerequisites\s+(\[.*\])$/i.exec(reason.trim());
  if (prerequisites) {
    const missing = parseStringList(prerequisites[1]);
    if (missing) return `Prerrequisitos faltantes: ${missing.join(", ") || "ninguno"}.`;
  }

  // Keep backend-provided reasons intact when there is no verified translation.
  return reason;
}

export function presentEligibility(value: unknown): EligibilityPresentation {
  if (!isRecord(value)) {
    return { state: "unknown", label: "Estado no disponible", criteria: [], reasons: [], hasDetails: false };
  }

  const result = typeof value.result === "string" ? value.result.trim().toUpperCase() : "";
  const state: EligibilityState = result === "ELIGIBLE"
    ? "eligible"
    : result === "INELIGIBLE" || result === "NOT_ELIGIBLE"
      ? "ineligible"
      : "unknown";

  const inputs = isRecord(value.inputs) ? value.inputs : {};
  const criteria: EligibilityPresentation["criteria"] = [];
  if (typeof inputs.credits === "number" && Number.isFinite(inputs.credits)) {
    criteria.push({ label: "Créditos", value: inputs.credits });
  }
  if (typeof inputs.academic_level === "number" && Number.isFinite(inputs.academic_level)) {
    criteria.push({ label: "Nivel académico", value: inputs.academic_level });
  }

  const reasons = Array.isArray(value.reasons)
    ? value.reasons.filter((reason): reason is string => typeof reason === "string" && reason.trim().length > 0)
      .map(presentReason)
    : [];

  const labels = {
    eligible: "Elegible",
    ineligible: "No elegible",
    unknown: "Estado no disponible",
  } as const;
  return { state, label: labels[state], criteria, reasons, hasDetails: criteria.length > 0 || reasons.length > 0 };
}
