import { useState, type FormEvent } from "react";
import * as api from "../api";
import type { PlacementDossier } from "../api";
import { Alert, BentoCard, EmptyState, Spinner } from "./ui";
import { formatHistoryDate } from "../history";
import { Field, useFieldErrors } from "./Field";

type Props = { dossier: PlacementDossier; onChanged: () => void };

export default function PlacementWorkPlan({ dossier, onChanged }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const canRead = dossier.capabilities.read_work_plan;
  const canAssign = dossier.capabilities.assign_work_plan_item;
  const formId = `work-plan-${dossier.placement.id}`;
  const fields = useFieldErrors<"title" | "description">((key) => `${formId}-${key}`);

  if (!canRead && !canAssign) return null;

  async function assign(event: FormEvent) {
    event.preventDefault();
    if (!fields.report({
      ...(title.trim() ? {} : { title: "Escribe el nombre de la actividad." }),
      ...(description.trim() ? {} : { description: "Describe la actividad asignada." }),
    })) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api.assignWorkPlanItem(dossier.placement.id, title, description);
      setTitle("");
      setDescription("");
      setNotice("Actividad incorporada al plan de trabajo.");
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible guardar la actividad.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <BentoCard
      variant="content"
      className="dossier-wide"
      title="Plan de trabajo"
      description="Actividades narrativas asignadas por la supervisión laboral. No registran fechas límite ni calificaciones."
    >
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      {canRead && dossier.work_plan?.length === 0 && (
        <EmptyState message="Todavía no hay actividades asignadas." />
      )}
      {canRead && dossier.work_plan && dossier.work_plan.length > 0 && (
        <ol className="follow-up-list work-plan-list">
          {dossier.work_plan.map((item) => (
            <li key={item.revision}>
              <div className="row">
                <strong>{item.title}</strong>
                <time dateTime={item.assigned_at}>{formatHistoryDate(item.assigned_at)}</time>
              </div>
              <p className="dossier-preserve-text">{item.description}</p>
              <span className="muted">Asignada por {item.assigned_by}</span>
              {typeof item.version_no === "number" && <span className="muted">Versión vigente al asignar: v{item.version_no}</span>}
            </li>
          ))}
        </ol>
      )}
      {canRead && dossier.placement.state === "CLOSED" && (
        <p className="muted">La práctica está cerrada. El plan permanece disponible para consulta.</p>
      )}
      {canAssign && (
        <form className="follow-up-form" noValidate onSubmit={(event) => void assign(event)}>
          <Field id={`${formId}-title`} label="Nombre de la actividad" error={fields.errors.title}>
            <input value={title} maxLength={160} required
              onChange={(event) => { setTitle(event.currentTarget.value); fields.clear("title"); }} />
          </Field>
          <Field id={`${formId}-description`} label="Descripción de la actividad" error={fields.errors.description}>
            <textarea value={description} maxLength={3000} required rows={4}
              onChange={(event) => { setDescription(event.currentTarget.value); fields.clear("description"); }} />
          </Field>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? <Spinner /> : "Asignar actividad"}
          </button>
        </form>
      )}
    </BentoCard>
  );
}
