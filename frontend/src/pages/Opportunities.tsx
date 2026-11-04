import { useEffect, useMemo, useState } from "react";
import * as api from "../api";
import type { EmployerApplication, Opportunity, OpportunityCatalogs, User, WorkplaceSupervisor } from "../api";
import { Alert, Badge, EmptyState, PageHeader, Spinner } from "../components/ui";
import EligibilitySummary from "../components/EligibilitySummary";
import { presentEligibility } from "../eligibility";

function opportunityStateLabel(state: string): string {
  return ({
    DRAFT: "Borrador",
    IN_REVIEW: "En revisión",
    APPROVED: "Aprobada",
    PUBLISHED: "Publicada",
    CLOSED: "Cerrada",
  } as Record<string, string>)[state] ?? state;
}

export default function Opportunities({ user }: { user: User }) {
  const isCreator = user.roles.some((r) => r.role === "HOST_ORG_MEMBER" || r.role === "PROGRAM_COORDINATOR");
  const isEmployer = user.roles.some((r) => r.role === "HOST_ORG_MEMBER");
  const isStudent = user.roles.some((r) => r.role === "STUDENT");
  const [items, setItems] = useState<Opportunity[] | null>(null);
  const [catalogs, setCatalogs] = useState<OpportunityCatalogs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("ALL");

  const [title, setTitle] = useState("");
  const [hostOrg, setHostOrg] = useState("");
  const [program, setProgram] = useState("");
  const [creating, setCreating] = useState(false);
  const [transitioningId, setTransitioningId] = useState<number | null>(null);

  const [apps, setApps] = useState<EmployerApplication[] | null>(null);
  const [supervisors, setSupervisors] = useState<WorkplaceSupervisor[] | null>(null);
  const [selectedOid, setSelectedOid] = useState<number | null>(null);
  const [selectingId, setSelectingId] = useState<number | null>(null);
  const [sel, setSel] = useState({ supervisor: "", start: "", end: "", location: "", responsibilities: "" });

  const organizationChoices = catalogs?.organizations ?? [];
  const programChoices = catalogs?.programs ?? [];

  useEffect(() => {
    if (!catalogs) return;
    setHostOrg((current) => catalogs.organizations.some((choice) => String(choice.id) === current)
      ? current : catalogs.organizations.length === 1 ? String(catalogs.organizations[0].id) : "");
    setProgram((current) => catalogs.programs.some((choice) => String(choice.id) === current)
      ? current : catalogs.programs.length === 1 ? String(catalogs.programs[0].id) : "");
  }, [catalogs]);

  async function reload() {
    setError(null);
    try {
      setItems(await api.listOpportunities());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    if (isCreator) {
      try {
        setCatalogs(await api.listOpportunityCatalogs());
      } catch (err) {
        setCatalogs(null);
        setError(err instanceof Error ? err.message : "No se pudieron cargar organizaciones y programas.");
      }
    }
  }

  useEffect(() => {
    reload();
  }, []);

  useEffect(() => {
    if (!items) return;
    const requestedId = Number(sessionStorage.getItem("dh05:open-opportunity"));
    if (!Number.isInteger(requestedId) || requestedId < 1) return;
    const requested = items.find((item) => item.id === requestedId);
    sessionStorage.removeItem("dh05:open-opportunity");
    if (requested) {
      setStateFilter("ALL");
      setSearch(requested.title);
    }
  }, [items]);

  async function loadApps(oid: number) {
    setSelectedOid(oid);
    setApps(null);
    setSupervisors(null);
    setError(null);
    try {
      const [applications, availableSupervisors] = await Promise.all([
        api.listApplicationsForOpportunity(oid),
        api.listWorkplaceSupervisors(oid),
      ]);
      setApps(applications);
      setSupervisors(availableSupervisors);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (creating) return;
    setError(null);
    setSuccess(null);
    setCreating(true);
    try {
      await api.createOpportunity({ host_org_id: Number(hostOrg), program_id: Number(program), title });
      setTitle("");
      setSuccess("Borrador guardado. La oportunidad no estará disponible para postulaciones hasta completar la revisión y publicación configuradas.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  }

  async function transitionOpportunity(opportunity: Opportunity, action: "submit" | "approve" | "publish" | "close") {
    if (action === "close" && !window.confirm("¿Cerrar esta oportunidad? Los cambios de estado quedarán en el historial.")) return;
    setError(null);
    setSuccess(null);
    setTransitioningId(opportunity.id);
    try {
      const operations = {
        submit: api.submitOpportunityForReview,
        approve: api.approveOpportunity,
        publish: api.publishOpportunity,
        close: api.closeOpportunity,
      };
      await operations[action](opportunity.id);
      const messages = {
        submit: "Oportunidad enviada a revisión.",
        approve: "Oportunidad aprobada para publicación.",
        publish: "Oportunidad publicada.",
        close: "Oportunidad cerrada.",
      };
      setSuccess(messages[action]);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar el estado de la oportunidad.");
    } finally {
      setTransitioningId(null);
    }
  }

  async function apply(id: number) {
    setError(null);
    setSuccess(null);
    try {
      const res = await api.apply(id);
      const eligibility = presentEligibility(res.eligibility);
      setSuccess(`Postulación registrada. Resultado de elegibilidad: ${eligibility.label.toLocaleLowerCase("es")}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function doSelect(aid: number) {
    if (!sel.start || !sel.end || !sel.location.trim() || !sel.responsibilities.trim()) {
      setError("Completa las fechas, la ubicación y las responsabilidades antes de confirmar.");
      return;
    }
    if (sel.supervisor && (!Number.isInteger(Number(sel.supervisor)) || Number(sel.supervisor) < 1)) {
      setError("Selecciona un supervisor laboral válido.");
      return;
    }
    if (!window.confirm("¿Confirmar la selección de este candidato?")) return;
    setError(null);
    setSuccess(null);
    try {
      await api.selectApplication(aid, {
        workplace_supervisor_id: sel.supervisor ? Number(sel.supervisor) : null,
        start_date: sel.start,
        end_date: sel.end,
        location: sel.location,
        responsibilities: sel.responsibilities,
      });
      setSuccess("Candidato seleccionado; la práctica quedó pendiente de aprobación académica.");
      setSelectingId(null);
      if (selectedOid) await loadApps(selectedOid);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const selectedOpportunity = items?.find((item) => item.id === selectedOid);
  const filteredItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("es");
    return (items ?? []).filter((opportunity) => {
      const matchesText = !query || [opportunity.title, opportunity.program_code, opportunity.host_name]
        .some((value) => value.toLocaleLowerCase("es").includes(query));
      return matchesText && (stateFilter === "ALL" || opportunity.state === stateFilter);
    });
  }, [items, search, stateFilter]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="CATÁLOGO"
        title="Oportunidades"
        description={isEmployer
          ? "Crea borradores, envíalos a revisión y consulta las postulaciones de oportunidades publicadas."
          : isStudent ? "Explora las oportunidades publicadas y postúlate." : "Oportunidades disponibles."}
      />

      {isCreator && (
        <form className="card form-card" onSubmit={create}>
          <div className="section-heading"><div><span className="eyebrow">GESTIÓN</span><h2>Crear borrador</h2><p>El borrador debe pasar por revisión y publicación según las autoridades institucionales configuradas.</p></div></div>
          <div className="grid cols-3 opportunity-assignment-grid">
            <div className="field">
              <label htmlFor="opp-title">Título</label>
              <input id="opp-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="opp-org">Organización</label>
              <select id="opp-org" value={hostOrg} onChange={(e) => setHostOrg(e.target.value)} required disabled={!catalogs}>
                <option value="">{catalogs ? "Selecciona una organización" : "Cargando organizaciones…"}</option>
                {organizationChoices.map((choice) => <option key={choice.id} value={choice.id}>{choice.name}</option>)}
              </select>
              {catalogs && organizationChoices.length === 0 && <small className="field-note">No hay organizaciones disponibles para tu cuenta. Contacta a coordinación.</small>}
            </div>
            <div className="field">
              <label htmlFor="opp-prog">Programa</label>
              <select id="opp-prog" value={program} onChange={(e) => setProgram(e.target.value)} required disabled={!catalogs}>
                <option value="">{catalogs ? "Selecciona un programa" : "Cargando programas…"}</option>
                {programChoices.map((choice) => <option key={choice.id} value={choice.id}>{choice.name} · {choice.code}</option>)}
              </select>
              {catalogs && programChoices.length === 0 && <small className="field-note">No hay programas disponibles para tu cuenta. Contacta a coordinación.</small>}
            </div>
          </div>
          <div>
            <button className="btn" type="submit" disabled={creating || !catalogs || !organizationChoices.length || !programChoices.length || !title.trim() || !hostOrg || !program}>
              {creating ? <Spinner /> : "Guardar borrador"}
            </button>
          </div>
        </form>
      )}

      {success && <Alert kind="success">{success}</Alert>}
      {error && <Alert kind="error">{error}</Alert>}

      {items === null && !error && (
        <div className="empty"><Spinner /> Cargando…</div>
      )}
      {items !== null && items.length === 0 && (
        <EmptyState message="No hay oportunidades disponibles." />
      )}
      {items !== null && items.length > 0 && (
        <section className="card catalog-card">
          <div className="catalog-toolbar">
            <div className="catalog-heading"><div><span className="eyebrow">EXPLORAR</span><h2>Oportunidades disponibles</h2></div><span className="result-count">{filteredItems.length} de {items.length}</span></div>
            <div className="catalog-filters">
              <div className="field search-field"><label htmlFor="opportunity-search">Buscar oportunidad</label><input id="opportunity-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Título, programa u organización" /></div>
              <div className="field state-filter"><label htmlFor="opportunity-state">Estado</label><select id="opportunity-state" value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}><option value="ALL">Todos</option>{["DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED", "CLOSED"].map((state) => <option key={state} value={state}>{({ DRAFT: "Borrador", IN_REVIEW: "En revisión", APPROVED: "Aprobada", PUBLISHED: "Publicada", CLOSED: "Cerrada" } as Record<string, string>)[state]}</option>)}</select></div>
            </div>
          </div>
          {filteredItems.length === 0 ? <EmptyState message="No hay oportunidades que coincidan con esta búsqueda." /> : <div className="table-scroll" tabIndex={0} aria-label="Lista de oportunidades">
          <table>
            <thead>
              <tr>
                <th>Oportunidad</th>
                <th>Programa</th>
                <th>Organización</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((o) => (
                <tr key={o.id}>
                  <td>{o.title}</td>
                  <td>{o.program_code}</td>
                  <td>{o.host_name}</td>
                  <td><Badge state={o.state} label={opportunityStateLabel(o.state)}>{o.state}</Badge></td>
                  <td>
                    <div className="row">
                      {isStudent && (
                        <button className="btn" onClick={() => apply(o.id)} disabled={o.state !== "PUBLISHED"}>
                          Postular
                        </button>
                      )}
                      {isEmployer && (
                        <button className="btn secondary" onClick={() => loadApps(o.id)}>
                          Postulaciones
                        </button>
                      )}
                      {o.can_submit_for_review && <button className="btn secondary" disabled={transitioningId === o.id} onClick={() => transitionOpportunity(o, "submit")}>{transitioningId === o.id ? <Spinner /> : "Enviar a revisión"}</button>}
                      {o.can_approve_for_publication && <button className="btn" disabled={transitioningId === o.id} onClick={() => transitionOpportunity(o, "approve")}>{transitioningId === o.id ? <Spinner /> : "Aprobar para publicación"}</button>}
                      {o.can_publish && <button className="btn" disabled={transitioningId === o.id} onClick={() => transitionOpportunity(o, "publish")}>{transitioningId === o.id ? <Spinner /> : "Publicar oportunidad"}</button>}
                      {o.can_close && <button className="btn danger" disabled={transitioningId === o.id} onClick={() => transitionOpportunity(o, "close")}>{transitioningId === o.id ? <Spinner /> : "Cerrar oportunidad"}</button>}
                      {o.state === "IN_REVIEW" && !o.review_authority_configured && <span className="field-note">La autoridad institucional de revisión no está configurada.</span>}
                      {o.state === "APPROVED" && !o.publisher_authority_configured && <span className="field-note">La autoridad institucional de publicación no está configurada.</span>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>}
        </section>
      )}

      {isEmployer && selectedOid !== null && (
        <div className="card">
          <h3>Postulaciones recibidas — {selectedOpportunity?.title ?? "oportunidad"}</h3>
          {apps === null && <div className="empty"><Spinner /> Cargando…</div>}
          {apps !== null && apps.length === 0 && <EmptyState message="No hay postulaciones." />}
          {apps !== null && apps.length > 0 && (
            <div className="table-scroll" tabIndex={0} aria-label="Postulaciones recibidas para la oportunidad seleccionada">
              <table>
                <thead>
                  <tr>
                    <th>Estudiante</th>
                    <th>Programa</th>
                    <th>Estado</th>
                    <th>Elegibilidad</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {apps.map((a) => (
                    <tr key={a.id}>
                      <td>{a.display_name}</td>
                      <td>{a.program_code}</td>
                      <td><Badge>{a.state}</Badge></td>
                      <td><EligibilitySummary value={a.eligibility_result} showCriteria={false} /></td>
                      <td>
                        {a.state === "SUBMITTED" && selectingId !== a.id && (
                          <button className="btn" onClick={() => setSelectingId(a.id)}>Seleccionar</button>
                        )}
                        {selectingId === a.id && (
                          <div className="grid cols-2" style={{ marginTop: 8 }}>
                            <div className="field"><label>Supervisor laboral asignado (opcional)</label>
                              <small className="field-note">Déjalo vacío si aún no tienes una asignación de supervisor.</small>
                              <select aria-label="Supervisor laboral asignado (opcional)" value={sel.supervisor}
                                onChange={(e) => setSel({ ...sel, supervisor: e.target.value })} disabled={supervisors === null}>
                                <option value="">Sin asignar</option>
                                {(supervisors ?? []).map((supervisor) => <option key={supervisor.id} value={supervisor.id}>{supervisor.display_name}</option>)}
                              </select>
                              {supervisors?.length === 0 && <small className="field-note">No hay supervisores activos registrados para esta organización.</small>}
                            </div>
                            <div className="field"><label>Fecha de inicio</label>
                              <input type="date" value={sel.start} onChange={(e) => setSel({ ...sel, start: e.target.value })} /></div>
                            <div className="field"><label>Fecha de finalización</label>
                              <input type="date" value={sel.end} onChange={(e) => setSel({ ...sel, end: e.target.value })} /></div>
                            <div className="field"><label>Ubicación</label>
                              <input value={sel.location} onChange={(e) => setSel({ ...sel, location: e.target.value })} /></div>
                            <div className="field" style={{ gridColumn: "1 / -1" }}><label>Responsabilidades</label>
                              <textarea rows={3} value={sel.responsibilities} onChange={(e) => setSel({ ...sel, responsibilities: e.target.value })} /></div>
                            <div className="row">
                              <button className="btn" onClick={() => doSelect(a.id)}>Confirmar</button>
                              <button className="btn secondary" onClick={() => setSelectingId(null)}>Cancelar</button>
                            </div>
                          </div>
                        )}
                        {a.placement_id && (
                          <span className="muted"> · Práctica: <Badge>{a.placement_state}</Badge></span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
