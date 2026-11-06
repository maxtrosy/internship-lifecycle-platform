import { useEffect, useState } from "react";
import * as api from "../api";
import type { ChecklistItem, DocumentSubmission } from "../api";
import { Alert, Badge, BentoCard, EmptyState, PageHeader, Spinner, formatDomainLabel } from "../components/ui";

type Row = { id: number; display_name: string; program_code: string; opportunity_title: string; state: string };

export default function DocumentReview() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [items, setItems] = useState<Record<number, ChecklistItem[]>>({});
  const [submissions, setSubmissions] = useState<Record<number, Record<number, DocumentSubmission[]>>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function reload() {
    setError(null);
    try {
      setRows(await api.listDocumentsPending());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => { void reload(); }, []);

  async function openItems(pid: number) {
    setOpen(pid);
    setError(null);
    try {
      const list = await api.listChecklist(pid);
      const pairs = await Promise.all(list.map(async (item) => [
        item.id,
        await api.listDocumentSubmissions(pid, item.id),
      ] as const));
      setItems((current) => ({ ...current, [pid]: list }));
      setSubmissions((current) => ({ ...current, [pid]: Object.fromEntries(pairs) }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function decide(pid: number, itemId: number, decision: "APPROVED" | "REJECTED") {
    const reason = (reasons[itemId] ?? "").trim();
    if (reason.length < 3) {
      setError("Escribe un motivo de al menos 3 caracteres para registrar la decisión.");
      return;
    }
    if (!window.confirm(decision === "REJECTED" ? "¿Rechazar o revocar la aprobación de este documento?" : "¿Aprobar este documento?")) return;
    setBusy(itemId);
    setError(null);
    setMessage(null);
    try {
      await api.reviewDocument(pid, itemId, decision, reason);
      setReasons((current) => ({ ...current, [itemId]: "" }));
      setMessage(decision === "APPROVED" ? "Documento aprobado." : "Documento rechazado con motivo registrado.");
      await reload();
      await openItems(pid);
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

  return (
    <div className="page-stack">
      <PageHeader eyebrow="REVISIÓN" title="Revisión documental" description="Revisa cada archivo, registra el motivo de la decisión y consulta el historial de versiones." />
      {error && <Alert kind="error">{error}</Alert>}
      {message && <Alert kind="success">{message}</Alert>}
      {rows === null && !error && <div className="empty"><Spinner /> Cargando…</div>}
      {rows !== null && rows.length === 0 && <EmptyState message="No hay documentos pendientes de revisión." />}
      {rows?.map((row) => (
        <BentoCard variant="task" className="document-review-card" key={row.id}>
          <div className="row">
            <div className="spacer">
              <h3>{row.display_name} · {row.program_code}</h3>
              <p className="muted">{row.opportunity_title} · práctica</p>
            </div>
            <Badge>{row.state}</Badge>
            <button className="btn secondary" onClick={() => open === row.id ? setOpen(null) : void openItems(row.id)}>
              {open === row.id ? "Ocultar" : "Ver documentos"}
            </button>
          </div>
          {open === row.id && items[row.id] && (
            <div className="table-scroll" tabIndex={0} aria-label={`Documentos de ${row.display_name}`}><table>
              <thead><tr><th>Requisito</th><th>Estado</th><th>Archivo actual</th><th>Decisión</th><th>Acción</th></tr></thead>
              <tbody>
                {items[row.id].filter((item) => item.kind.startsWith("DOC_") && (item.status === "SUBMITTED" ||
                  (row.state === "ACTIVE" && item.status === "APPROVED"))).map((item) => {
                  const history = submissions[row.id]?.[item.id] ?? [];
                  const latest = history[0];
                  return (
                    <tr key={item.id}>
                      <td>{formatDomainLabel(item.kind)}</td>
                      <td><Badge>{item.status}</Badge></td>
                      <td>
                        {latest ? <>
                          <span>{latest.original_filename} · v{latest.revision}</span>
                          <div><button className="btn link" onClick={() => void download(row.id, item.id, latest)}>Descargar</button></div>
                        </> : <span className="muted">Sin archivo adjunto</span>}
                      </td>
                      <td>{latest?.decision ? <><Badge>{latest.decision}</Badge><div>{latest.reason}</div></> : "Pendiente"}</td>
                      <td>
                        {item.status === "SUBMITTED" && latest && (
                          <div className="field" style={{ minWidth: 220 }}>
                            <textarea rows={2} maxLength={1000} placeholder="Motivo obligatorio de la decisión"
                              aria-label={`Motivo para ${formatDomainLabel(item.kind)}`} value={reasons[item.id] ?? ""}
                              onChange={(event) => setReasons((current) => ({ ...current, [item.id]: event.target.value }))} />
                            <div className="row">
                              <button className="btn" disabled={busy === item.id} onClick={() => void decide(row.id, item.id, "APPROVED")}>
                                {busy === item.id ? <Spinner /> : "Aprobar"}
                              </button>
                              <button className="btn danger" disabled={busy === item.id} onClick={() => void decide(row.id, item.id, "REJECTED")}>Rechazar</button>
                            </div>
                          </div>
                        )}
                        {row.state === "ACTIVE" && item.status === "APPROVED" && (
                          <div className="field" style={{ minWidth: 220 }}>
                            <textarea rows={2} maxLength={1000} placeholder="Motivo obligatorio de revocación"
                              aria-label={`Motivo de revocación para ${formatDomainLabel(item.kind)}`} value={reasons[item.id] ?? ""}
                              onChange={(event) => setReasons((current) => ({ ...current, [item.id]: event.target.value }))} />
                            <button className="btn danger" disabled={busy === item.id} onClick={() => void decide(row.id, item.id, "REJECTED")}>
                              Revocar aprobación
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
      ))}
    </div>
  );
}
