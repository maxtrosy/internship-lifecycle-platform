import { useEffect, useState } from "react";
import * as api from "../api";
import type { UserNotification } from "../api";
import type { SectionId } from "./Layout";
import { Alert, BentoCard, EmptyState, PageHeader, Spinner } from "./ui";
import { formatHistoryDate } from "../history";

type Props = { onNavigate: (section: SectionId) => void };

export function notificationTitle(category: UserNotification["category"]): string {
  const labels: Record<UserNotification["category"], string> = {
    APPLICATION_SUBMITTED: "Nueva postulación en una oportunidad relacionada",
    APPLICATION_SELECTED: "Se actualizó una selección de práctica",
    DOCUMENT_ACTIVITY: "Cambió el estado de un documento",
    PLACEMENT_ACTIVATED: "La práctica fue activada",
    PROGRESS_REPORTED: "Se registró un avance de práctica",
    EVALUATION_SUBMITTED: "Se registró una evaluación narrativa",
    INCIDENT_REPORTED: "Se reportó una situación en la práctica",
    CHANGE_REPORTED: "Se reportó un cambio en la práctica",
    PLACEMENT_COMPLETED: "Se confirmó la finalización de la práctica",
    PLACEMENT_CLOSED: "La práctica fue cerrada",
    MESSAGE_RECEIVED: "Hay un nuevo mensaje en una conversación de práctica",
    OPPORTUNITY_REVIEW: "Una oportunidad requiere una decisión institucional",
    OPPORTUNITY_PUBLISHED: "Hay una nueva oportunidad publicada en tu programa",
    OPPORTUNITY_CLOSED: "Una oportunidad relacionada fue cerrada",
  };
  return labels[category];
}

export default function NotificationInbox({ onNavigate }: Props) {
  const [rows, setRows] = useState<UserNotification[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    setRows(null);
    setError(null);
    api.listNotifications()
      .then((items) => { if (current) setRows(items); })
      .catch((cause: unknown) => {
        if (current) setError(cause instanceof Error ? cause.message : "No fue posible cargar las notificaciones.");
      });
    return () => { current = false; };
  }, [attempt]);

  async function open(item: UserNotification) {
    setBusyId(item.id);
    setError(null);
    try {
      if (!item.is_read) {
        await api.markNotificationRead(item.id);
        setRows((current) => current?.map((row) => row.id === item.id ? { ...row, is_read: true } : row) ?? null);
      }
      if (item.placement_id !== null) {
        sessionStorage.setItem("dh05:open-placement", String(item.placement_id));
        onNavigate("dossier");
      } else {
        if (item.opportunity_id !== null) sessionStorage.setItem("dh05:open-opportunity", String(item.opportunity_id));
        onNavigate("opportunities");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible abrir el elemento relacionado.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page-stack notification-page">
      <PageHeader eyebrow="ACTIVIDAD" title="Notificaciones" description="Avisos persistidos de oportunidades y prácticas relacionadas con tu cuenta." />
      {error && <Alert kind="error">{error} <button className="btn link" type="button" onClick={() => setAttempt((value) => value + 1)}>Reintentar</button></Alert>}
      <BentoCard variant="content" title="Bandeja" description="Los avisos no contienen detalles de documentos, evaluaciones o incidentes.">
        {rows === null && !error && <div className="empty"><Spinner /> Cargando notificaciones…</div>}
        {rows?.length === 0 && <EmptyState message="No tienes notificaciones todavía." />}
        {!!rows?.length && <ol className="notification-list">
          {rows.map((item) => (
            <li key={item.id} className={item.is_read ? "notification-item read" : "notification-item unread"}>
              <div className="notification-copy">
                <strong>{notificationTitle(item.category)}</strong>
                <time dateTime={item.created_at}>{formatHistoryDate(item.created_at)}</time>
                <span>{item.is_read ? "Leída" : "Sin leer"}</span>
              </div>
              <button className="btn secondary" type="button" disabled={busyId === item.id}
                onClick={() => void open(item)}>
                {busyId === item.id ? <Spinner /> : item.placement_id !== null ? "Abrir expediente" : "Abrir oportunidad"}
              </button>
            </li>
          ))}
        </ol>}
      </BentoCard>
    </div>
  );
}
