import type { PlacementHistoryEvent } from "../api";
import { formatHistoryAction, formatHistoryDate } from "../history";

export default function ActivityTimeline({ events }: { events: PlacementHistoryEvent[] }) {
  if (events.length === 0) return <p className="muted">Todavía no hay actividad registrada.</p>;
  return (
    <ol className="placement-history-list">
      {events.map((event, index) => (
        <li key={`${event.occurred_at}-${event.action}-${index}`}>
          <span className="placement-history-marker" aria-hidden="true" />
          <div>
            <strong>{formatHistoryAction(event.action)}</strong>
            <time dateTime={event.occurred_at}>{formatHistoryDate(event.occurred_at)}</time>
          </div>
        </li>
      ))}
    </ol>
  );
}
