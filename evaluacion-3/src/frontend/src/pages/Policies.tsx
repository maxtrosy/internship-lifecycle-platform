import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "../api";
import type { PolicyCondition, PolicyKind, ProgramPolicies } from "../api";
import { Alert, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";

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
      setError("Explica el motivo de esta versión (máximo 500 caracteres).");
      return;
    }
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

  return (
    <div className="page-stack">
      <PageHeader eyebrow="CONFIGURACIÓN" title="Políticas del programa" description="Configura condiciones versionadas. Las nuevas reglas aplican a colocaciones aprobadas desde ese momento." />
      {error && <Alert kind="error">{error}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}
      {programs === null && !error && <div className="empty"><Spinner /> Cargando…</div>}
      {programs !== null && programs.length === 0 && <EmptyState message="No tienes programas asignados para administrar políticas." />}
      {programs && programs.length > 0 && (
        <>
          <BentoCard variant="content" className="policy-program" title="Programa y versiones">
            <div className="field" style={{ maxWidth: 460 }}>
              <label htmlFor="program">Programa</label>
              <select id="program" value={selectedCode} onChange={(event) => {
                const code = event.target.value;
                setSelectedCode(code);
                setDraft(draftFrom(programs?.find((program) => program.code === code)));
              }}>
                {programs.map((program) => <option key={program.code} value={program.code}>{program.name} · {program.code}</option>)}
              </select>
            </div>
            {selected && <p className="muted" style={{ marginTop: 12 }}>
              Versiones vigentes: elegibilidad {selected.policies.ELIGIBILITY?.version_no ? `v${selected.policies.ELIGIBILITY.version_no}` : "sin configurar"},
              activación {selected.policies.ACTIVATION?.version_no ? `v${selected.policies.ACTIVATION.version_no}` : "sin configurar"},
              cierre {selected.policies.COMPLETION?.version_no ? `v${selected.policies.COMPLETION.version_no}` : "sin configurar"}.
            </p>}
          </BentoCard>

          <BentoCard variant="content" className="policy-card">
            <h2>Elegibilidad</h2>
            <p className="muted">Una postulación debe cumplir todas las condiciones de la versión vigente.</p>
            {selected?.policies.ELIGIBILITY && <PolicyProvenance version={selected.policies.ELIGIBILITY} />}
            <div className="grid cols-2">
              <div className="field"><label htmlFor="eligibility-programs">Programas permitidos (códigos separados por coma)</label>
                <input id="eligibility-programs" value={draft.programs} onChange={(event) => set("programs", event.target.value)} placeholder="ING-SIS, ADM" /></div>
              <div className="field"><label htmlFor="eligibility-min-level">Nivel académico mínimo</label>
                <input id="eligibility-min-level" type="number" min="0" step="1" value={draft.minLevel} onChange={(event) => set("minLevel", event.target.value)} /></div>
              <div className="field"><label htmlFor="eligibility-min-credits">Créditos mínimos</label>
                <input id="eligibility-min-credits" type="number" min="0" step="1" value={draft.minCredits} onChange={(event) => set("minCredits", event.target.value)} /></div>
              <div className="field"><label htmlFor="eligibility-prerequisites">Prerrequisitos aprobados</label>
                <input id="eligibility-prerequisites" value={draft.prerequisites} onChange={(event) => set("prerequisites", event.target.value)} placeholder="MAT101, CS102" /></div>
            </div>
            <label className="row" style={{ marginTop: 12 }}>
              <input type="checkbox" checked={draft.manualReview} onChange={(event) => set("manualReview", event.target.checked)} style={{ width: "auto" }} />
              Requiere decisión manual de coordinación antes de mostrar la postulación a la organización
            </label>
            <button className="btn" style={{ marginTop: 12 }} disabled={busy !== null} onClick={() => void save("ELIGIBILITY")}>
              {busy === "ELIGIBILITY" ? <Spinner /> : "Crear versión de elegibilidad"}
            </button>
          </BentoCard>

          <BentoCard variant="content" className="policy-card">
            <h2>Activación</h2>
            <p className="muted">El sistema fija estas condiciones cuando se aprueba académicamente la selección.</p>
            {selected?.policies.ACTIVATION && <PolicyProvenance version={selected.policies.ACTIVATION} />}
            <div className="field"><label>Documentos obligatorios (tipos separados por coma)</label>
              <input value={draft.documents} onChange={(event) => set("documents", event.target.value)} placeholder="DOC_INSURANCE, DOC_AGREEMENT" /></div>
            <label className="row" style={{ marginTop: 12 }}>
              <input type="checkbox" checked={draft.supervisors} onChange={(event) => set("supervisors", event.target.checked)} style={{ width: "auto" }} />
              Exigir supervisor del lugar asignado
            </label>
            <button className="btn" style={{ marginTop: 12 }} disabled={busy !== null} onClick={() => void save("ACTIVATION")}>
              {busy === "ACTIVATION" ? <Spinner /> : "Crear versión de activación"}
            </button>
          </BentoCard>

          <BentoCard variant="content" className="policy-card">
            <h2>Finalización y cierre</h2>
            <p className="muted">Las horas se verifican sumando los registros de origen antes de completar la práctica.</p>
            {selected?.policies.COMPLETION && <PolicyProvenance version={selected.policies.COMPLETION} />}
            <div className="grid cols-2">
              <label className="row"><input type="checkbox" checked={draft.finalReport}
                onChange={(event) => set("finalReport", event.target.checked)} style={{ width: "auto" }} />Informe final obligatorio</label>
              <label className="row"><input type="checkbox" checked={draft.finalEvaluation}
                onChange={(event) => set("finalEvaluation", event.target.checked)} style={{ width: "auto" }} />Evaluación final obligatoria</label>
              <div className="field"><label>Horas mínimas (vacío = sin condición de horas)</label>
                <input type="number" min="1" step="1" value={draft.minHours} onChange={(event) => set("minHours", event.target.value)} /></div>
            </div>
            <button className="btn" style={{ marginTop: 12 }} disabled={busy !== null} onClick={() => void save("COMPLETION")}>
              {busy === "COMPLETION" ? <Spinner /> : "Crear versión de cierre"}
            </button>
          </BentoCard>
          <BentoCard variant="content" className="policy-card">
            <h2>Motivo de la nueva versión</h2>
            <p className="muted">El motivo se guarda en la auditoría junto con la persona autora. Indica si es una configuración de demostración; no la convierte en regla institucional aprobada.</p>
            <div className="field">
              <label htmlFor="policy-reason">Motivo <span aria-hidden="true">*</span></label>
              <textarea id="policy-reason" value={draft.reason} maxLength={500}
                onChange={(event) => set("reason", event.target.value)} required rows={3}
                aria-describedby="policy-reason-help" />
              <span id="policy-reason-help" className="muted">Obligatorio, hasta 500 caracteres. No incluyas datos personales.</span>
            </div>
          </BentoCard>
          <Alert kind="info">Cada versión nueva queda registrada y no cambia las condiciones de colocaciones ya aprobadas.</Alert>
        </>
      )}
    </div>
  );
}

function PolicyProvenance({ version }: { version: NonNullable<ProgramPolicies["policies"][PolicyKind]> }) {
  return (
    <p className="muted policy-provenance">
      Versión v{version.version_no} · {version.created_by_name ? `creada por ${version.created_by_name}` : "autor histórico no disponible"}
      {version.created_reason ? ` · Motivo: ${version.created_reason}` : " · Motivo no registrado en versiones históricas"}
    </p>
  );
}
