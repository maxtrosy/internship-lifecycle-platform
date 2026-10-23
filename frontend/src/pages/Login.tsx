import { useState } from "react";
import * as api from "../api";
import type { User } from "../api";

export default function Login({ onLoggedIn }: { onLoggedIn: (u: User) => void }) {
  const [userId, setUserId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const { access_token } = await api.login(Number(userId));
      api.setToken(access_token);
      onLoggedIn(await api.me());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div style={{ maxWidth: 320, margin: "80px auto", fontFamily: "sans-serif" }}>
      <h1>Ingresar</h1>
      <p style={{ color: "#666" }}>Identidad simulada: ingresa el id de usuario sintético (p. ej. 1, 6, 8…).</p>
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          type="number"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="user_id"
          required
        />
        <button type="submit">Entrar</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}
