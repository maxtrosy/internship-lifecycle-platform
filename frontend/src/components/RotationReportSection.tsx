import { useEffect, useState } from "react";
import * as api from "../api";
import type { RotationReport } from "../api";
import { RECOGNITION_LABELS, SEGMENT_STATUS_LABELS } from "../segments";
import { Alert, Badge, BentoCard, EmptyState, Spinner } from "./ui";

type Props = { programId?: number; organizationId?: number; placementState?: string };

const hoursFormat = new Intl.NumberFormat("es", { maximumFractionDigits: 1 });

/** CR-05 aggregates (rotations, transfers, interruptions, accepted hours,
 * missing evaluations, pending consolidations). Same scope as the
 * operational report; it never shows names, reasons or individual entries. */
export default function RotationReportSection({ programId, organizationId, placementState }: Props) {
  const [data, setData] = useState<RotationReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    setError(null);
    api.getRotationReports({
      ...(programId ? { program_id: programId } : {}),
      ...(organizationId ? { organization_id: organizationId } : {}),
      ...(placementState ? { placement_state: placementState } : {}),
    })
      .then((result) => { if (current) setData(result); })
      .catch((cause: unknown) => {
        if (current) setError(cause instanceof Error ? cause.message : "No fue posible cargar el reporte de rotaciones.");
      });
    return () => { current = false; };
  }, [programId, organizationId, placementState, attempt]);

  return (
    <section className="rotation-report" aria-labelledby="rotation-report-title">
      <div className="section-heading">
        <div>
          <h2 id="rotation-report-title">Rotaciones y transferencias</h2>
          <p className="muted">Segmentos, transferencias, interrupciones y horas aceptadas (CR-05). Usa los filtros de programa, organización (incluye la de cada segmento) y estado de práctica de arriba.</p>
        </div>
      </div>
      {error && <Alert kind="error">{error} <button className="btn link" type="button" onClick={() => setAttempt((value) => value + 1)}>Reintentar</button></Alert>}
      {!data && !error && <div className="empty"><Spinner /> Calculando rotaciones…</div>}
      {data && <>
        <div className="rotation-metrics">
          <BentoCard variant="metric" title="Prácticas con varios segmentos"><strong className="metric-value">{data.multi_segment_placements}</strong></BentoCard>
          <BentoCard variant="metric" title="Rotaciones activas"><strong className="metric-value">{data.active_rotations}</strong></BentoCard>
          <BentoCard variant="metric" title="Revisiones combinadas pendientes"><strong className="metric-value">{data.pending_consolidations}</strong></BentoCard>
          <BentoCard variant="metric" title="Transferencias"><strong className="metric-value">{data.transfers}</strong></BentoCard>
          <BentoCard variant="metric" title="Interrupciones"><strong className="metric-value">{data.interruptions}</strong></BentoCard>
          <BentoCard variant="metric" title="Horas aceptadas"><strong className="metric-value">{hoursFormat.format(data.hours.accepted)}</strong></BentoCard>
        </div>
        <div className="rotation-tables">
          <BentoCard variant="content" title="Horas y evaluaciones" description="Solo las horas aceptadas cuentan para el total; las de segmentos no reconocidos se excluyen.">
            <div className="rotation-table-wrap"><table className="report-table"><thead><tr><th scope="col">Indicador</th><th scope="col">Valor</th></tr></thead><tbody>
              <tr><td>Horas reportadas</td><td>{hoursFormat.format(data.hours.reported)}</td></tr>
              <tr><td>Horas aceptadas</td><td>{hoursFormat.format(data.hours.accepted)}</td></tr>
              <tr><td>Horas de segmentos no reconocidos</td><td>{hoursFormat.format(data.hours.not_recognized)}</td></tr>
              <tr><td>Registros pendientes de revisión</td><td>{data.hours.pending_entries}</td></tr>
              <tr><td>Registros en disputa</td><td>{data.hours.disputed_entries}</td></tr>
              <tr><td>Segmentos activos sin evaluación final</td><td>{data.active_segments_without_final_evaluation}</td></tr>
              <tr><td>Segmentos completados sin evaluación final</td><td>{data.completed_segments_missing_final_evaluation}</td></tr>
            </tbody></table></div>
          </BentoCard>
          <BentoCard variant="content" title="Segmentos por estado">
            {!data.segments_by_status.length ? <EmptyState message="No hay segmentos en el ámbito consultado." /> : <div className="rotation-table-wrap"><table className="report-table"><thead><tr><th scope="col">Estado</th><th scope="col">Cantidad</th></tr></thead><tbody>
              {data.segments_by_status.map((row) => <tr key={row.status}><td><Badge>{SEGMENT_STATUS_LABELS[row.status] ?? row.status}</Badge></td><td>{row.count}</td></tr>)}
            </tbody></table></div>}
            <div className="report-subsection"><h3>Trabajo previo en transferencias</h3>{!data.transfers_by_treatment.length ? <p className="muted">Sin transferencias.</p> : data.transfers_by_treatment.map((row) => <div className="dossier-requirement" key={row.treatment}><span>{RECOGNITION_LABELS[row.treatment] ?? row.treatment}</span><strong>{row.count}</strong></div>)}</div>
            <div className="report-subsection"><h3>Reconocimiento en interrupciones</h3>{!data.interruptions_by_recognition.length ? <p className="muted">Sin interrupciones.</p> : data.interruptions_by_recognition.map((row) => <div className="dossier-requirement" key={row.recognition}><span>{RECOGNITION_LABELS[row.recognition] ?? row.recognition}</span><strong>{row.count}</strong></div>)}</div>
          </BentoCard>
          <BentoCard variant="content" className="report-wide" title="Rotaciones por programa">
            {!data.by_program.length ? <EmptyState message="No hay datos agregados." /> : <div className="rotation-table-wrap"><table className="report-table"><thead><tr><th scope="col">Programa</th><th scope="col">Varios segmentos</th><th scope="col">Transferencias</th><th scope="col">Interrupciones</th><th scope="col">Revisiones pendientes</th></tr></thead><tbody>
              {data.by_program.map((row) => <tr key={row.program_code}><td>{row.program_name} ({row.program_code})</td><td>{row.multi_segment_placements}</td><td>{row.transfers}</td><td>{row.interruptions}</td><td>{row.pending_consolidations}</td></tr>)}
            </tbody></table></div>}
          </BentoCard>
        </div>
      </>}
    </section>
  );
}
