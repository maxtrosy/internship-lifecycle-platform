import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import * as api from "../api";
import { Drawer, useConfirm } from "../components/overlays";
import type { EmployerApplication, Opportunity, OpportunityCatalogs, User, WorkplaceSupervisor } from "../api";
import { Alert, Badge, EmptyState, Icon, PageHeader, Skeleton, Spinner } from "../components/ui";
import { Field, useFieldErrors } from "../components/Field";
import EligibilitySummary from "../components/EligibilitySummary";
import { presentEligibility } from "../eligibility";
import { useAsyncAction } from "../useAsyncAction";

const STATE_LABELS: Record<string, string> = {
  DRAFT: "Borrador",
  IN_REVIEW: "En revisión",
  APPROVED: "Aprobada",
  PUBLISHED: "Publicada",
  CLOSED: "Cerrada",
};
const STATE_ORDER = ["DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED", "CLOSED"];

type CreateKey = "title" | "org" | "program";
type SelectKey = "start" | "end" | "location" | "responsibilities";
const EMPTY_SELECTION = { supervisor: "", start: "", end: "", location: "", responsibilities: "" };

export default function Opportunities({ user }: { user: User }) {
  const confirm = useConfirm();
  const isCreator = user.roles.some((r) => r.role === "HOST_ORG_MEMBER" || r.role === "PROGRAM_COORDINATOR");
  const isEmployer = user.roles.some((r) => r.role === "HOST_ORG_MEMBER");
  const isStudent = user.roles.some((r) => r.role === "STUDENT");
  const { busy, error, notice, run, setError, setNotice, clear } = useAsyncAction();
  const [items, setItems] = useState<Opportunity[] | null>(null);
  const [catalogs, setCatalogs] = useState<OpportunityCatalogs | null>(null);
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("ALL");

  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [hostOrg, setHostOrg] = useState("");
  const [program, setProgram] = useState("");
  const createErrors = useFieldErrors<CreateKey>((key) => ({ title: "opp-title", org: "opp-org", program: "opp-prog" })[key]);

  const [apps, setApps] = useState<EmployerApplication[] | null>(null);
  const [supervisors, setSupervisors] = useState<WorkplaceSupervisor[] | null>(null);
  const [selectedOid, setSelectedOid] = useState<number | null>(null);
  const [selecting, setSelecting] = useState<EmployerApplication | null>(null);
  const [sel, setSel] = useState(EMPTY_SELECTION);
  const selectErrors = useFieldErrors<SelectKey>((key) => `select-${selecting?.id ?? 0}-${key}`);
  const applicationsRef = useRef<HTMLHeadingElement>(null);

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
    void reload();
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
    clear();
    window.setTimeout(() => applicationsRef.current?.focus(), 0);
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

  async function create(event: FormEvent) {
    event.preventDefault();
    if (busy === "create") return;
    const valid = createErrors.report({
      ...(!title.trim() ? { title: "Escribe el título de la oportunidad." } : {}),
      ...(!hostOrg ? { org: "Selecciona la organización anfitriona." } : {}),
      ...(!program ? { program: "Selecciona el programa académico." } : {}),
    });
    if (!valid) return;
    const saved = await run("create", async () => {
      await api.createOpportunity({ host_org_id: Number(hostOrg), program_id: Number(program), title });
      await reload();
    }, "Borrador guardado. La oportunidad no estará disponible para postulaciones hasta completar la revisión y publicación configuradas.");
    if (saved) {
      setTitle("");
      setCreateOpen(false);
    }
  }

  async function transitionOpportunity(opportunity: Opportunity, action: "submit" | "approve" | "publish" | "close") {
    if (action === "close" && !(await confirm({ title: "¿Cerrar esta oportunidad?", message: "Dejará de recibir postulaciones. El cambio de estado queda en el historial.", confirmLabel: "Cerrar oportunidad", tone: "danger" }))) return;
    const operations = {
      submit: api.submitOpportunityForReview,
      approve: api.approveOpportunity,
      publish: api.publishOpportunity,
      close: api.closeOpportunity,
    };
    const messages = {
      submit: "Oportunidad enviada a revisión.",
      approve: "Oportunidad aprobada para publicación.",
      publish: "Oportunidad publicada.",
      close: "Oportunidad cerrada.",
    };
    await run(`transition-${opportunity.id}`, async () => {
      await operations[action](opportunity.id);
      await reload();
    }, messages[action], "No se pudo actualizar el estado de la oportunidad.");
  }

  async function apply(id: number) {
    let label = "";
    const ok = await run(`apply-${id}`, async () => {
      const res = await api.apply(id);
      label = presentEligibility(res.eligibility).label.toLocaleLowerCase("es");
    });
    if (ok) setNotice(`Postulación registrada. Resultado de elegibilidad: ${label}.`);
  }

  function openSelection(application: EmployerApplication) {
    setSel(EMPTY_SELECTION);
    selectErrors.reset();
    setSelecting(application);
  }

  async function doSelect(event: FormEvent) {
    event.preventDefault();
    if (!selecting) return;
    const valid = selectErrors.report({
      ...(!sel.start ? { start: "Indica la fecha de inicio." } : {}),
      ...(!sel.end ? { end: "Indica la fecha de finalización." } : {}),
      ...(!sel.location.trim() ? { location: "Indica la ubicación de la práctica." } : {}),
      ...(!sel.responsibilities.trim() ? { responsibilities: "Describe las responsabilidades." } : {}),
    });
    if (!valid) return;
    if (sel.supervisor && (!Number.isInteger(Number(sel.supervisor)) || Number(sel.supervisor) < 1)) {
      setError("Selecciona un supervisor laboral válido.");
      return;
    }
    if (!(await confirm({ title: "¿Confirmar la selección?", message: "La selección pasará a aprobación académica con las condiciones indicadas.", confirmLabel: "Confirmar selección" }))) return;
    const target = selecting;
    const ok = await run(`select-${target.id}`, () => api.selectApplication(target.id, {
      workplace_supervisor_id: sel.supervisor ? Number(sel.supervisor) : null,
      start_date: sel.start,
      end_date: sel.end,
      location: sel.location,
      responsibilities: sel.responsibilities,
    }), "Candidato seleccionado; la práctica quedó pendiente de aprobación académica.");
    if (ok) {
      setSelecting(null);
      if (selectedOid) {
        try {
          setApps(await api.listApplicationsForOpportunity(selectedOid));
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    }
  }

  const selectedOpportunity = items?.find((item) => item.id === selectedOid);
  const counts = useMemo(() => {
    const result: Record<string, number> = { ALL: items?.length ?? 0 };
    for (const item of items ?? []) result[item.state] = (result[item.state] ?? 0) + 1;
    return result;
  }, [items]);
  const filteredItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("es");
    return (items ?? []).filter((opportunity) => {
      const matchesText = !query || [opportunity.title, opportunity.program_code, opportunity.host_name]
        .some((value) => value.toLocaleLowerCase("es").includes(query));
      return matchesText && (stateFilter === "ALL" || opportunity.state === stateFilter);
    });
  }, [items, search, stateFilter]);
  const visibleStates = STATE_ORDER.filter((state) => counts[state]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Catálogo"
        title="Oportunidades"
        description={isEmployer
          ? "Crea borradores, envíalos a revisión y consulta las postulaciones de oportunidades publicadas."
          : isStudent ? "Explora las oportunidades publicadas y postúlate." : "Oportunidades visibles para tu cuenta y su estado de publicación."}
        actions={isCreator ? (
          <button className="btn" type="button" onClick={() => { createErrors.reset(); setCreateOpen(true); }}>
            <Icon name="briefcase" /> Nueva oportunidad
          </button>
        ) : undefined}
      />

      {notice && <Alert kind="success">{notice}</Alert>}
      {error && !createOpen && !selecting && <Alert kind="error">{error}</Alert>}

      <section className="data-panel" aria-labelledby="opportunities-title">
        <div className="data-panel-header">
          <div>
            <h2 id="opportunities-title">Oportunidades</h2>
            {items && <p className="data-panel-meta" aria-live="polite">{filteredItems.length} de {items.length} visibles</p>}
          </div>
          <div className="toolbar">
            <div className="field search-field">
              <label htmlFor="opportunity-search">Buscar oportunidad</label>
              <span className="input-with-icon">
                <Icon name="search" className="input-icon" />
                <input id="opportunity-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Título, programa u organización…" />
              </span>
            </div>
            <div className="field state-filter">
              <label htmlFor="opportunity-state">Estado</label>
              <select id="opportunity-state" value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}>
                <option value="ALL">Todos ({counts.ALL})</option>
                {STATE_ORDER.map((state) => <option key={state} value={state}>{STATE_LABELS[state]} ({counts[state] ?? 0})</option>)}
              </select>
            </div>
          </div>
        </div>
        {visibleStates.length > 1 && (
          <p className="state-summary">
            {visibleStates.map((state) => <span key={state}><strong>{counts[state]}</strong> {STATE_LABELS[state].toLocaleLowerCase("es")}</span>)}
          </p>
        )}

        {items === null && !error && <Skeleton lines={4} />}
        {items !== null && items.length === 0 && (
          <EmptyState icon="briefcase" message={isCreator ? "Todavía no hay oportunidades. Crea un borrador para iniciar su revisión." : "No hay oportunidades publicadas por ahora."} />
        )}
        {items !== null && items.length > 0 && filteredItems.length === 0 && (
          <EmptyState icon="search" message="Ninguna oportunidad coincide con la búsqueda o el estado elegido."
            action={<button className="btn secondary small" type="button" onClick={() => { setSearch(""); setStateFilter("ALL"); }}>Limpiar filtros</button>} />
        )}
        {filteredItems.length > 0 && (
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Lista de oportunidades">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Oportunidad</th>
                  <th scope="col">Programa</th>
                  <th scope="col">Estado</th>
                  <th scope="col" className="col-actions"><span className="sr-only">Acciones</span></th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((o) => {
                  const pending = busy === `transition-${o.id}`;
                  const authorityNote = o.state === "IN_REVIEW" && !o.review_authority_configured
                    ? "La autoridad institucional de revisión no está configurada."
                    : o.state === "APPROVED" && !o.publisher_authority_configured
                      ? "La autoridad institucional de publicación no está configurada." : null;
                  return (
                    <tr key={o.id} className={o.id === selectedOid ? "is-selected" : undefined}>
                      <td>
                        <span className="cell-primary">{o.title}</span>
                        <span className="cell-secondary">{o.host_name}</span>
                        {authorityNote && <span className="cell-note">{authorityNote}</span>}
                      </td>
                      <td className="nowrap">{o.program_code}</td>
                      <td><Badge state={o.state} label={STATE_LABELS[o.state] ?? o.state}>{o.state}</Badge></td>
                      <td className="col-actions">
                        <div className="row-actions">
                          {isStudent && (
                            <button className="btn small" type="button" onClick={() => void apply(o.id)} disabled={o.state !== "PUBLISHED" || busy === `apply-${o.id}`}>
                              {busy === `apply-${o.id}` ? <Spinner /> : "Postular"}
                            </button>
                          )}
                          {isEmployer && (
                            <button className="btn secondary small" type="button" aria-pressed={o.id === selectedOid} onClick={() => void loadApps(o.id)}>
                              Postulaciones
                            </button>
                          )}
                          {o.can_submit_for_review && <button className="btn secondary small" type="button" disabled={pending} onClick={() => void transitionOpportunity(o, "submit")}>{pending ? <Spinner /> : "Enviar a revisión"}</button>}
                          {o.can_approve_for_publication && <button className="btn small" type="button" disabled={pending} onClick={() => void transitionOpportunity(o, "approve")}>{pending ? <Spinner /> : "Aprobar para publicación"}</button>}
                          {o.can_publish && <button className="btn small" type="button" disabled={pending} onClick={() => void transitionOpportunity(o, "publish")}>{pending ? <Spinner /> : "Publicar oportunidad"}</button>}
                          {o.can_close && <button className="btn danger small" type="button" disabled={pending} onClick={() => void transitionOpportunity(o, "close")}>{pending ? <Spinner /> : "Cerrar oportunidad"}</button>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {isEmployer && selectedOid !== null && (
        <section className="data-panel" aria-labelledby="received-applications-title">
          <div className="data-panel-header">
            <div>
              <h2 id="received-applications-title" ref={applicationsRef} tabIndex={-1}>Postulaciones recibidas — {selectedOpportunity?.title ?? "oportunidad seleccionada"}</h2>
              <p className="data-panel-meta">Selecciona a una persona para fijar supervisión, fechas y lugar antes de la aprobación académica.</p>
            </div>
            <button className="btn ghost small" type="button" onClick={() => { setSelectedOid(null); setApps(null); }}>Cerrar lista</button>
          </div>
          {apps === null && !error && <Skeleton lines={3} />}
          {apps !== null && apps.length === 0 && <EmptyState icon="users" message="No hay postulaciones." />}
          {apps !== null && apps.length > 0 && (
            <div className="table-scroll" tabIndex={0} role="region" aria-label="Postulaciones recibidas para la oportunidad seleccionada">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Estudiante</th>
                    <th scope="col">Estado</th>
                    <th scope="col">Elegibilidad</th>
                    <th scope="col" className="col-actions"><span className="sr-only">Acciones</span></th>
                  </tr>
                </thead>
                <tbody>
                  {apps.map((a) => (
                    <tr key={a.id}>
                      <td><span className="cell-primary">{a.display_name}</span><span className="cell-secondary">{a.program_code}</span></td>
                      <td>
                        <Badge>{a.state}</Badge>
                        {a.placement_id && <span className="cell-secondary">Práctica: {a.placement_state ? <Badge>{a.placement_state}</Badge> : "registrada"}</span>}
                      </td>
                      <td><EligibilitySummary value={a.eligibility_result} showCriteria={false} /></td>
                      <td className="col-actions">
                        {a.state === "SUBMITTED" && (
                          <button className="btn small" type="button" onClick={() => openSelection(a)}>Seleccionar</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <Drawer open={createOpen} title="Nueva oportunidad" onClose={() => setCreateOpen(false)}
        description="Se guarda como borrador. Debe pasar por revisión y publicación según las autoridades institucionales configuradas."
        footer={<>
          <button className="btn secondary" type="button" onClick={() => setCreateOpen(false)}>Cancelar</button>
          <button className="btn" type="submit" form="opportunity-create-form" disabled={busy === "create" || !catalogs}>
            {busy === "create" ? <Spinner /> : "Guardar borrador"}
          </button>
        </>}>
        {error && <Alert kind="error">{error}</Alert>}
        <form id="opportunity-create-form" onSubmit={(event) => void create(event)} noValidate>
          <Field id="opp-title" label="Título" error={createErrors.errors.title}>
            <input value={title} maxLength={200} onChange={(e) => { setTitle(e.target.value); createErrors.clear("title"); }} required />
          </Field>
          <Field id="opp-org" label="Organización anfitriona" error={createErrors.errors.org}
            hint={catalogs && organizationChoices.length === 0 ? "No hay organizaciones disponibles para tu cuenta. Contacta a coordinación." : undefined}>
            <select value={hostOrg} onChange={(e) => { setHostOrg(e.target.value); createErrors.clear("org"); }} required disabled={!catalogs}>
              <option value="">{catalogs ? "Selecciona una organización" : "Cargando organizaciones…"}</option>
              {organizationChoices.map((choice) => <option key={choice.id} value={choice.id}>{choice.name}</option>)}
            </select>
          </Field>
          <Field id="opp-prog" label="Programa" error={createErrors.errors.program}
            hint={catalogs && programChoices.length === 0 ? "No hay programas disponibles para tu cuenta. Contacta a coordinación." : undefined}>
            <select value={program} onChange={(e) => { setProgram(e.target.value); createErrors.clear("program"); }} required disabled={!catalogs}>
              <option value="">{catalogs ? "Selecciona un programa" : "Cargando programas…"}</option>
              {programChoices.map((choice) => <option key={choice.id} value={choice.id}>{choice.name} · {choice.code}</option>)}
            </select>
          </Field>
        </form>
      </Drawer>

      <Drawer open={selecting !== null} title={selecting ? `Seleccionar a ${selecting.display_name}` : "Seleccionar candidato"}
        onClose={() => setSelecting(null)}
        description={`${selectedOpportunity?.title ?? "Oportunidad"}. La selección queda pendiente de aprobación académica.`}
        footer={<>
          <button className="btn secondary" type="button" onClick={() => setSelecting(null)}>Cancelar</button>
          <button className="btn" type="submit" form="selection-form" disabled={busy !== null}>
            {busy?.startsWith("select-") ? <Spinner /> : "Confirmar selección"}
          </button>
        </>}>
        {error && <Alert kind="error">{error}</Alert>}
        {selecting && (
          <form id="selection-form" className="form-grid-2" onSubmit={(event) => void doSelect(event)} noValidate>
            <Field id={`select-${selecting.id}-supervisor`} label="Supervisor laboral asignado (opcional)" className="field--full"
              hint={supervisors?.length === 0 ? "No hay supervisores activos registrados para esta organización." : "Déjalo vacío si aún no tienes una asignación de supervisor."}>
              <select value={sel.supervisor} onChange={(e) => setSel({ ...sel, supervisor: e.target.value })} disabled={supervisors === null}>
                <option value="">Sin asignar</option>
                {(supervisors ?? []).map((supervisor) => <option key={supervisor.id} value={supervisor.id}>{supervisor.display_name}</option>)}
              </select>
            </Field>
            <Field id={`select-${selecting.id}-start`} label="Fecha de inicio" error={selectErrors.errors.start}>
              <input type="date" value={sel.start} onChange={(e) => { setSel({ ...sel, start: e.target.value }); selectErrors.clear("start"); }} required />
            </Field>
            <Field id={`select-${selecting.id}-end`} label="Fecha de finalización" error={selectErrors.errors.end}>
              <input type="date" value={sel.end} onChange={(e) => { setSel({ ...sel, end: e.target.value }); selectErrors.clear("end"); }} required />
            </Field>
            <Field id={`select-${selecting.id}-location`} label="Ubicación" className="field--full" error={selectErrors.errors.location}>
              <input value={sel.location} onChange={(e) => { setSel({ ...sel, location: e.target.value }); selectErrors.clear("location"); }} required />
            </Field>
            <Field id={`select-${selecting.id}-responsibilities`} label="Responsabilidades" className="field--full" error={selectErrors.errors.responsibilities}>
              <textarea rows={4} value={sel.responsibilities} onChange={(e) => { setSel({ ...sel, responsibilities: e.target.value }); selectErrors.clear("responsibilities"); }} required />
            </Field>
          </form>
        )}
      </Drawer>
    </div>
  );
}
