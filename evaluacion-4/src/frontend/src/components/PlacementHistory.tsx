import { useEffect, useState } from "react";
import * as api from "../api";
import type { PlacementHistoryEvent } from "../api";
import ActivityTimeline from "./ActivityTimeline";
import { Alert, Spinner } from "./ui";

export default function PlacementHistory({ placementId }: { placementId: number }) {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<PlacementHistoryEvent[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const panelId = `placement-history-${placementId}`;

  useEffect(() => {
    if (!open || events !== null) return;
    let current = true;
    setLoading(true);
    setError(false);
    api.listPlacementHistory(placementId)
      .then((result) => { if (current) setEvents(result); })
      .catch(() => { if (current) setError(true); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [attempt, events, open, placementId]);

  return (
    <section className="placement-history">
      <button
        className="btn secondary"
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? "Ocultar historial" : "Ver actividad de la práctica"}
      </button>
      <div id={panelId} className="placement-history-panel" aria-label="Actividad de la práctica" hidden={!open}>
        {open && <>
          <p className="muted">Acciones registradas durante esta práctica.</p>
          {loading && <div className="empty"><Spinner /> Cargando historial…</div>}
          {error && (
            <Alert kind="error">
              No fue posible cargar el historial. <button className="btn link" type="button" onClick={() => setAttempt((value) => value + 1)}>Reintentar</button>
            </Alert>
          )}
          {events && <ActivityTimeline events={events} />}
        </>}
      </div>
    </section>
  );
}
