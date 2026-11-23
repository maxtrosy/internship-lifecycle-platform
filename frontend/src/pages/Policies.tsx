import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "../api";
import type { PolicyCondition, PolicyKind, ProgramPolicies } from "../api";
import { Alert, EmptyState, PageHeader, Skeleton, Spinner, formatDomainLabel } from "../components/ui";
import { Field } from "../components/Field";
import { TabPanel, Tabs } from "../components/overlays";

type Draft = {
  reason: string;
  programs: string;
  minLevel: string;
  minCredits: string;
  prerequisites: string;
  manualReview: boolean;
  documents: string;
  supervisors: boolean;
  finalReport: boolean;
  finalEvaluation: boolean;
  minHours: string;
};

const emptyDraft: Draft = {
  reason: "", programs: "", minLevel: "", minCredits: "", prerequisites: "", manualReview: false, documents: "",
  supervisors: false, finalReport: false, finalEvaluation: false, minHours: "",
};

function splitList(value: string): string[] {
  return [...new Set(value.split(",").map((part) => part.trim()).filter(Boolean))];
}

function draftFrom(program: ProgramPolicies | undefined): Draft {
  if (!program) return emptyDraft;
  const conditions = Object.fromEntries(
    Object.entries(program.policies).map(([kind, policy]) => [kind, policy?.conditions ?? []]),
  ) as Record<PolicyKind, PolicyCondition[]>;
  const eligibility = conditions.ELIGIBILITY ?? [];
  const activation = conditions.ACTIVATION ?? [];
  const completion = conditions.COMPLETION ?? [];
  const value = (list: PolicyCondition[], type: string) => list.find((item) => item.type === type)?.value;
  return {
    reason: "",
    programs: Array.isArray(value(eligibility, "PROGRAM_IN")) ? (value(eligibility, "PROGRAM_IN") as string[]).join(", ") : "",
    minLevel: value(eligibility, "ACADEMIC_LEVEL_MIN")?.toString() ?? "",
    minCredits: value(eligibility, "CREDITS_MIN")?.toString() ?? "",
    prerequisites: Array.isArray(value(eligibility, "PREREQUISITE_COMPLETED"))
      ? (value(eligibility, "PREREQUISITE_COMPLETED") as string[]).join(", ") : "",
    manualReview: value(eligibility, "MANUAL_REVIEW") === true,
    documents: Array.isArray(value(activation, "REQUIRE_DOCUMENTS"))
      ? (value(activation, "REQUIRE_DOCUMENTS") as string[]).join(", ") : "",
    supervisors: value(activation, "SUPERVISORS_ASSIGNED") === true,
    finalReport: value(completion, "FINAL_REPORT") === true,
    finalEvaluation: value(completion, "FINAL_EVALUATION") === true,
    minHours: value(completion, "MIN_HOURS")?.toString() ?? "",
  };
}

function conditionsFrom(draft: Draft, kind: PolicyKind): PolicyCondition[] {
  if (kind === "ELIGIBILITY") {
    const conditions: PolicyCondition[] = [];
    const programs = splitList(draft.programs);
    const prerequisites = splitList(draft.prerequisites);
    if (programs.length) conditions.push({ type: "PROGRAM_IN", value: programs });
    if (draft.minLevel.trim()) conditions.push({ type: "ACADEMIC_LEVEL_MIN", value: Number(draft.minLevel) });
    if (draft.minCredits.trim()) conditions.push({ type: "CREDITS_MIN", value: Number(draft.minCredits) });
    if (prerequisites.length) conditions.push({ type: "PREREQUISITE_COMPLETED", value: prerequisites });
    if (draft.manualReview) conditions.push({ type: "MANUAL_REVIEW", value: true });
    return conditions;
  }
  if (kind === "ACTIVATION") {
    const conditions: PolicyCondition[] = [];
    const documents = splitList(draft.documents);
    if (documents.length) conditions.push({ type: "REQUIRE_DOCUMENTS", value: documents });
    if (draft.supervisors) conditions.push({ type: "SUPERVISORS_ASSIGNED", value: true });
    return conditions;
  }
  const conditions: PolicyCondition[] = [];
  if (draft.finalReport) conditions.push({ type: "FINAL_REPORT", value: true });
  if (draft.finalEvaluation) conditions.push({ type: "FINAL_EVALUATION", value: true });
  if (draft.minHours.trim()) conditions.push({ type: "MIN_HOURS", value: Number(draft.minHours) });
  return conditions;
}

