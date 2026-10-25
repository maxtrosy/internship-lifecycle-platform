import { useState } from "react";
import * as api from "../api";
import type { User } from "../api";
import { Alert, Spinner } from "../components/ui";
import { demoLoginPassword } from "../demoLogin";

type DemoAccount = {
  name: string;
  usernames: string[];
  roles: string;
};

const ACCOUNTS: DemoAccount[] = [
  { name: "Student One", usernames: ["student1", "s1"], roles: "Estudiante · ING-SIS" },
  { name: "Student Two", usernames: ["student2", "s2"], roles: "Estudiante · ING-SIS" },
  { name: "Student Three", usernames: ["student3", "s3"], roles: "Estudiante · ADM" },
  { name: "Host Member Alfa", usernames: ["hm_alfa"], roles: "Representante de Org Alfa" },
  { name: "Host Member Beta", usernames: ["hm_beta"], roles: "Representante de Org Beta" },
  { name: "Coord Sys", usernames: ["pc_sys"], roles: "Coordinador · ING-SIS" },
  { name: "Coord Adm", usernames: ["pc_adm"], roles: "Coordinador · ADM" },
  { name: "Experiential Coord 1", usernames: ["ec1"], roles: "Coordinador de prácticas" },
  { name: "Legal Reviewer", usernames: ["legal1"], roles: "Revisor jurídico" },
  { name: "Workplace Sup Alfa", usernames: ["ws_alfa"], roles: "Supervisor de empresa · Alfa" },
  { name: "Workplace Sup Alfa 2", usernames: ["ws_alfa2"], roles: "Supervisor de empresa · Alfa" },
  { name: "Workplace Sup Beta", usernames: ["ws_beta"], roles: "Supervisor de empresa · Beta" },
  { name: "Faculty Sup 1", usernames: ["faculty1", "f1"], roles: "Supervisor académico" },
  { name: "Dual Coordinator/Faculty", usernames: ["dual1"], roles: "Coordinador · Supervisor académico" },
];

export default function DemoLogin({
  onLoggedIn,
  onBack,
}: {
  onLoggedIn: (user: User) => void;
  onBack: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function signIn(account: DemoAccount) {
    if (busy) return;
    setBusy(account.name);
    setError(null);
    try {
      let authenticated = false;
      for (const username of account.usernames) {
        try {
          await api.login(username, demoLoginPassword);
          authenticated = true;
          break;
        } catch (err) {
          const message = err instanceof Error ? err.message : "";
          if (!message.includes("Tu sesión terminó") && !message.includes("no son correctos")) throw err;
        }
      }
      if (!authenticated) {
        setError("No se pudo iniciar sesión con esa cuenta. Revisa que los usuarios de prueba estén disponibles.");
        return;
      }
      onLoggedIn(await api.me());
    } catch {
      setError("No se pudo completar el acceso. Inténtalo de nuevo en unos segundos.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="demo-login-page">
      <div className="demo-login-header">
        <div>
          <span className="eyebrow">DH-05 · DEMOSTRACIÓN</span>
          <h1>Cuentas de prueba</h1>
          <p>Elige un perfil para entrar directamente. Cada acceso usa la sesión normal de la aplicación.</p>
        </div>
        <button className="btn secondary" type="button" onClick={onBack}>Volver al inicio de sesión</button>
      </div>

      {error && <Alert kind="error">{error}</Alert>}
      <div className="demo-account-grid">
        {ACCOUNTS.map((account) => (
          <button
            className="demo-account-card"
            type="button"
            key={account.name}
            disabled={busy !== null}
            onClick={() => void signIn(account)}
          >
            <span className="demo-account-copy">
              <strong>{account.name}</strong>
              <small>{account.roles}</small>
            </span>
            <span className="demo-account-action">
              {busy === account.name ? <Spinner /> : "Entrar →"}
            </span>
          </button>
        ))}
      </div>
      <p className="demo-login-note">Solo cuentas sintéticas de este entorno local. No hay registro ni usuarios reales en esta lista.</p>
    </main>
  );
}
