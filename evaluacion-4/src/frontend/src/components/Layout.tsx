import { useEffect, useRef, useState, type MouseEvent, type ReactNode } from "react";
import * as api from "../api";
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

const ALL_ROLES = [
  "STUDENT", "HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR", "FACULTY_SUPERVISOR",
  "PROGRAM_COORDINATOR", "EXPERIENTIAL_COORDINATOR", "LEGAL_REVIEWER",
];

/**
 * Navigation groups derived only from the roles the account already has. The
 * visibility rules mirror `canAccessSection` in App.tsx; nothing is added.
 */
function navigationFor(roles: string[]): NavGroup[] {
  const groups: NavGroup[] = [
    { label: "Principal", items: [
      { id: "home", label: "Inicio", icon: "home" },
      { id: "opportunities", label: "Oportunidades", icon: "briefcase" },
      { id: "notifications", label: "Notificaciones", icon: "bell" },
    ] },
  ];
  if (roles.some((role) => ALL_ROLES.includes(role))) {
    groups.push({ label: "Ciclo de vida", items: [{ id: "dossier", label: "Expedientes", icon: "clipboard" }] });
  }
  if (roles.includes("STUDENT")) {
    groups.push({ label: "Mi práctica", items: [
      { id: "applications", label: "Mis postulaciones", icon: "inbox" },
      { id: "documents", label: "Mis documentos", icon: "document" },
    ] });
  }
  if (roles.includes("PROGRAM_COORDINATOR")) {
    groups.push({ label: "Coordinación", items: [
      { id: "academic", label: "Revisión académica", icon: "academic" },
      { id: "policies", label: "Políticas", icon: "settings" },
      { id: "reports", label: "Reportes operativos", icon: "chart" },
    ] });
  }
  if (roles.includes("LEGAL_REVIEWER")) {
    groups.push({ label: "Revisión", items: [{ id: "docreview", label: "Revisión documental", icon: "review" }] });
  }
  if (roles.includes("EXPERIENTIAL_COORDINATOR")) {
    groups.push({ label: "Operación", items: [
      { id: "activation", label: "Activación", icon: "check" },
      { id: "reports", label: "Reportes operativos", icon: "chart" },
    ] });
  }
  const seen = new Set<SectionId>();
  return groups
    .map((group) => ({ ...group, items: group.items.filter((item) => (seen.has(item.id) ? false : (seen.add(item.id), true))) }))
    .filter((group) => group.items.length > 0);
}

