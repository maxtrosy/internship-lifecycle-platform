import { useEffect, useMemo, useState } from "react";
import * as api from "../api";
import { useConfirm } from "../components/overlays";
import type { ChecklistItem, DocumentSubmission } from "../api";
import { Alert, Badge, EmptyState, Icon, PageHeader, Skeleton, Spinner, formatDomainLabel } from "../components/ui";
import { errorMessage, useAsyncAction } from "../useAsyncAction";

type Row = { id: number; display_name: string; program_code: string; opportunity_title: string; state: string };

function reviewable(row: Row, item: ChecklistItem) {
  return item.kind.startsWith("DOC_") && (item.status === "SUBMITTED" || (row.state === "ACTIVE" && item.status === "APPROVED"));
}

export default function DocumentReview() {
  const confirm = useConfirm();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [items, setItems] = useState<Record<number, ChecklistItem[]>>({});
  const [submissions, setSubmissions] = useState<Record<number, Record<number, DocumentSubmission[]>>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [reasonErrors, setReasonErrors] = useState<Record<number, string>>({});
  const [open, setOpen] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const { busy, error, notice, run, setError } = useAsyncAction();

  async function reload() {
    try {
      setRows(await api.listDocumentsPending());
    } catch (err) {
      setError(errorMessage(err, "No fue posible cargar la cola de revisión."));
    }
  }

  useEffect(() => { void reload(); }, []);

  async function openItems(pid: number) {
    setOpen(pid);
    try {
      const list = await api.listChecklist(pid);
      const pairs = await Promise.all(list.map(async (item) => [
        item.id,
        await api.listDocumentSubmissions(pid, item.id),
      ] as const));
      setItems((current) => ({ ...current, [pid]: list }));
      setSubmissions((current) => ({ ...current, [pid]: Object.fromEntries(pairs) }));
    } catch (err) {
      setError(errorMessage(err, "No fue posible cargar los documentos."));
    }
  }

  async function decide(pid: number, itemId: number, decision: "APPROVED" | "REJECTED") {
    const reason = (reasons[itemId] ?? "").trim();
    if (reason.length < 3) {
      setReasonErrors((current) => ({ ...current, [itemId]: "Escribe un motivo de al menos 3 caracteres para registrar la decisión." }));
      document.getElementById(`reason-${itemId}`)?.focus();
      return;
    }
    setReasonErrors((current) => ({ ...current, [itemId]: "" }));
    if (!(await confirm(decision === "REJECTED"
      ? { title: "¿Rechazar este documento?", message: "Si estaba aprobado, la aprobación se revoca. El motivo queda visible para la persona titular.", confirmLabel: "Rechazar documento", tone: "danger" }
      : { title: "¿Aprobar este documento?", message: "La decisión y el motivo quedan registrados en el historial del documento.", confirmLabel: "Aprobar documento" }))) return;
    const ok = await run(`decide-${itemId}`, async () => {
      await api.reviewDocument(pid, itemId, decision, reason);
      await reload();
      await openItems(pid);
    }, decision === "APPROVED" ? "Documento aprobado." : "Documento rechazado con motivo registrado.");
    if (ok) setReasons((current) => ({ ...current, [itemId]: "" }));
  }

  async function download(pid: number, itemId: number, submission: DocumentSubmission) {
    await run(`download-${submission.id}`, () => api.downloadDocument(pid, itemId, submission));
  }

  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("es");
    if (!rows || !needle) return rows ?? [];
    return rows.filter((row) => `${row.display_name} ${row.program_code} ${row.opportunity_title}`.toLocaleLowerCase("es").includes(needle));
  }, [rows, query]);

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Revisión" title="Revisión documental" description="Revisa cada archivo, registra el motivo de la decisión y consulta el historial de versiones." />
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      {rows === null && !error && <Skeleton lines={4} />}
      {rows !== null && rows.length === 0 && <EmptyState icon="review" message="No hay documentos pendientes de revisión." />}
      {rows !== null && rows.length > 0 && (
        <section className="data-panel" aria-labelledby="review-queue-title">
          <div className="data-panel-header">
            <div>
              <h2 id="review-queue-title">Prácticas con documentos por revisar <span className="count-pill">{rows.length}</span></h2>
              <p className="data-panel-meta">Abre una práctica para ver sus archivos. Cada decisión exige un motivo, que queda en el historial.</p>
            </div>
            <div className="toolbar">
              <div className="field search-field">
                <label htmlFor="review-search">Buscar</label>
                <span className="input-with-icon">
                  <Icon name="search" className="input-icon" />
                  <input id="review-search" type="search" value={query} placeholder="Estudiante, programa u oportunidad…"
                    onChange={(event) => setQuery(event.target.value)} />
                </span>
              </div>
            </div>
          </div>
          {visible.length === 0 && <p className="muted">Ninguna práctica coincide con la búsqueda.</p>}
          <ul className="review-list">
            {visible.map((row) => {
              const expanded = open === row.id;
              const panelId = `review-items-${row.id}`;
              const list = (items[row.id] ?? []).filter((item) => reviewable(row, item));
              return (
                <li key={row.id} className={`document-review-card${expanded ? " is-open" : ""}`}>
                  <div className="review-item-head">
                    <div className="review-item-title">
                      <h3>{row.display_name}</h3>
                      <p className="muted">{row.opportunity_title} · {row.program_code}</p>
                    </div>
                    <Badge>{row.state}</Badge>
                    <button className="btn secondary small" type="button" aria-expanded={expanded} aria-controls={panelId}
                      onClick={() => expanded ? setOpen(null) : void openItems(row.id)}>
                      <Icon name={expanded ? "chevron-down" : "chevron-right"} />
                      {expanded ? "Ocultar" : "Ver documentos"}
                    </button>
                  </div>
                  {expanded && (
                    <div id={panelId} className="review-item-body">
                      {!items[row.id] && <Skeleton lines={2} />}
                      {items[row.id] && list.length === 0 && <p className="muted">No hay documentos que requieran decisión en esta práctica.</p>}
                      {list.length > 0 && (
                        <div className="table-scroll" tabIndex={0} aria-label={`Documentos de ${row.display_name}`}>
                          <table className="data-table data-table--stack review-table">
                            <thead><tr><th scope="col">Requisito</th><th scope="col">Estado</th><th scope="col">Archivo actual</th><th scope="col">Última decisión</th><th scope="col">Decisión</th></tr></thead>
                            <tbody>
                              {list.map((item) => {
                                const latest = (submissions[row.id]?.[item.id] ?? [])[0];
                                const label = formatDomainLabel(item.kind);
                                const revoking = row.state === "ACTIVE" && item.status === "APPROVED";
                                const reasonError = reasonErrors[item.id] || null;
                                const deciding = busy === `decide-${item.id}`;
                                return (
                                  <tr key={item.id}>
                                    <td data-label="Requisito"><span className="cell-primary">{label}</span></td>
                                    <td data-label="Estado"><Badge>{item.status}</Badge></td>
                                    <td data-label="Archivo actual">
                                      {latest ? <>
                                        <span className="cell-primary file-name">{latest.original_filename}</span>
                                        <span className="cell-secondary">Versión {latest.revision}</span>
                                        <button className="btn link" type="button" disabled={busy === `download-${latest.id}`}
                                          onClick={() => void download(row.id, item.id, latest)}>Descargar</button>
                                      </> : <span className="muted">Sin archivo adjunto</span>}
                                    </td>
                                    <td data-label="Última decisión">{latest?.decision
                                      ? <><Badge>{latest.decision}</Badge>{latest.reason && <span className="cell-secondary review-reason">{latest.reason}</span>}</>
                                      : <span className="muted">Pendiente</span>}</td>
                                    <td className="cell-wide" data-label="Decisión">
                                      {(item.status === "SUBMITTED" && latest) || revoking ? (
                                        <div className={`field field--decision${reasonError ? " field--invalid" : ""}`}>
                                          <textarea id={`reason-${item.id}`} rows={2} maxLength={1000}
                                            placeholder={revoking ? "Motivo obligatorio de revocación…" : "Motivo obligatorio de la decisión…"}
                                            aria-label={revoking ? `Motivo de revocación para ${label}` : `Motivo para ${label}`}
                                            aria-invalid={reasonError ? true : undefined}
                                            aria-describedby={reasonError ? `reason-${item.id}-error` : undefined}
                                            value={reasons[item.id] ?? ""}
                                            onChange={(event) => {
                                              const next = event.target.value;
                                              setReasons((current) => ({ ...current, [item.id]: next }));
                                              setReasonErrors((current) => ({ ...current, [item.id]: "" }));
                                            }} />
                                          {reasonError && <p className="field-error" id={`reason-${item.id}-error`}>{reasonError}</p>}
                                          <div className="action-row decision-actions">
                                            {revoking ? (
                                              <button className="btn danger small" type="button" disabled={deciding} onClick={() => void decide(row.id, item.id, "REJECTED")}>
                                                {deciding ? <Spinner /> : "Revocar aprobación"}
                                              </button>
                                            ) : <>
                                              <button className="btn small" type="button" disabled={deciding} onClick={() => void decide(row.id, item.id, "APPROVED")}>
                                                {deciding ? <Spinner /> : "Aprobar"}
                                              </button>
                                              <button className="btn danger small" type="button" disabled={deciding} onClick={() => void decide(row.id, item.id, "REJECTED")}>Rechazar</button>
                                            </>}
                                          </div>
                                        </div>
                                      ) : <span className="muted">—</span>}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
