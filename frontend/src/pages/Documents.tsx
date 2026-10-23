import { useEffect, useState } from "react";
import * as api from "../api";
import type { ActivationStatus, Application, DocumentSubmission } from "../api";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";

export default function Documents() {
  const [apps, setApps] = useState<Application[] | null>(null);
  const [statuses, setStatuses] = useState<Record<number, ActivationStatus>>({});
  const [submissions, setSubmissions] = useState<Record<string, DocumentSubmission[]>>({});
  const [files, setFiles] = useState<Record<number, File>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function reload() {
    setError(null);
    try {
      const list = await api.listApplications();
      const placements = list.filter((a) => a.placement_id &&
        (a.placement_state === "DOCUMENTATION_PENDING" || a.placement_state === "ACTIVE"));
      const statusPairs = await Promise.all(placements.map(async (a) => {
        const pid = a.placement_id!;
        return [pid, await api.activationStatus(pid)] as const;
      }));
      const statusMap = Object.fromEntries(statusPairs);
      const submissionPairs = await Promise.all(placements.flatMap((a) => {
        const pid = a.placement_id!;
        return statusMap[pid].items.map(async (item) => [
          `${pid}:${item.id}`,
          await api.listDocumentSubmissions(pid, item.id),
        ] as const);
      }));
      setApps(list);
      setStatuses(statusMap);
      setSubmissions(Object.fromEntries(submissionPairs));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => { void reload(); }, []);

  async function submit(pid: number, itemId: number) {
    const file = files[itemId];
    if (!file) return;
    setBusy(itemId);
    setError(null);
    setMessage(null);
    try {
      const result = await api.submitDocument(pid, itemId, file);
      setFiles((current) => {
        const next = { ...current };
        delete next[itemId];
        return next;
      });
      setMessage(`Documento enviado como versión ${result.revision}.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function download(pid: number, itemId: number, submission: DocumentSubmission) {
    setError(null);
    try {
      await api.downloadDocument(pid, itemId, submission);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const placements = (apps ?? []).filter((a) => a.placement_id &&
    (a.placement_state === "DOCUMENTATION_PENDING" || a.placement_state === "ACTIVE"));

  return (
    <div className="page-stack">
      <PageHeader eyebrow="MI PRÁCTICA" title="Mis documentos" description="Consulta los requisitos, entrega archivos y revisa las decisiones del equipo académico." />
      <Alert kind="info">Carga únicamente archivos sintéticos para esta demostración. Se aceptan PDF, PNG, JPG y DOCX de hasta 10 MB.</Alert>
      {error && <Alert kind="error">{error}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}
      {apps === null && !error && <div className="empty"><Spinner /> Cargando…</div>}
      {apps !== null && placements.length === 0 && (
        <EmptyState message="No tienes prácticas con requisitos documentales pendientes o en seguimiento." />
      )}
      {placements.map((a) => {
        const pid = a.placement_id!;
        const status = statuses[pid];
        return (
          <BentoCard variant="content" className="document-placement" key={a.id}>
            <div className="row">
              <div className="spacer">
                <h3>{a.title} · práctica</h3>
                <p className="muted">{a.placement_state === "ACTIVE" ? "Práctica activa" : "Documentación para activación"}</p>
              </div>
              <Badge>{a.placement_state}</Badge>
            </div>
            {status && a.placement_state === "DOCUMENTATION_PENDING" && (
              <p className="muted">
                {status.ready_to_activate
                  ? "Los requisitos están aprobados; el coordinador puede activar la práctica."
                  : `Pendiente para activar: ${status.unmet.map(formatDomainLabel).join(", ") || "—"}`}
              </p>
            )}
            {status?.activation_noncompliant && (
              <Alert kind="info">La práctica sigue activa. Corrige los requisitos rechazados para completar el ciclo.</Alert>
            )}
            {status && status.items.length > 0 && (
              <div className="table-scroll" tabIndex={0} aria-label={`Requisitos documentales de ${a.title}`}><table>
                <thead><tr><th>Requisito</th><th>Estado</th><th>Entrega actual</th><th>Revisión</th><th>Acción</th></tr></thead>
                <tbody>
                  {status.items.map((item) => {
                    const history = submissions[`${pid}:${item.id}`] ?? [];
                    const latest = history[0];
                    return (
                      <tr key={item.id}>
                        <td>{formatDomainLabel(item.kind)}{item.mandatory ? " · obligatorio" : " · opcional"}</td>
                        <td><Badge>{item.status}</Badge></td>
                        <td>
                          {latest ? (
                            <div>
                              <span>{latest.original_filename} · v{latest.revision}</span>
                              <div><button className="btn link" onClick={() => void download(pid, item.id, latest)}>Descargar</button></div>
                            </div>
                          ) : <span className="muted">Sin archivo</span>}
                        </td>
                        <td>
                          {latest?.decision ? <><Badge>{latest.decision}</Badge><div>{latest.reason}</div></>
                            : <span className="muted">{item.status === "SUBMITTED" ? "En revisión" : "—"}</span>}
                        </td>
                        <td>
                          {item.kind.startsWith("DOC_") && (item.status === "REQUIRED" || item.status === "REJECTED") && (
                            <div className="field">
                              <input
                                aria-label={`Archivo para ${formatDomainLabel(item.kind)}`}
                                type="file"
                                accept=".pdf,.png,.jpg,.jpeg,.docx,application/pdf,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                onChange={(event) => {
                                  const selected = event.currentTarget.files?.[0];
                                  if (selected) setFiles((current) => ({ ...current, [item.id]: selected }));
                                }}
                              />
                              <button className="btn" disabled={!files[item.id] || busy === item.id}
                                onClick={() => void submit(pid, item.id)}>
                                {busy === item.id ? <Spinner /> : item.status === "REJECTED" ? "Reenviar" : "Enviar"}
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table></div>
            )}
          </BentoCard>
        );
      })}
    </div>
  );
}