export default function Policies() {
  const [programs, setPrograms] = useState<ProgramPolicies[] | null>(null);
  const [selectedCode, setSelectedCode] = useState("");
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [busy, setBusy] = useState<PolicyKind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [tab, setTab] = useState<PolicyKind>("ELIGIBILITY");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const reloadRequest = useRef(0);

  async function reload(preserveDraft = false) {
    const request = ++reloadRequest.current;
    setError(null);
    try {
      const result = await api.listPolicies();
      if (request !== reloadRequest.current) return;
      const nextCode = result.some((program) => program.code === selectedCode)
        ? selectedCode
        : result[0]?.code ?? "";
      const nextProgram = result.find((program) => program.code === nextCode);
      setPrograms(result);
      setSelectedCode(nextCode);
      // A save refreshes version metadata while the operator may still be
      // editing a different policy. Do not discard that in-progress draft.
      if (!preserveDraft) setDraft(draftFrom(nextProgram));
    } catch (err) {
      if (request === reloadRequest.current) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }
  }

  useEffect(() => {
    void reload();
    return () => { reloadRequest.current += 1; };
  }, []);

  const selected = useMemo(() => programs?.find((program) => program.code === selectedCode), [programs, selectedCode]);

  async function save(kind: PolicyKind) {
    const reason = draft.reason.trim();
    if (!reason || reason.length > 500) {
      setReasonError("Explica el motivo de esta versión (máximo 500 caracteres).");
      window.setTimeout(() => document.getElementById("policy-reason")?.focus(), 0);
      return;
    }
    setReasonError(null);
    const conditions = conditionsFrom(draft, kind);
    if (conditions.length === 0) {
      setError("Agrega al menos una condición para crear una versión de política.");
      return;
    }
    if (conditions.some((condition) => typeof condition.value === "number" && !Number.isInteger(condition.value))) {
      setError("Los niveles, créditos y horas deben ser números enteros.");
      return;
    }
    setBusy(kind);
    setError(null);
    setMessage(null);
    try {
      await api.createPolicyVersion(selectedCode, kind, conditions, reason);
      setMessage(`Nueva versión de política de ${formatDomainLabel(kind)} creada para ${selectedCode}.`);
      setDraft((current) => ({ ...current, reason: "" }));
      await reload(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((current) => ({ ...current, [key]: value }));
  const versionOf = (kind: PolicyKind) => selected?.policies[kind]?.version_no;
  const KIND_COPY: Record<PolicyKind, { title: string; description: string; submit: string }> = {
    ELIGIBILITY: { title: "Elegibilidad", description: "Una postulación debe cumplir todas las condiciones de la versión vigente.", submit: "Crear versión de elegibilidad" },
    ACTIVATION: { title: "Activación", description: "El sistema fija estas condiciones cuando se aprueba académicamente la selección.", submit: "Crear versión de activación" },
    COMPLETION: { title: "Finalización y cierre", description: "Las horas se verifican sumando los registros de origen antes de completar la práctica.", submit: "Crear versión de cierre" },
  };
  const copy = KIND_COPY[tab];

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Configuración" title="Políticas del programa" description="Configura condiciones versionadas. Las nuevas reglas aplican a colocaciones aprobadas desde ese momento." />
      {error && <Alert kind="error">{error}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}
      {programs === null && !error && <Skeleton lines={4} />}
      {programs !== null && programs.length === 0 && <EmptyState icon="settings" message="No tienes programas asignados para administrar políticas." />}
      {programs && programs.length > 0 && (
        <>
          <section className="data-panel policy-program" aria-labelledby="policy-program-title">
            <div className="data-panel-header">
              <div>
                <h2 id="policy-program-title">Programa</h2>
                {selected && <p className="data-panel-meta">
                  Versiones vigentes: elegibilidad {versionOf("ELIGIBILITY") ? `v${versionOf("ELIGIBILITY")}` : "sin configurar"},
                  activación {versionOf("ACTIVATION") ? `v${versionOf("ACTIVATION")}` : "sin configurar"},
                  cierre {versionOf("COMPLETION") ? `v${versionOf("COMPLETION")}` : "sin configurar"}.
                </p>}
              </div>
              <div className="field field--narrow">
                <label htmlFor="program">Programa</label>
                <select id="program" value={selectedCode} onChange={(event) => {
                  const code = event.target.value;
                  setSelectedCode(code);
                  setDraft(draftFrom(programs?.find((program) => program.code === code)));
                }}>
                  {programs.map((program) => <option key={program.code} value={program.code}>{program.name} · {program.code}</option>)}
                </select>
              </div>
            </div>
          </section>

          <section className="data-panel policy-card" aria-labelledby="policy-kind-title">
            <Tabs label="Tipo de política" idBase="policy" value={tab} onChange={setTab}
              items={(["ELIGIBILITY", "ACTIVATION", "COMPLETION"] as PolicyKind[]).map((kind) => ({ id: kind, label: KIND_COPY[kind].title }))} />
            <TabPanel idBase="policy" id={tab}>
              <div className="policy-panel">
                <div className="policy-panel-heading">
                  <h2 id="policy-kind-title">{copy.title}</h2>
                  <p className="muted">{copy.description}</p>
                  {selected?.policies[tab] ? <PolicyProvenance version={selected.policies[tab]!} /> : <p className="muted policy-provenance">Sin versión vigente para este programa.</p>}
                </div>

                <fieldset className="policy-fieldset">
                  <legend>Condiciones de la nueva versión</legend>
                  {tab === "ELIGIBILITY" && (
                    <>
                      <div className="form-grid-2">
                        <Field id="eligibility-programs" label="Programas permitidos" hint="Códigos separados por coma, por ejemplo ING-SIS, ADM.">
                          <input value={draft.programs} onChange={(event) => set("programs", event.target.value)} />
                        </Field>
                        <Field id="eligibility-prerequisites" label="Prerrequisitos aprobados" hint="Códigos de asignatura separados por coma.">
                          <input value={draft.prerequisites} onChange={(event) => set("prerequisites", event.target.value)} />
                        </Field>
                        <Field id="eligibility-min-level" label="Nivel académico mínimo">
                          <input type="number" min="0" step="1" inputMode="numeric" value={draft.minLevel} onChange={(event) => set("minLevel", event.target.value)} />
                        </Field>
                        <Field id="eligibility-min-credits" label="Créditos mínimos">
                          <input type="number" min="0" step="1" inputMode="numeric" value={draft.minCredits} onChange={(event) => set("minCredits", event.target.value)} />
                        </Field>
                      </div>
                      <label className="check-row">
                        <input type="checkbox" checked={draft.manualReview} onChange={(event) => set("manualReview", event.target.checked)} />
                        Requiere decisión manual de coordinación antes de mostrar la postulación a la organización
                      </label>
                    </>
                  )}
                  {tab === "ACTIVATION" && (
                    <>
                      <Field id="policy-activation-documents" label="Documentos obligatorios" hint="Tipos separados por coma, por ejemplo DOC_INSURANCE, DOC_AGREEMENT.">
                        <input value={draft.documents} onChange={(event) => set("documents", event.target.value)} />
                      </Field>
                      <label className="check-row">
                        <input type="checkbox" checked={draft.supervisors} onChange={(event) => set("supervisors", event.target.checked)} />
                        Exigir supervisor del lugar asignado
                      </label>
                    </>
                  )}
                  {tab === "COMPLETION" && (
                    <>
                      <label className="check-row">
                        <input type="checkbox" checked={draft.finalReport} onChange={(event) => set("finalReport", event.target.checked)} />
                        Informe final obligatorio
                      </label>
                      <label className="check-row">
                        <input type="checkbox" checked={draft.finalEvaluation} onChange={(event) => set("finalEvaluation", event.target.checked)} />
                        Evaluación final obligatoria
                      </label>
                      <Field id="policy-completion-min-hours" label="Horas mínimas" hint="Déjalo vacío si no hay condición de horas." className="field--narrow">
                        <input type="number" min="1" step="1" inputMode="numeric" value={draft.minHours} onChange={(event) => set("minHours", event.target.value)} />
                      </Field>
                    </>
                  )}
                </fieldset>

                <Field id="policy-reason" label={<>Motivo de la nueva versión <span aria-hidden="true">*</span></>} error={reasonError}
                  hint="Obligatorio, hasta 500 caracteres. Se guarda en la auditoría con la persona autora; indica si es una configuración de demostración. No incluyas datos personales.">
                  <textarea value={draft.reason} maxLength={500} rows={3} required
                    onChange={(event) => { set("reason", event.target.value); setReasonError(null); }} />
                </Field>

                <div className="policy-actions">
                  <button className="btn" type="button" disabled={busy !== null} onClick={() => void save(tab)}>
                    {busy === tab ? <Spinner /> : copy.submit}
                  </button>
                  <p className="field-hint">Cada versión nueva queda registrada y no cambia las condiciones de colocaciones ya aprobadas.</p>
                </div>
              </div>
            </TabPanel>
          </section>
        </>
      )}
    </div>
  );
}

function PolicyProvenance({ version }: { version: NonNullable<ProgramPolicies["policies"][PolicyKind]> }) {
  return (
    <p className="muted policy-provenance">
      Versión vigente v{version.version_no} · {version.created_by_name ? `creada por ${version.created_by_name}` : "autor histórico no disponible"}
      {version.created_reason ? ` · Motivo: ${version.created_reason}` : " · Motivo no registrado en versiones históricas"}
    </p>
  );
}