/** Plain left clicks are handled in-app; modified clicks keep native link behavior (new tab, etc.). */
function isPlainClick(event: MouseEvent) {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

function useUnreadNotifications(active: SectionId): number | null {
  const [unread, setUnread] = useState<number | null>(null);
  useEffect(() => {
    let cancelled = false;
    api.listNotifications()
      .then((items) => { if (!cancelled) setUnread(Array.isArray(items) ? items.filter((item) => !item.is_read).length : null); })
      .catch(() => { if (!cancelled) setUnread(null); });
    return () => { cancelled = true; };
  }, [active]);
  return unread;
}

export default function Layout({ user, active, onNavigate, onLogout, children }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const mainRef = useRef<HTMLDivElement>(null);
  const roles = user.roles.map((role) => role.role);
  const roleLabels = [...new Set(user.roles.map((role) => formatDomainLabel(role.role)))];
  const viewTitle = SECTION_TITLES[active];
  const groups = navigationFor(roles);
  const unread = useUnreadNotifications(active);
  const initial = (user.display_name || "?").trim().charAt(0).toLocaleUpperCase("es");

  const go = (section: SectionId) => (event: MouseEvent) => {
    if (!isPlainClick(event)) return;
    event.preventDefault();
    onNavigate(section);
    setMobileMenuOpen(false);
  };

  useEffect(() => {
    if (!mobileMenuOpen && !profileOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (profileOpen) {
        setProfileOpen(false);
        document.getElementById("user-menu-button")?.focus();
        return;
      }
      setMobileMenuOpen(false);
      document.getElementById("mobile-menu-toggle")?.focus();
    };
    const handlePointer = (event: PointerEvent) => {
      if (profileOpen && profileRef.current && !profileRef.current.contains(event.target as Node)) setProfileOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("pointerdown", handlePointer);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("pointerdown", handlePointer);
    };
  }, [mobileMenuOpen, profileOpen]);

  // Mobile navigation drawer: move focus inside, keep Tab/Shift+Tab within the
  // drawer, make the page behind it inert, and close it if the viewport grows.
  useEffect(() => {
    if (!mobileMenuOpen) return;
    const drawer = sidebarRef.current;
    const page = mainRef.current;
    if (!drawer) return;
    page?.setAttribute("inert", "");
    const focusable = () => Array.from(drawer.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )).filter((element) => element.offsetParent !== null);
    const current = drawer.querySelector<HTMLElement>('.sidebar-nav a[aria-current="page"]');
    (current ?? drawer.querySelector<HTMLElement>(".sidebar-nav a") ?? focusable()[0])?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const items = focusable();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || !drawer.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !drawer.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };
    const desktop = window.matchMedia("(min-width: 768px)");
    const closeOnDesktop = () => { if (desktop.matches) setMobileMenuOpen(false); };
    document.addEventListener("keydown", trap);
    desktop.addEventListener("change", closeOnDesktop);
    return () => {
      page?.removeAttribute("inert");
      document.removeEventListener("keydown", trap);
      desktop.removeEventListener("change", closeOnDesktop);
    };
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

      <aside className="sidebar" ref={sidebarRef}>
        <div className="sidebar-top">
          <a className="brand" href="#/home" onClick={go("home")} aria-label="Prácticas y Pasantías, ir al inicio">
            {/* Neutral placeholder: the official crest must be supplied by the institution. */}
            <span className="brand-mark" aria-hidden="true"><Icon name="academic" /></span>
            <span className="brand-wordmark">Prácticas y Pasantías<small><span translate="no">DH-05</span> · Gestión de prácticas</small></span>
          </a>
          <button
            id="mobile-menu-toggle"
            className="mobile-menu-toggle"
            type="button"
            aria-controls="primary-navigation"
            aria-expanded={mobileMenuOpen}
            aria-label={mobileMenuOpen ? "Cerrar menú de navegación" : "Abrir menú de navegación"}
            onClick={() => setMobileMenuOpen((open) => !open)}
          >
            <Icon name={mobileMenuOpen ? "close" : "menu"} />
            <span>{mobileMenuOpen ? "Cerrar" : "Menú"}</span>
          </button>
        </div>

        <nav id="primary-navigation" className="sidebar-nav" aria-label="Navegación principal">
          {groups.map((group) => (
            <div className="nav-group" key={group.label} role="group" aria-labelledby={`nav-group-${group.label}`}>
              <span className="nav-caption" id={`nav-group-${group.label}`}>{group.label}</span>
              {group.items.map((item) => (
                <a
                  key={item.id}
                  href={`#/${item.id}`}
                  className={`nav ${active === item.id ? "active" : ""}`}
                  aria-current={active === item.id ? "page" : undefined}
                  title={collapsed ? item.label : undefined}
                  onClick={go(item.id)}
                >
                  <Icon name={item.icon} />
                  <span className="nav-label">{item.label}</span>
                  {item.id === "notifications" && unread ? <span className="nav-count" aria-hidden="true">{unread}</span> : null}
                </a>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="sidebar-collapse" type="button" aria-label={collapsed ? "Expandir navegación" : "Contraer navegación"} aria-expanded={!collapsed} onClick={() => setCollapsed((value) => !value)}>
            <Icon name={collapsed ? "chevron-right" : "chevron-left"} />
            <span className="collapse-label">Contraer menú</span>
          </button>
          <span className="sidebar-env">Entorno de demostración con datos sintéticos</span>
        </div>
      </aside>

      <div className="main" ref={mainRef}>
        <header className="topbar">
          <nav className="topbar-context breadcrumbs" aria-label="Ruta de navegación">
            <ol>
              {active !== "home" && (
                <li><a href="#/home" onClick={go("home")}>Inicio</a><Icon name="chevron-right" className="breadcrumb-sep" /></li>
              )}
              <li><span className="topbar-title" aria-current="page">{viewTitle}</span></li>
            </ol>
          </nav>
          <div className="topbar-actions">
            <a
              className={`header-icon-button ${active === "notifications" ? "active" : ""}`}
              href="#/notifications"
              onClick={go("notifications")}
              aria-label={unread ? `Avisos, ${unread} sin leer` : "Avisos"}
              title="Avisos"
            >
              <Icon name="bell" />
              {unread ? <span className="header-count" aria-hidden="true">{unread > 99 ? "99+" : unread}</span> : null}
            </a>
            <ThemeControl />
            <div className="user-menu" ref={profileRef}>
              <button
                id="user-menu-button"
                className="user-menu-button"
                type="button"
                aria-haspopup="true"
                aria-expanded={profileOpen}
                aria-controls="user-menu-panel"
                onClick={() => setProfileOpen((open) => !open)}
              >
                <span className="avatar" aria-hidden="true">{initial}</span>
                <span className="user-meta">
                  <strong>{user.display_name}</strong>
                  <span>{roleLabels[0]}{roleLabels.length > 1 ? ` +${roleLabels.length - 1}` : ""}</span>
                </span>
                <Icon name="chevron-down" className="user-menu-chevron" />
                <span className="sr-only">Perfil de usuario</span>
              </button>
              {profileOpen && (
                <div className="user-menu-panel" id="user-menu-panel">
                  <p className="user-menu-name">{user.display_name}</p>
                  <p className="user-menu-caption">Roles asignados</p>
                  <ul className="user-menu-roles">
                    {roleLabels.map((label) => <li key={label}>{label}</li>)}
                  </ul>
                  <p className="user-menu-caption">Los permisos de cada sección dependen de estos roles.</p>
                </div>
              )}
            </div>
            <button className="logout-button" type="button" aria-label="Cerrar sesión" title="Cerrar sesión" onClick={onLogout}>
              <Icon name="logout" />
              <span className="logout-label">Cerrar sesión</span>
            </button>
          </div>
        </header>
        <main className="content" id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
