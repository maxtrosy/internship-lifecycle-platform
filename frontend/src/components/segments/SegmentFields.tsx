import type { ReactNode } from "react";
import type { SegmentOption } from "../../api";
import { MODALITY_LABELS, type SegmentDraft } from "../../segments";

/** Shared fields for planning a segment and for the destination of a transfer. */
export function SegmentFields({ draft, setDraft, options, idPrefix }: {
  draft: SegmentDraft;
  setDraft: (next: SegmentDraft) => void;
  options: SegmentOption[];
  idPrefix: string;
}) {
  const supervisors = options.find((option) => String(option.id) === draft.host_org_id)?.supervisors ?? [];
  const field = (key: keyof SegmentDraft, label: string, input: ReactNode) => (
    <div className="field"><label htmlFor={`${idPrefix}-${key}`}>{label}</label>{input}</div>
  );
  const set = (key: keyof SegmentDraft) => (event: { target: { value: string } }) =>
    setDraft({ ...draft, [key]: event.target.value, ...(key === "host_org_id" ? { workplace_supervisor_id: "" } : {}) });
  return (
    <div className="segment-form-grid">
      {field("host_org_id", "Organización", (
        <select id={`${idPrefix}-host_org_id`} required value={draft.host_org_id} onChange={set("host_org_id")}>
          <option value="">Selecciona…</option>
          {options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
        </select>
      ))}
      {field("workplace_supervisor_id", "Supervisor laboral", (
        <select id={`${idPrefix}-workplace_supervisor_id`} required value={draft.workplace_supervisor_id}
          onChange={set("workplace_supervisor_id")} disabled={!draft.host_org_id}>
          <option value="">Selecciona…</option>
          {supervisors.map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}
        </select>
      ))}
      {field("unit", "Unidad o área", <input id={`${idPrefix}-unit`} required maxLength={160} value={draft.unit} onChange={set("unit")} />)}
      {field("modality", "Modalidad", (
        <select id={`${idPrefix}-modality`} required value={draft.modality} onChange={set("modality")}>
          <option value="">Selecciona…</option>
          {Object.entries(MODALITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      ))}
      {field("start_date", "Inicio", <input id={`${idPrefix}-start_date`} type="date" required value={draft.start_date} onChange={set("start_date")} />)}
      {field("end_date", "Fin", <input id={`${idPrefix}-end_date`} type="date" required value={draft.end_date} onChange={set("end_date")} />)}
      {field("expected_hours", "Horas esperadas (opcional)", (
        <input id={`${idPrefix}-expected_hours`} type="number" min="0.5" step="0.5" value={draft.expected_hours} onChange={set("expected_hours")} />
      ))}
      <div className="field segment-form-wide"><label htmlFor={`${idPrefix}-responsibilities`}>Responsabilidades</label>
        <textarea id={`${idPrefix}-responsibilities`} required maxLength={5000} rows={3} value={draft.responsibilities} onChange={set("responsibilities")} />
      </div>
    </div>
  );
}
