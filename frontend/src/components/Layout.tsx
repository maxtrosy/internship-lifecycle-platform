import type { ReactNode } from "react";
import type { User } from "../api";
import { formatDomainLabel } from "./ui";

export type SectionId =
  | "home"
  | "opportunities"
  | "applications"
  | "academic"
  | "policies"
  | "documents"
  | "docreview"
  | "activation";

type Props = {
  user: User;
  active: SectionId;
  onNavigate: (s: SectionId) => void;
  onLogout: () => void;
  children: ReactNode;
};

const SECTION_TITLES: Record<SectionId, string> = {
  home: "Inicio",
  opportunities: "Oportunidades",
  applications: "Mis postulaciones",
  academic: "Revisión académica",
  policies: "Políticas del programa",
  documents: "Mis documentos",
  docreview: "Revisión documental",
  activation: "Activación de prácticas",
};

export default function Layout({ user, active, onNavigate, onLogout, children }: Props) {
  const roles = user.roles.map((role) => role.role);
  const isStudent = roles.includes("STUDENT");
  const isAcademic = roles.includes("PROGRAM_COORDINATOR");
  const isLegal = roles.includes("LEGAL_REVIEWER");
  const isEc = roles.includes("EXPERIENTIAL_COORDINATOR");

  const items: { id: SectionId; label: string; marker: string }[] = [
    { id: "home", label: "Inicio", marker: "01" },
    { id: "opportunities", label: "Oportunidades", marker: "02" },
  ];
  if (isStudent) {
    items.push({ id: "applications", label: "Mis postulaciones", marker: "03" });
    items.push({ id: "documents", label: "Mis documentos", marker: "04" });
  }
  if (isAcademic) {
    items.push({ id: "academic", label: "Revisión académica", marker: "05" });
    items.push({ id: "policies", label: "Políticas", marker: "06" });
  }
  if (isLegal) items.push({ id: "docreview", label: "Revisión documental", marker: "07" });
  if (isEc) items.push({ id: "activation", label: "Activación", marker: "08" });

  const initial = (user.display_name || "?").trim().charAt(0).toUpperCase();
  const roleSummary = [...new Set(user.roles.map((role) => formatDomainLabel(role.role)))].join(" · ");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" type="button" onClick={() => onNavigate("home")} aria-label="DH-05, ir al inicio">
          <span className="brand-mark" aria-hidden="true">D</span>
          <span className="brand-wordmark">DH-05<small>Prácticas y pasantías</small></span>
        </button>
        <nav className="sidebar-nav" aria-label="Navegación principal">
          <span className="nav-caption">Espacio de trabajo</span>
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav ${active === item.id ? "active" : ""}`}
              aria-current={active === item.id ? "page" : undefined}
              onClick={() => onNavigate(item.id)}
            >
              <span className="nav-marker" aria-hidden="true">{item.marker}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footnote">
          <span className="status-dot" aria-hidden="true" />
          <span>Entorno local · DH-05</span>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-context">
            <span className="topbar-kicker">DH-05 / ESPACIO DE TRABAJO</span>
            <h1>{SECTION_TITLES[active]}</h1>
          </div>
          <div className="topbar-actions">
            <div className="user">
              <span className="avatar" aria-hidden="true">{initial}</span>
              <span className="user-meta">
                <strong>{user.display_name}</strong>
                <span className="muted">{roleSummary}</span>
              </span>
            </div>
            <span className="topbar-divider" aria-hidden="true" />
            <button className="btn secondary logout-button" type="button" onClick={onLogout}>Cerrar sesión</button>
          </div>
        </header>
        <main className="content" id="main-content">{children}</main>
      </div>
    </div>
  );
}
