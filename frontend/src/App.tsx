import { useEffect, useState } from "react";
import * as api from "./api";
import type { User } from "./api";
import Login from "./pages/Login";
import Opportunities from "./pages/Opportunities";
import Applications from "./pages/Applications";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<"opportunities" | "applications">("opportunities");

  useEffect(() => {
    if (api.getToken() && !user) {
      api.me().then(setUser).catch(() => api.setToken(null));
    }
  }, [user]);

  if (!user) {
    return <Login onLoggedIn={setUser} />;
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", fontFamily: "sans-serif", padding: 16 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>DH-05 · Pasantías</h1>
        <div>
          <span>{user.display_name}</span>{" "}
          <button
            onClick={() => {
              api.setToken(null);
              setUser(null);
            }}
          >
            Salir
          </button>
        </div>
      </header>
      <nav style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button onClick={() => setTab("opportunities")}>Oportunidades</button>
        <button onClick={() => setTab("applications")}>Mis postulaciones</button>
      </nav>
      {tab === "opportunities" ? <Opportunities user={user} /> : <Applications />}
    </div>
  );
}
