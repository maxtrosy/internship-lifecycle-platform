import type { PlacementDossier } from "../../api";
import { RECOGNITION_LABELS, formatHours, hoursOverview } from "../../segments";

/** Consolidated hours by review state, plus a per-segment breakdown when there is more than one segment. */
export function SegmentHours({ dossier }: { dossier: PlacementDossier }) {
  const overview = hoursOverview(dossier.hours_summary);
  const hourRows = dossier.hours_summary?.segments ?? [];
  return (
    <>
      {overview && (
        <div className="segment-hours-overview" aria-label="Resumen de horas por estado">
          <div><span>Horas reportadas</span><strong>{formatHours(overview.reported)} h</strong></div>
          <div><span>Horas aceptadas{dossier.hours_summary?.scope === "SEGMENT" ? " (tu segmento)" : " consolidadas"}</span><strong>{formatHours(overview.accepted)} h</strong></div>
          <div><span>Pendientes de revisión</span><strong>{formatHours(overview.pending)} h</strong></div>
        </div>
      )}

      {hourRows.length > 1 && (
        <div className="table-scroll segment-hours-table" tabIndex={0} role="region" aria-label="Horas por segmento">
          <table>
            <caption className="sr-only">Horas por segmento y estado de revisión</caption>
            <thead>
              <tr>
                <th scope="col">Segmento</th>
                <th scope="col" className="num">Reportadas</th>
                <th scope="col" className="num">Pendientes</th>
                <th scope="col" className="num">Aceptadas</th>
                <th scope="col" className="num">Rechazadas</th>
                <th scope="col" className="num">En disputa</th>
                <th scope="col">Cómputo</th>
              </tr>
            </thead>
            <tbody>
              {hourRows.map((row, index) => (
                <tr key={row.segment_id ?? `none-${index}`}>
                  <th scope="row">{row.sequence_no === null ? "Sin segmento" : `Segmento ${row.sequence_no}`}</th>
                  <td className="num">{formatHours(row.reported)} h</td>
                  <td className="num">{formatHours(row.pending)} h</td>
                  <td className="num">{formatHours(row.accepted)} h</td>
                  <td className="num">{formatHours(row.rejected)} h</td>
                  <td className="num">{formatHours(row.disputed)} h</td>
                  <td>{row.counts_toward_total ? "Cuenta para el total" : row.work_recognition ? RECOGNITION_LABELS[row.work_recognition] : "No cuenta para el total"}</td>
                </tr>
              ))}
            </tbody>
            {overview && (
              <tfoot>
                <tr>
                  <th scope="row">Total de la práctica</th>
                  <td className="num">{formatHours(overview.reported)} h</td>
                  <td className="num">{formatHours(overview.pending)} h</td>
                  <td className="num">{formatHours(overview.accepted)} h</td>
                  <td className="num" colSpan={2} />
                  <td>Solo horas aceptadas computables</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </>
  );
}
