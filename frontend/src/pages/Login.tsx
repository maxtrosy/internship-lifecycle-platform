import { useState } from "react";
import * as api from "../api";
import type { User } from "../api";
import { Alert, Spinner } from "../components/ui";
import { isDemoLoginEnabled } from "../demoLogin";

type Mode = "login" | "request-reset" | "complete-reset";

export default function Login({ onLoggedIn }: { onLoggedIn: (u: User) => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function readableError(err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    if (mode === "login" && (message === "unauthorized" || message === "Tu sesión terminó. Inicia sesión nuevamente.")) {
      return "El correo/usuario o la contraseña no son correctos.";
    }
    if (message === "too_many_requests") return "Demasiados intentos. Espera unos minutos e inténtalo de nuevo.";
    if (message.includes("PASSWORD_RESET_INVALID") || message.includes("inválido o venció")) {
      return "El enlace de recuperación es inválido o venció. Solicita uno nuevo.";
    }
    return message;
  }

  async function submitLogin(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      await api.login(identifier, password);
      onLoggedIn(await api.me());
    } catch (err) {
      setError(readableError(err));
    } finally {
      setLoading(false);
    }
  }

  async function requestReset(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setError(null);
    setNotice(null);
    setLoading(true);
    try {
      const result = await api.requestPasswordReset(email);
      setNotice(result.message);
      if (result.development_token) {
        setResetToken(result.development_token);
        setMode("complete-reset");
      }
    } catch (err) {
      setError(readableError(err));
    } finally {
      setLoading(false);
    }
  }

  async function completeReset(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setLoading(true);
    try {
      await api.completePasswordReset(resetToken, newPassword);
      setMode("login");
      setPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setResetToken("");
      setNotice("Contraseña actualizada. Inicia sesión con tu nueva contraseña.");
    } catch (err) {
      setError(readableError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <aside className="login-brand">
        <div>
          <span className="mark">DH-05 · Acceso seguro</span>
          <h1>Gestión integral de prácticas y pasantías</h1>
          <p>
            Una sola plataforma para todo el ciclo: oportunidades, postulaciones,
            selección, aprobación académica, documentación y activación, con
            trazabilidad y control de acceso por rol.
          </p>
          <ul className="login-features">
            <li>Estudiantes: postúlate y sigue el estado de tu práctica.</li>
            <li>Empleadores: publica oportunidades y selecciona candidatos.</li>
            <li>Coordinadores: aprueba, revisa documentos y activa prácticas.</li>
          </ul>
        </div>
      </aside>

      <main className="login-panel">
        <div className="card auth-card">
          <div className="auth-hero">
            <h2>
              {mode === "login" ? "Iniciar sesión" : mode === "request-reset" ? "Recuperar contraseña" : "Crear nueva contraseña"}
            </h2>
            <p>
              {mode === "login"
                ? "Ingresa con tu cuenta local de DH-05. Este acceso no usa SSO institucional."
                : mode === "request-reset"
                  ? "Solicita un enlace para recuperar el acceso a tu cuenta."
                  : "Elige una contraseña nueva para tu cuenta."}
            </p>
          </div>

          {mode === "login" && (
            <form onSubmit={submitLogin}>
              <div className="field">
                <label htmlFor="identifier">Correo electrónico o nombre de usuario</label>
                <input
                  id="identifier"
                  type="text"
                  autoComplete="username"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="nombre@ejemplo.edu o usuario"
                  autoFocus
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="password">Contraseña</label>
                <div className="password-input-row">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button className="btn secondary password-toggle" type="button" onClick={() => setShowPassword((v) => !v)}>
                    {showPassword ? "Ocultar" : "Mostrar"}
                  </button>
                </div>
              </div>

              {error && <Alert kind="error">{error}</Alert>}
              {notice && <Alert kind="success">{notice}</Alert>}

              <button className="btn login-submit" type="submit" disabled={loading || !identifier || !password}>
                {loading ? <><Spinner /> Verificando…</> : "Ingresar"}
              </button>
              <button className="btn link login-link" type="button" onClick={() => { setMode("request-reset"); setError(null); setNotice(null); }}>
                ¿Olvidaste tu contraseña?
              </button>
              {isDemoLoginEnabled() && (
                <button className="btn secondary login-demo-link" type="button" onClick={() => { window.location.hash = "/demo-login"; }}>
                  Entrar con una cuenta de prueba
                </button>
              )}
              <p className="muted login-footnote">No hay registro público. Las cuentas se aprovisionan por el operador o mediante invitación.</p>
            </form>
          )}

          {mode === "request-reset" && (
            <form onSubmit={requestReset}>
              <div className="field">
                <label htmlFor="reset-email">Correo de la cuenta</label>
                <input
                  id="reset-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              {error && <Alert kind="error">{error}</Alert>}
              {notice && <Alert kind="info">{notice}</Alert>}
              {notice && !resetToken && <p className="muted login-footnote">Esta instalación no tiene un proveedor de correo conectado. En desarrollo local, pide al operador que habilite la recuperación.</p>}
              <button className="btn login-submit" type="submit" disabled={loading || !email}>
                {loading ? <><Spinner /> Procesando…</> : "Solicitar recuperación"}
              </button>
              <button className="btn link login-link" type="button" onClick={() => { setMode("login"); setError(null); setNotice(null); }}>
                Volver al inicio de sesión
              </button>
            </form>
          )}

          {mode === "complete-reset" && (
            <form onSubmit={completeReset}>
              <p className="muted">Token local de desarrollo, válido por 30 minutos y de un solo uso.</p>
              <div className="field">
                <label htmlFor="reset-token">Token de recuperación</label>
                <input id="reset-token" value={resetToken} onChange={(e) => setResetToken(e.target.value)} required />
              </div>
              <div className="field">
                <label htmlFor="new-password">Nueva contraseña</label>
                <input id="new-password" type="password" autoComplete="new-password" minLength={12} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
              </div>
              <div className="field">
                <label htmlFor="confirm-password">Confirmar contraseña</label>
                <input id="confirm-password" type="password" autoComplete="new-password" minLength={12} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
              </div>
              {error && <Alert kind="error">{error}</Alert>}
              <button className="btn login-submit" type="submit" disabled={loading || newPassword.length < 12 || !resetToken}>
                {loading ? <><Spinner /> Actualizando…</> : "Actualizar contraseña"}
              </button>
              <button className="btn link login-link" type="button" onClick={() => { setMode("login"); setError(null); setNotice(null); }}>
                Cancelar
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
