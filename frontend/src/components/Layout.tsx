import type { ReactNode } from "react";
import type { User } from "../api";
import { formatDomainLabel, Icon, type IconName } from "./ui";

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

type NavItem = { id: SectionId; label: string; icon: IconName };
type NavGroup = { label: string; items: NavItem[] };

export default function Layout({ user, active, onNavigate, onLogout, children }: Props) {
  const roles = user.roles.map((role) => role.role);
  const roleSummary = [...new Set(user.roles.map((role) => formatDomainLabel(role.role)))].join(" · ");
  const viewTitle = active === "home" ? `Hola, ${user.display_name.split(" ")[0]}` : SECTION_TITLES[active];
  const groups: NavGroup[] = [
    { label: "Principal", items: [
      { id: "home", label: "Inicio", icon: "home" },
      { id: "opportunities", label: "Oportunidades", icon: "briefcase" },
    ] },
  ];
  if (roles.includes("STUDENT")) {
    groups.push({ label: "Mi práctica", items: [
      { id: "applications", label: "Mis postulaciones", icon: "clipboard" },
      { id: "documents", label: "Mis documentos", icon: "document" },
    ] });
  }
  if (roles.includes("PROGRAM_COORDINATOR")) {
    groups.push({ label: "Coordinación", items: [
      { id: "academic", label: "Revisión académica", icon: "academic" },
      { id: "policies", label: "Políticas", icon: "settings" },
    ] });
  }
  if (roles.includes("LEGAL_REVIEWER")) {
    groups.push({ label: "Revisión", items: [{ id: "docreview", label: "Revisión documental", icon: "review" }] });
  }
  if (roles.includes("EXPERIENTIAL_COORDINATOR")) {
    groups.push({ label: "Operación", items: [{ id: "activation", label: "Activación", icon: "check" }] });
  }

  const initial = (user.display_name || "?").trim().charAt(0).toLocaleUpperCase("es");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" type="button" onClick={() => onNavigate("home")} aria-label="DH-05, ir al inicio">
          <span className="brand-mark" aria-hidden="true">D</span>
          <span className="brand-wordmark">DH-05<small>Ciclo de prácticas</small></span>
        </button>

        <nav className="sidebar-nav" aria-label="Navegación principal">
          {groups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-caption">{group.label}</span>
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`nav ${active === item.id ? "active" : ""}`}
                  aria-current={active === item.id ? "page" : undefined}
                  onClick={() => onNavigate(item.id)}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-account">
          <div className="account-profile">
            <span className="avatar" aria-hidden="true">{initial}</span>
            <span className="user-meta">
              <strong>{user.display_name}</strong>
              <span>{roleSummary}</span>
            </span>
          </div>
          <button className="logout-button" type="button" onClick={onLogout}>
            <Icon name="logout" />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-context">
            <span className="topbar-kicker">DH-05 · ESPACIO DE TRABAJO</span>
            <h1>{viewTitle}</h1>
          </div>
          <span className="topbar-product">Prácticas y pasantías</span>
        </header>
        <main className="content" id="main-content">{children}</main>
      </div>
    </div>
  );
}
