import { useEffect, useState } from "react";
import * as api from "../api";
import type { Opportunity, User } from "../api";

export default function Opportunities({ user }: { user: User }) {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [hostOrg, setHostOrg] = useState("1");
  const [program, setProgram] = useState("1");
  const [message, setMessage] = useState<string | null>(null);

  const isCreator = user.roles.some(
    (r) => r.role === "HOST_ORG_MEMBER" || r.role === "PROGRAM_COORDINATOR",
  );
  const isStudent = user.roles.some((r) => r.role === "STUDENT");

  async function reload() {
    try {
      setItems(await api.listOpportunities());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await api.createOpportunity({ host_org_id: Number(hostOrg), program_id: Number(program), title });
      setTitle("");
      setMessage("Oportunidad creada");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function apply(id: number) {
    setError(null);
    setMessage(null);
    try {
      const res = await api.apply(id);
      setMessage(`Postulación: ${JSON.stringify(res)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <section>
      {isCreator && (
        <form onSubmit={create} style={{ display: "flex", gap: 6, marginBottom: 12 }}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Título" required />
          <input value={hostOrg} onChange={(e) => setHostOrg(e.target.value)} placeholder="org" style={{ width: 60 }} />
          <input value={program} onChange={(e) => setProgram(e.target.value)} placeholder="prog" style={{ width: 60 }} />
          <button type="submit">Publicar</button>
        </form>
      )}
      {message && <p style={{ color: "green" }}>{message}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Título</th>
            <th>Programa</th>
            <th>Organización</th>
            <th>Estado</th>
            {isStudent && <th />}
          </tr>
        </thead>
        <tbody>
          {items.map((o) => (
            <tr key={o.id}>
              <td>{o.id}</td>
              <td>{o.title}</td>
              <td>{o.program_code}</td>
              <td>{o.host_name}</td>
              <td>{o.state}</td>
              {isStudent && (
                <td>
                  <button onClick={() => apply(o.id)} disabled={o.state !== "PUBLISHED"}>
                    Postular
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
