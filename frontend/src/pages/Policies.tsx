import { useEffect, useMemo, useState } from "react";
import * as api from "../api";
import type { PolicyCondition, PolicyKind, ProgramPolicies } from "../api";
import { Alert, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";

type Draft = {
  programs: string;
  minLevel: string;
  minCredits: string;
  prerequisites: string;
  documents: string;
  supervisors: boolean;
  finalReport: boolean;
  finalEvaluation: boolean;
  minHours: string;
};

const emptyDraft: Draft = {
  programs: "", minLevel: "", minCredits: "", prerequisites: "", documents: "",
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
    programs: Array.isArray(value(eligibility, "PROGRAM_IN")) ? (value(eligibility, "PROGRAM_IN") as string[]).join(", ") : "",
    minLevel: value(eligibility, "ACADEMIC_LEVEL_MIN")?.toString() ?? "",
    minCredits: value(eligibility, "CREDITS_MIN")?.toString() ?? "",
    prerequisites: Array.isArray(value(eligibility, "PREREQUISITE_COMPLETED"))
      ? (value(eligibility, "PREREQUISITE_COMPLETED") as string[]).join(", ") : "",
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

  async function reload() {
    setError(null);
    try {
      const result = await api.listPolicies();
      setPrograms(result);
      setSelectedCode((current) => current || result[0]?.code || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => { void reload(); }, []);

  const selected = useMemo(() => programs?.find((program) => program.code === selectedCode), [programs, selectedCode]);

  useEffect(() => {
    if (selected) setDraft(draftFrom(selected));
  }, [selected]);

  async function save(kind: PolicyKind) {
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
      await api.createPolicyVersion(selectedCode, kind, conditions);
      setMessage(`Nueva versión de política de ${formatDomainLabel(kind)} creada para ${selectedCode}.`);
      await reload();
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
              <select id="program" value={selectedCode} onChange={(event) => setSelectedCode(event.target.value)}>
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
            <div className="grid cols-2">
              <div className="field"><label>Programas permitidos (códigos separados por coma)</label>
                <input value={draft.programs} onChange={(event) => set("programs", event.target.value)} placeholder="ING-SIS, ADM" /></div>
              <div className="field"><label>Nivel académico mínimo</label>
                <input type="number" min="0" step="1" value={draft.minLevel} onChange={(event) => set("minLevel", event.target.value)} /></div>
              <div className="field"><label>Créditos mínimos</label>
                <input type="number" min="0" step="1" value={draft.minCredits} onChange={(event) => set("minCredits", event.target.value)} /></div>
              <div className="field"><label>Prerrequisitos aprobados</label>
                <input value={draft.prerequisites} onChange={(event) => set("prerequisites", event.target.value)} placeholder="MAT101, CS102" /></div>
            </div>
            <button className="btn" style={{ marginTop: 12 }} disabled={busy !== null} onClick={() => void save("ELIGIBILITY")}>
              {busy === "ELIGIBILITY" ? <Spinner /> : "Crear versión de elegibilidad"}
            </button>
          </BentoCard>

          <BentoCard variant="content" className="policy-card">
            <h2>Activación</h2>
            <p className="muted">El sistema fija estas condiciones cuando se aprueba académicamente la selección.</p>
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
          <Alert kind="info">Cada versión nueva queda registrada y no cambia las condiciones de colocaciones ya aprobadas.</Alert>
        </>
      )}
    </div>
  );
}
