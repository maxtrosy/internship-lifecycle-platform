import { useEffect, useState } from "react";
import * as api from "../api";
import type { PlacementDossier } from "../api";
import { Alert, EmptyState, Spinner } from "./ui";
import { formatHistoryDate } from "../history";

export default function FacultyAssignmentManager({ dossier, onChanged }: {
  dossier: PlacementDossier;
  onChanged: () => void;
}) {
  const canManage = dossier.capabilities.manage_faculty_assignments;
  const mayConfigure = dossier.capabilities.may_configure_faculty_assignments;
  const canReadHistory = dossier.capabilities.read_faculty_assignment_history;
  const [options, setOptions] = useState<{ id: number; display_name: string }[] | null>(null);
  const [selected, setSelected] = useState("");
  const [busyId, setBusyId] = useState<number | "assign" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!canManage) { setOptions(null); return; }
    let current = true;
    setOptions(null);
    api.listFacultySupervisorOptions(dossier.placement.id)
      .then((rows) => { if (current) setOptions(rows); })
      .catch((cause: unknown) => {
        if (current) setError(cause instanceof Error ? cause.message : "No se pudieron cargar las personas disponibles.");
      });
    return () => { current = false; };
  }, [canManage, dossier.placement.id, attempt]);

  async function assign() {
    const userId = Number(selected);
    if (!Number.isInteger(userId) || userId < 1) return;
    setBusyId("assign"); setError(null); setSuccess(null);
    try {
      await api.assignFacultySupervisor(dossier.placement.id, userId);
      setSelected("");
      setSuccess("Supervisión docente asignada; el cambio quedó en el historial.");
      onChanged();
      setAttempt((value) => value + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo guardar la asignación.");
    } finally { setBusyId(null); }
  }

  async function unassign(userId: number) {
    setBusyId(userId); setError(null); setSuccess(null);
    try {
      await api.unassignFacultySupervisor(dossier.placement.id, userId);
      setSuccess("Asignación docente retirada; el historial se conservó.");
      onChanged();
      setAttempt((value) => value + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo retirar la asignación.");
    } finally { setBusyId(null); }
  }

  if (!canManage && !canReadHistory && !mayConfigure) return null;
  return (
    <div className="faculty-assignment-panel">
      {mayConfigure && !dossier.capabilities.faculty_assignment_authority_configured &&
        <Alert kind="info">La autoridad institucional para asignar supervisión docente no está configurada; no se permiten cambios.</Alert>}
      {canManage && <>
        <p className="muted">La autoridad para asignar o retirar supervisión docente depende de la configuración institucional.</p>
        {error && <Alert kind="error">{error} <button className="btn link" type="button" onClick={() => setAttempt((value) => value + 1)}>Reintentar</button></Alert>}
        {success && <Alert kind="success">{success}</Alert>}
        {options === null && !error && <div className="empty"><Spinner /> Cargando supervisión docente…</div>}
        {options?.length === 0 && <EmptyState message="No hay cuentas activas con rol de supervisión docente." />}
        {!!options?.length && <div className="faculty-assignment-controls">
          <label className="field" htmlFor={`faculty-assignment-${dossier.placement.id}`}>Asignar supervisión docente
            <select id={`faculty-assignment-${dossier.placement.id}`} value={selected} onChange={(event) => setSelected(event.target.value)}>
              <option value="">Selecciona una persona</option>
              {options.filter((person) => !dossier.responsibles.faculty_assignments.some((assignment) => assignment.id === person.id))
                .map((person) => <option key={person.id} value={person.id}>{person.display_name}</option>)}
            </select>
          </label>
          <button className="btn" type="button" disabled={busyId !== null || !selected} onClick={() => void assign()}>
            {busyId === "assign" ? <Spinner /> : "Asignar"}
          </button>
        </div>}
        {dossier.responsibles.faculty_assignments.map((assignment) => (
          <div className="faculty-assignment-row" key={assignment.id}>
            <span>{assignment.display_name}</span>
            <button className="btn secondary" type="button" disabled={busyId !== null}
              onClick={() => void unassign(assignment.id)}>
              {busyId === assignment.id ? <Spinner /> : "Retirar asignación"}
            </button>
          </div>
        ))}
      </>}
      {canReadHistory && <div className="faculty-assignment-history">
        <h3>Historial de supervisión docente</h3>
        {!dossier.responsibles.faculty_assignment_history.length
          ? <EmptyState message="No hay cambios de asignación registrados desde que se habilitó este historial." />
          : <ol className="message-list">{dossier.responsibles.faculty_assignment_history.map((entry, index) => (
            <li key={`${entry.occurred_at}-${index}`}>
              <strong>{entry.action === "ASSIGNED" ? "Asignación registrada" : "Asignación retirada"}</strong>
              <time dateTime={entry.occurred_at}>{formatHistoryDate(entry.occurred_at)}</time>
              <p>{entry.actor_name} · {entry.faculty_name}</p>
            </li>
          ))}</ol>}
      </div>}
    </div>
  );
}
