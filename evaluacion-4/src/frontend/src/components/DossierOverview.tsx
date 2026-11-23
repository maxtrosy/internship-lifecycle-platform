// F6: dossier header pieces — lifecycle stepper, current situation and the
// in-page section navigation. Everything is derived from the persisted dossier
// projection; nothing here adds states or rules.
import { useEffect, useState, type RefObject } from "react";
import type { PlacementDossier } from "../api";
import { Icon, formatDomainLabel, type IconName } from "./ui";
import { formatHours, numeric } from "../segments";

const LIFECYCLE_STEPS = [
  { label: "Selección", detail: "Candidatura seleccionada por la organización" },
  { label: "Aprobación académica", detail: "Decisión de la coordinación de programa" },
  { label: "Documentación y activación", detail: "Requisitos previos y activación" },
  { label: "Práctica en curso", detail: "Segmentos, horas y seguimiento" },
  { label: "Finalización", detail: "Confirmación de requisitos de cierre" },
  { label: "Cierre", detail: "Expediente cerrado como registro" },
] as const;

const STEP_BY_STATE: Record<string, number> = {
  PENDING_ACADEMIC_APPROVAL: 1,
  DOCUMENTATION_PENDING: 2,
  ACTIVE: 3,
  COMPLETED: 5,
  CLOSED: 6,
};

export function LifecycleSteps({ state }: { state: string }) {
  const current = STEP_BY_STATE[state];
  const interrupted = current === undefined;
  return (
    <div className="lifecycle">
      <ol className="lifecycle-steps" aria-label="Etapas del ciclo de vida">
        {LIFECYCLE_STEPS.map((step, index) => {
          const status = interrupted ? "pending" : index < current ? "done" : index === current ? "current" : "pending";
          const statusText = status === "done" ? "completada" : status === "current" ? "etapa actual" : "pendiente";
          return (
            <li key={step.label} className={`lifecycle-step is-${status}`} aria-current={status === "current" ? "step" : undefined}>
              <span className="lifecycle-marker" aria-hidden="true">
                {status === "done" ? <Icon name="check" /> : index + 1}
              </span>
              <span className="lifecycle-text">
                <span className="lifecycle-label">{step.label}</span>
                <span className="sr-only">: {statusText}</span>
              </span>
            </li>
          );
        })}
      </ol>
      {interrupted && (
        <p className="lifecycle-note">
          El ciclo se detuvo en estado «{formatDomainLabel(state)}». El historial anterior se conserva.
        </p>
      )}
    </div>
  );
}

export type Situation = { tone: "ready" | "blocked" | "info" | "done"; title: string; detail: string };

const SITUATION_ICON: Record<Situation["tone"], IconName> = {
  ready: "status-success",
  blocked: "status-warning",
  info: "status-info",
  done: "status-success",
};

export function SituationPanel({ situation }: { situation: Situation }) {
  return (
    <div className={`situation situation--${situation.tone}`}>
      <Icon name={SITUATION_ICON[situation.tone]} className="situation-icon" />
      <div>
        <p className="situation-title">{situation.title}</p>
        <p className="situation-detail">{situation.detail}</p>
      </div>
    </div>
  );
}

/** Accepted hours against the fixed MIN_HOURS threshold, when both are visible. */
export function HoursProgress({ dossier }: { dossier: PlacementDossier }) {
  const summary = dossier.hours_summary;
  const threshold = dossier.completion_requirements?.find((item) => item.kind === "MIN_HOURS")?.threshold ?? null;
  if (!summary) return null;
  const accepted = numeric(summary.accepted_total);
  const target = threshold === null ? null : numeric(threshold);
  const ratio = target && target > 0 ? Math.min(1, accepted / target) : null;
  return (
    <div className="hours-progress">
      <div className="hours-progress-figures">
        <span className="hours-progress-label">Horas aceptadas{summary.scope === "SEGMENT" ? " en tu segmento" : ""}</span>
        <span className="hours-progress-value">
          <strong>{formatHours(accepted)} h</strong>
          {target !== null && <span> de {formatHours(target)} h mínimas</span>}
        </span>
      </div>
      {ratio !== null && (
        <div className="hours-progress-track" aria-hidden="true">
          <span className="hours-progress-fill" style={{ width: `${Math.round(ratio * 100)}%` }} />
        </div>
      )}
      <span className="hours-progress-note">Reportadas: {formatHours(summary.reported_total)} h · solo las aceptadas cuentan para finalizar.</span>
    </div>
  );
}

type SectionLink = { id: string; label: string };

/**
 * Sticky in-page navigation built from the sections that actually rendered,
 * so roles without access to a section never see a dead link.
 */
export function DossierSectionNav({ containerRef, version }: { containerRef: RefObject<HTMLElement>; version: string }) {
  const [links, setLinks] = useState<SectionLink[]>([]);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const collect = () => {
      const sections = Array.from(container.querySelectorAll<HTMLElement>("[data-dossier-section]"))
        .filter((element) => element.childElementCount > 0);
      setLinks(sections.map((element) => ({ id: element.id, label: element.dataset.dossierSection ?? element.id })));
      return sections;
    };
    let sections = collect();
    // Child components fetch nothing on their own, but may render after layout; re-check once.
    const timer = window.setTimeout(() => { sections = collect(); observe(); }, 0);
    let observer: IntersectionObserver | null = null;
    function observe() {
      observer?.disconnect();
      if (typeof IntersectionObserver === "undefined") return;
      observer = new IntersectionObserver((entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      }, { rootMargin: "-140px 0px -55% 0px" });
      sections.forEach((section) => observer?.observe(section));
    }
    observe();
    return () => { window.clearTimeout(timer); observer?.disconnect(); };
  }, [containerRef, version]);

  if (links.length < 2) return null;

  function go(id: string) {
    const target = document.getElementById(id);
    if (!target) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    target.focus({ preventScroll: true });
    setActive(id);
  }

  return (
    <nav className="dossier-sections" aria-label="Secciones del expediente">
      <ul>
        {links.map((link) => (
          <li key={link.id}>
            <button type="button" className="dossier-section-link" aria-current={active === link.id ? "true" : undefined} onClick={() => go(link.id)}>
              {link.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
