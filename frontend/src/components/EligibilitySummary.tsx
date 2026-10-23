import type { EligibilityPresentation } from "../eligibility";
import { presentEligibility } from "../eligibility";
import { Badge } from "./ui";

export default function EligibilitySummary({ value, showCriteria = true }: { value: unknown; showCriteria?: boolean }) {
  const eligibility: EligibilityPresentation = presentEligibility(value);
  const criteria = showCriteria ? eligibility.criteria : [];
  const hasDetails = criteria.length > 0 || eligibility.reasons.length > 0;
  return (
    <div className="eligibility-cell">
      <Badge state={eligibility.state === "unknown" ? "UNKNOWN" : eligibility.state === "eligible" ? "ELIGIBLE" : "INELIGIBLE"}>
        {eligibility.label}
      </Badge>
      {hasDetails && (
        <details className="eligibility-details">
          <summary>{eligibility.reasons.length > 0 ? "Ver detalles" : "Ver criterios"}</summary>
          {criteria.length > 0 && (
            <dl>
              {criteria.map((criterion) => (
                <div key={criterion.label}>
                  <dt>{criterion.label}</dt>
                  <dd>{criterion.value}</dd>
                </div>
              ))}
            </dl>
          )}
          {eligibility.reasons.length > 0 && (
            <div>
              <strong>Motivos informados</strong>
              <ul>
                {eligibility.reasons.map((reason, index) => <li key={`${index}-${reason}`}>{reason}</li>)}
              </ul>
            </div>
          )}
        </details>
      )}
    </div>
  );
}
