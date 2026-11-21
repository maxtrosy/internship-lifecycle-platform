import { useEffect, useState } from "react";
import * as api from "../api";
import type { Application } from "../api";
import EligibilitySummary from "../components/EligibilitySummary";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Spinner } from "../components/ui";
import type { SectionId } from "../components/Layout";

export default function Applications({ onNavigate }: { onNavigate: (section: SectionId) => void }) {
  const [items, setItems] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listApplications()
      .then(setItems)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <div className="page-stack">
      <PageHeader eyebrow="MI PROCESO" title="Mis postulaciones" description="Consulta las decisiones de selección, el estado de tu práctica y el resultado de elegibilidad." />

      {error && <Alert kind="error">{error}</Alert>}
      {items === null && !error && (
        <div className="empty">
          <Spinner /> Cargando…
        </div>
      )}
      {items !== null && items.length === 0 && (
        <EmptyState message="Todavía no tienes postulaciones." action={<button className="btn" type="button" onClick={() => onNavigate("opportunities")}>Explorar oportunidades</button>} />
      )}
      {items !== null && items.length > 0 && (
        <BentoCard variant="content" className="applications-card" title="Historial de postulaciones" description="El resultado de elegibilidad se presenta en un resumen legible; abre sus detalles para consultar los criterios disponibles.">
          <div className="table-scroll" tabIndex={0} aria-label="Historial de postulaciones con columnas consultables">
          <table className="applications-table">
            <thead>
              <tr>
                <th>Oportunidad</th>
                <th>Postulación</th>
                <th>Práctica</th>
                <th>Elegibilidad</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td data-label="Oportunidad">{a.title}</td>
                  <td data-label="Postulación"><Badge>{a.state}</Badge></td>
                  <td data-label="Práctica">
                    {a.placement_id ? (
                      <><span className="muted">Práctica asignada</span><br /><Badge>{a.placement_state}</Badge></>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td data-label="Elegibilidad"><EligibilitySummary value={a.eligibility_result} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </BentoCard>
      )}
    </div>
  );
}
