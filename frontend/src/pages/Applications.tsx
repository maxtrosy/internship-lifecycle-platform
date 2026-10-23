import { useEffect, useState } from "react";
import * as api from "../api";
import type { Application } from "../api";

export default function Applications() {
  const [items, setItems] = useState<Application[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listApplications().then(setItems).catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <section>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Oportunidad</th>
            <th>Estado</th>
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td>
              <td>{a.title}</td>
              <td>{a.state}</td>
              <td>{JSON.stringify(a.eligibility_result)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
