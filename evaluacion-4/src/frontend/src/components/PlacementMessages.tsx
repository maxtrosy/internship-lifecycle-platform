import { useEffect, useState, type FormEvent } from "react";
import * as api from "../api";
import type { PlacementDossier, PlacementMessage } from "../api";
import { Alert, BentoCard, EmptyState, Spinner } from "./ui";
import { formatHistoryDate } from "../history";

type Props = { dossier: PlacementDossier };
type Audience = "JOINT" | "ACADEMIC";

export default function PlacementMessages({ dossier }: Props) {
  const scopes: Audience[] = [
    ...(dossier.capabilities.read_joint_messages ? ["JOINT" as const] : []),
    ...(dossier.capabilities.read_academic_messages ? ["ACADEMIC" as const] : []),
  ];
  const [audience, setAudience] = useState<Audience>(scopes[0] ?? "JOINT");
  const [rows, setRows] = useState<PlacementMessage[] | null>(null);
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!scopes.includes(audience)) setAudience(scopes[0] ?? "JOINT");
  }, [audience, dossier.placement.id, dossier.capabilities.read_joint_messages, dossier.capabilities.read_academic_messages]);

  useEffect(() => {
    if (!scopes.includes(audience)) { setRows(null); return; }
    let current = true;
    setRows(null);
    setError(null);
    api.listPlacementMessages(dossier.placement.id, audience)
      .then((messages) => { if (current) setRows(messages); })
      .catch((cause: unknown) => {
        if (current) setError(cause instanceof Error ? cause.message : "No fue posible cargar la conversación.");
      });
    return () => { current = false; };
  }, [dossier.placement.id, audience, attempt]);

  async function send(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await api.sendPlacementMessage(dossier.placement.id, audience, content);
      setRows((current) => [...(current ?? []), saved]);
      setContent("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No fue posible guardar el mensaje.");
    } finally {
      setBusy(false);
    }
  }

  if (!scopes.length) return null;
  return (
    <BentoCard variant="content" className="dossier-wide" title="Conversación de la práctica" description="Mensajes vinculados al expediente; solo participantes autorizados pueden consultarlos.">
      {error && <Alert kind="error">{error} <button className="btn link" type="button" onClick={() => setAttempt((value) => value + 1)}>Reintentar</button></Alert>}
      {scopes.length > 1 && <div className="message-scopes" role="tablist" aria-label="Ámbito de conversación">
        {scopes.map((scope) => <button key={scope} type="button" role="tab" aria-selected={audience === scope}
          className={`btn ${audience === scope ? "" : "secondary"}`} onClick={() => setAudience(scope)}>
          {scope === "JOINT" ? "Práctica" : "Académico"}
        </button>)}
      </div>}
      {audience === "ACADEMIC" && <p className="muted">El canal académico está disponible para estudiante, supervisión docente, coordinación y EC. La supervisión laboral no tiene acceso.</p>}
      {rows === null && !error && <div className="empty"><Spinner /> Cargando conversación…</div>}
      {rows?.length === 0 && <EmptyState message="Aún no hay mensajes en esta conversación." />}
      {!!rows?.length && <ol className="message-list" aria-label="Historial de mensajes">
        {rows.map((message) => <li key={message.id}>
          <div className="row"><strong>{message.author_name}</strong><time dateTime={message.created_at}>{formatHistoryDate(message.created_at)}</time></div>
          <p className="dossier-preserve-text">{message.content}</p>
        </li>)}
      </ol>}
      <form className="follow-up-form message-form" onSubmit={(event) => void send(event)}>
        <label className="field">Escribir un mensaje
          <textarea value={content} maxLength={4000} rows={3} required aria-label="Mensaje de la práctica"
            onChange={(event) => setContent(event.currentTarget.value)} />
        </label>
        <button className="btn" type="submit" disabled={busy || !content.trim()}>{busy ? <Spinner /> : "Enviar mensaje"}</button>
      </form>
    </BentoCard>
  );
}
