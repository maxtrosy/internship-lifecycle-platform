import { useEffect, useState } from "react";
import * as api from "../api";
import type { OperationalReport } from "../api";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";

type DistributionCardRow = {
  key: string;
  label: string;
  opportunities: number;
  applications: number;
  placements: number;
};

function DistributionCards({ rows, label }: { rows: DistributionCardRow[]; label: string }) {
  return <ul className="report-distribution-cards" aria-label={label}>
    {rows.map((row) => <li key={row.key}>
      <h3>{row.label}</h3>
      <dl>
        <div><dt>Oportunidades</dt><dd>{row.opportunities}</dd></div>
        <div><dt>Postulaciones</dt><dd>{row.applications}</dd></div>
        <div><dt>Prácticas</dt><dd>{row.placements}</dd></div>
      </dl>
    </li>)}
  </ul>;
}

function localDate(value: string): string {
  const parts = value.slice(0, 10).split("-").map(Number);
  if (parts.length !== 3 || parts.some((part) => !Number.isFinite(part))) return "Fecha no disponible";
  return new Date(parts[0], parts[1] - 1, parts[2]).toLocaleDateString("es-CO");
}

export default function OperationalReports() {
  const [data, setData] = useState<OperationalReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    program_id: "", organization_id: "", placement_state: "", opportunity_state: "", application_state: "",
  });
  const [options, setOptions] = useState<OperationalReport | null>(null);

  useEffect(() => {
    let current = true;
    setError(null);
    setLoading(true);
    const query = {
      ...(filters.program_id ? { program_id: Number(filters.program_id) } : {}),
      ...(filters.organization_id ? { organization_id: Number(filters.organization_id) } : {}),
      ...(filters.placement_state ? { placement_state: filters.placement_state } : {}),
      ...(filters.opportunity_state ? { opportunity_state: filters.opportunity_state } : {}),
      ...(filters.application_state ? { application_state: filters.application_state } : {}),
    };
    api.getOperationalReports(query)
      .then((result) => {
        if (current) {
          setData(result);
          setOptions((previous) => previous ?? result);
        }
      })
      .catch((cause: unknown) => {
        if (current) setError(cause instanceof Error ? cause.message : "No fue posible cargar los reportes.");
      })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [attempt, filters]);

  function setFilter(key: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="page-stack reports-page">
      <PageHeader eyebrow="OPERACIÓN INSTITUCIONAL" title="Reportes operativos" description="Conteos calculados desde oportunidades, postulaciones, prácticas, requisitos e incidentes persistidos. El alcance depende de tu programa o rol institucional." />
      {error && <Alert kind="error">{error} <button className="btn link" type="button" onClick={() => setAttempt((value) => value + 1)}>Reintentar</button></Alert>}
      <section className="card report-filters" aria-label="Filtros de reportes">
        <div className="section-heading"><div><span className="eyebrow">CONSULTA</span><h2>Filtrar datos</h2></div>{loading && <span className="muted"><Spinner /> Actualizando…</span>}</div>
        <div className="grid cols-3">
          <div className="field"><label htmlFor="report-program">Programa</label><select id="report-program" value={filters.program_id} onChange={(event) => setFilter("program_id", event.target.value)} disabled={!options}><option value="">Todos los programas autorizados</option>{options?.by_program.map((row) => <option key={row.program_code} value={row.program_id}>{row.program_name} ({row.program_code})</option>)}</select></div>
          <div className="field"><label htmlFor="report-organization">Organización</label><select id="report-organization" value={filters.organization_id} onChange={(event) => setFilter("organization_id", event.target.value)} disabled={!options}><option value="">Todas</option>{options?.by_organization.map((row) => <option key={row.organization_id} value={row.organization_id}>{row.organization}</option>)}</select></div>
          <div className="field"><label htmlFor="report-placement-state">Estado de práctica</label><select id="report-placement-state" value={filters.placement_state} onChange={(event) => setFilter("placement_state", event.target.value)} disabled={!options}><option value="">Todos</option>{options?.placements_by_state.map((row) => <option key={row.state} value={row.state}>{formatDomainLabel(row.state)}</option>)}</select></div>
          <div className="field"><label htmlFor="report-opportunity-state">Estado de oportunidad</label><select id="report-opportunity-state" value={filters.opportunity_state} onChange={(event) => setFilter("opportunity_state", event.target.value)} disabled={!options}><option value="">Todos</option>{options?.opportunities_by_state.map((row) => <option key={row.state} value={row.state}>{formatDomainLabel(row.state)}</option>)}</select></div>
          <div className="field"><label htmlFor="report-application-state">Estado de postulación</label><select id="report-application-state" value={filters.application_state} onChange={(event) => setFilter("application_state", event.target.value)} disabled={!options}><option value="">Todos</option>{options?.applications_by_state.map((row) => <option key={row.state} value={row.state}>{formatDomainLabel(row.state)}</option>)}</select></div>
          <div className="field filter-reset"><span className="field-note">Los resultados permanecen dentro del ámbito autorizado.</span><button className="btn secondary" type="button" onClick={() => setFilters({ program_id: "", organization_id: "", placement_state: "", opportunity_state: "", application_state: "" })}>Limpiar filtros</button></div>
        </div>
      </section>
      {!data && !error && <div className="empty"><Spinner /> Calculando reportes…</div>}
      {data && <>
        <div className="report-metrics">
          <BentoCard variant="metric" title="Prácticas activas"><strong className="metric-value">{data.active_placements}</strong></BentoCard>
          <BentoCard variant="metric" title="Documentos obligatorios pendientes"><strong className="metric-value">{data.mandatory_documents_pending}</strong></BentoCard>
          <BentoCard variant="metric" title="Incidentes reportados"><strong className="metric-value">{data.reported_incidents}</strong></BentoCard>
        </div>
        <div className="report-tables">
          <BentoCard variant="content" title="Prácticas por estado">
            {!data.placements_by_state.length ? <EmptyState message="No hay prácticas en el ámbito consultado." /> : <div className="report-table-wrap"><table className="report-table"><thead><tr><th>Estado</th><th>Cantidad</th></tr></thead><tbody>{data.placements_by_state.map((row) => <tr key={row.state}><td><Badge>{formatDomainLabel(row.state)}</Badge></td><td>{row.count}</td></tr>)}</tbody></table></div>}
          </BentoCard>
          <BentoCard variant="content" title="Oportunidades y postulaciones">
            <div className="report-subsection"><h3>Oportunidades</h3>{!data.opportunities_by_state.length ? <p className="muted">Sin oportunidades.</p> : data.opportunities_by_state.map((row) => <div className="dossier-requirement" key={row.state}><span>{formatDomainLabel(row.state)}</span><strong>{row.count}</strong></div>)}</div>
            <div className="report-subsection"><h3>Postulaciones</h3>{!data.applications_by_state.length ? <p className="muted">Sin postulaciones.</p> : data.applications_by_state.map((row) => <div className="dossier-requirement" key={row.state}><span>{formatDomainLabel(row.state)}</span><strong>{row.count}</strong></div>)}</div>
          </BentoCard>
          <BentoCard variant="content" title="Distribución por programa">
            {!data.by_program.length ? <EmptyState message="No hay datos agregados." /> : <>
              <div className="report-table-wrap report-distribution-table"><table className="report-table"><thead><tr><th>Programa</th><th>Oportunidades</th><th>Postulaciones</th><th>Prácticas</th></tr></thead><tbody>{data.by_program.map((row) => <tr key={row.program_code}><td>{row.program_name} ({row.program_code})</td><td>{row.opportunities}</td><td>{row.applications}</td><td>{row.placements}</td></tr>)}</tbody></table></div>
              <DistributionCards label="Distribución por programa" rows={data.by_program.map((row) => ({ key: row.program_code, label: `${row.program_name} (${row.program_code})`, opportunities: row.opportunities, applications: row.applications, placements: row.placements }))} />
            </>}
          </BentoCard>
          <BentoCard variant="content" title="Distribución por organización">
            {!data.by_organization.length ? <EmptyState message="No hay datos agregados." /> : <>
              <div className="report-table-wrap report-distribution-table"><table className="report-table"><thead><tr><th>Organización</th><th>Oportunidades</th><th>Postulaciones</th><th>Prácticas</th></tr></thead><tbody>{data.by_organization.map((row) => <tr key={row.organization}><td>{row.organization}</td><td>{row.opportunities}</td><td>{row.applications}</td><td>{row.placements}</td></tr>)}</tbody></table></div>
              <DistributionCards label="Distribución por organización" rows={data.by_organization.map((row) => ({ key: String(row.organization_id), label: row.organization, opportunities: row.opportunities, applications: row.applications, placements: row.placements }))} />
            </>}
          </BentoCard>
          <BentoCard variant="content" className="report-wide" title="Fechas previstas de finalización" description="Fechas de fin persistidas en la versión vigente de prácticas activas; sin umbral de proximidad inventado.">
            {!data.expected_end_dates.length ? <EmptyState message="No hay prácticas activas con una fecha futura de finalización registrada." /> : <div className="report-table-wrap"><table className="report-table"><thead><tr><th>Fecha prevista</th><th>Prácticas</th></tr></thead><tbody>{data.expected_end_dates.map((row) => <tr key={row.end_date}><td>{localDate(row.end_date)}</td><td>{row.placements}</td></tr>)}</tbody></table></div>}
          </BentoCard>
        </div>
      </>}
    </div>
  );
}
