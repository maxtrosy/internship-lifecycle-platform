import { useState, type FormEvent } from "react";
import * as api from "../api";
import type { PlacementDossier } from "../api";
import { Alert, BentoCard, EmptyState, Spinner } from "./ui";
import { formatHistoryDate } from "../history";

type Props = { dossier: PlacementDossier; onChanged: () => void };

export default function PlacementWorkPlan({ dossier, onChanged }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const canRead = dossier.capabilities.read_work_plan;
  const canAssign = dossier.capabilities.assign_work_plan_item;

  if (!canRead && !canAssign) return null;

  async function assign(event: FormEvent) {
    event.preventDefault();
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
            </li>
          ))}
        </ol>
      )}
      {canRead && dossier.placement.state === "CLOSED" && (
        <p className="muted">La práctica está cerrada. El plan permanece disponible para consulta.</p>
      )}
      {canAssign && (
        <form className="follow-up-form" onSubmit={(event) => void assign(event)}>
          <label className="field">
            Actividad
            <input
              value={title}
              maxLength={160}
              required
              aria-label="Nombre de la actividad"
              onChange={(event) => setTitle(event.currentTarget.value)}
            />
          </label>
          <label className="field">
            Descripción
            <textarea
              value={description}
              maxLength={3000}
              required
              rows={4}
              aria-label="Descripción de la actividad"
              onChange={(event) => setDescription(event.currentTarget.value)}
            />
          </label>
          <button className="btn" type="submit" disabled={busy || !title.trim() || !description.trim()}>
            {busy ? <Spinner /> : "Asignar actividad"}
          </button>
        </form>
      )}
    </BentoCard>
  );
}
