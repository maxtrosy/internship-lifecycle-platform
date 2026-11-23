import type { PlacementDossier } from "../../api";
import { Icon } from "../ui";
import { formatCalendarDate, formatHistoryDate } from "../../history";
import { RECOGNITION_LABELS } from "../../segments";

/** Read-only record of approved transfers between segments. */
export function SegmentTransfers({ pid, transfers }: { pid: number; transfers: NonNullable<PlacementDossier["transfers"]> }) {
  const localDate = (value: string | null | undefined) => formatCalendarDate(value, "—");
  return (
    <>
    {transfers.length > 0 && (
      <section className="segment-transfers" aria-labelledby={`transfers-${pid}`}>
        <h3 id={`transfers-${pid}`}>Transferencias</h3>
        <ol className="transfer-list">
          {transfers.map((transfer) => (
            <li key={transfer.id}>
              <div className="transfer-route">
                <span>Segmento {transfer.from_sequence_no}</span>
                <Icon name="arrow" className="transfer-arrow" />
                <span>Segmento {transfer.to_sequence_no}</span>
                <span className="transfer-sr sr-only">: transferencia</span>
              </div>
              <dl className="transfer-facts">
                <div><dt>Efecto</dt><dd>{localDate(transfer.effective_date)}</dd></div>
                <div><dt>Aprobada por</dt><dd>{transfer.approved_by} · {formatHistoryDate(transfer.approved_at)}</dd></div>
                <div><dt>Trabajo previo</dt><dd>{RECOGNITION_LABELS[transfer.prior_work_treatment]}</dd></div>
              </dl>
              <p className="segment-reason"><strong>Motivo:</strong> {transfer.reason_shared}</p>
              {transfer.reason_internal && <p className="segment-internal"><strong>Motivo confidencial:</strong> {transfer.reason_internal}</p>}
            </li>
          ))}
        </ol>
      </section>
    )}
    </>
  );
}
