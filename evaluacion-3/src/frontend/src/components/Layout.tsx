import { useEffect, useState, type ReactNode } from "react";
import type { User } from "../api";
import { formatDomainLabel, Icon, type IconName } from "./ui";
import { ThemeControl } from "../theme";

export type SectionId =
  | "home"
  | "opportunities"
  | "applications"
  | "academic"
  | "policies"
  | "documents"
  | "docreview"
  | "activation"
  | "dossier"
  | "notifications"
  | "reports";

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
  dossier: "Expediente de práctica",
  notifications: "Notificaciones",
  reports: "Reportes operativos",
};

type NavItem = { id: SectionId; label: string; icon: IconName };
type NavGroup = { label: string; items: NavItem[] };

export default function Layout({ user, active, onNavigate, onLogout, children }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const roles = user.roles.map((role) => role.role);
  const roleSummary = [...new Set(user.roles.map((role) => formatDomainLabel(role.role)))].join(" · ");
  const viewTitle = active === "home" ? "Inicio" : SECTION_TITLES[active];
  const groups: NavGroup[] = [
    { label: "Principal", items: [
      { id: "home", label: "Inicio", icon: "home" },
      { id: "opportunities", label: "Oportunidades", icon: "briefcase" },
      { id: "notifications", label: "Notificaciones", icon: "bell" },
    ] },
  ];
  if (roles.some((role) => [
    "STUDENT", "HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR", "FACULTY_SUPERVISOR",
    "PROGRAM_COORDINATOR", "EXPERIENTIAL_COORDINATOR", "LEGAL_REVIEWER",
  ].includes(role))) {
    groups.push({ label: "Ciclo de vida", items: [
      { id: "dossier", label: "Expedientes", icon: "clipboard" },
    ] });
  }
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
      { id: "reports", label: "Reportes operativos", icon: "review" },
    ] });
  }
  if (roles.includes("LEGAL_REVIEWER")) {
    groups.push({ label: "Revisión", items: [{ id: "docreview", label: "Revisión documental", icon: "review" }] });
  }
  if (roles.includes("EXPERIENTIAL_COORDINATOR")) {
    groups.push({ label: "Operación", items: [
      { id: "activation", label: "Activación", icon: "check" },
      { id: "reports", label: "Reportes operativos", icon: "review" },
    ] });
  }
  const seenSections = new Set<SectionId>();
  const visibleGroups = groups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => {
        if (seenSections.has(item.id)) return false;
        seenSections.add(item.id);
        return true;
      }),
    }))
    .filter((group) => group.items.length > 0);

  const initial = (user.display_name || "?").trim().charAt(0).toLocaleUpperCase("es");

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setMobileMenuOpen(false);
      document.getElementById("mobile-menu-toggle")?.focus();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileMenuOpen]);

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""} ${mobileMenuOpen ? "mobile-menu-open" : ""}`}>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >Saltar al contenido</a>
      <aside className="sidebar">
        <button className="brand" type="button" onClick={() => {
          onNavigate("home");
          setMobileMenuOpen(false);
        }} aria-label="DH-05, ir al inicio">
          <span className="brand-mark" aria-hidden="true">D</span>
          <span className="brand-wordmark">DH-05<small>Ciclo de prácticas</small></span>
        </button>
        <button
          id="mobile-menu-toggle"
          className="mobile-menu-toggle"
          type="button"
          aria-controls="primary-navigation"
          aria-expanded={mobileMenuOpen}
          aria-label={mobileMenuOpen ? "Cerrar menú de navegación" : "Abrir menú de navegación"}
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          <span aria-hidden="true">{mobileMenuOpen ? "×" : "☰"}</span>
          <span>{mobileMenuOpen ? "Cerrar" : "Menú"}</span>
        </button>
        <button className="sidebar-collapse" type="button" aria-label={collapsed ? "Expandir navegación" : "Contraer navegación"} aria-expanded={!collapsed} onClick={() => setCollapsed((value) => !value)}>
          <span aria-hidden="true">{collapsed ? "›" : "‹"}</span><span className="collapse-label">{collapsed ? "Expandir" : "Contraer menú"}</span>
        </button>

        <nav id="primary-navigation" className="sidebar-nav" aria-label="Navegación principal">
          {visibleGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-caption">{group.label}</span>
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`nav ${active === item.id ? "active" : ""}`}
                  aria-current={active === item.id ? "page" : undefined}
                  aria-label={item.label}
                  title={collapsed ? item.label : undefined}
                  onClick={() => {
                    onNavigate(item.id);
                    setMobileMenuOpen(false);
                  }}
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
          <button className="logout-button" type="button" aria-label="Cerrar sesión" title={collapsed ? "Cerrar sesión" : undefined} onClick={onLogout}>
            <Icon name="logout" />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-context">
            <span className="topbar-kicker">DH-05 · ESPACIO DE TRABAJO</span>
            <p className="topbar-title" aria-hidden="true">{viewTitle}</p>
          </div>
          <div className="topbar-actions"><span className="topbar-product">Prácticas y pasantías</span><ThemeControl /></div>
        </header>
        <main className="content" id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
