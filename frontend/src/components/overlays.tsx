// Shared interaction primitives (F5): confirmation dialog, side panel (drawer)
// and accessible tabs. Built on the native <dialog> element so focus trapping,
// Escape handling and background inertness come from the browser.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { Icon } from "./ui";

/* ------------------------------------------------------------------ */
/* Confirmation dialog                                                 */
/* ------------------------------------------------------------------ */

export type ConfirmOptions = {
  title: string;
  message?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** "danger" styles the confirm button as destructive and focuses Cancel first. */
  tone?: "default" | "danger";
};

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>;

const fallbackConfirm: ConfirmFn = async (options) =>
  window.confirm(typeof options.message === "string" ? `${options.title}\n\n${options.message}` : options.title);

const ConfirmContext = createContext<ConfirmFn>(fallbackConfirm);

/** Returns an async confirm(): resolves true when the person accepts. */
export function useConfirm(): ConfirmFn {
  return useContext(ConfirmContext);
}

type PendingConfirm = { options: ConfirmOptions; resolve: (value: boolean) => void; returnFocus: Element | null };

function openModal(dialog: HTMLDialogElement | null) {
  if (!dialog || dialog.open) return;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function closeModal(dialog: HTMLDialogElement | null) {
  if (!dialog || !dialog.open) return;
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

function restoreFocus(target: Element | null) {
  if (target instanceof HTMLElement && target.isConnected) target.focus();
}

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<PendingConfirm | null>(null);

  const confirm = useCallback<ConfirmFn>((options) => new Promise<boolean>((resolve) => {
    setPending({ options, resolve, returnFocus: document.activeElement });
  }), []);

  const settle = useCallback((value: boolean) => {
    setPending((current) => {
      if (current) {
        current.resolve(value);
        // Wait for the dialog to unmount before returning focus to the trigger.
        window.setTimeout(() => restoreFocus(current.returnFocus), 0);
      }
      return null;
    });
  }, []);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {pending && <ConfirmDialog options={pending.options} onSettle={settle} />}
    </ConfirmContext.Provider>
  );
}

function ConfirmDialog({ options, onSettle }: { options: ConfirmOptions; onSettle: (value: boolean) => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  const danger = options.tone === "danger";

  useEffect(() => {
    const dialog = ref.current;
    openModal(dialog);
    return () => closeModal(dialog);
  }, []);

  return (
    <dialog
      ref={ref}
      className="dialog confirm-dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby={`${id}-title`}
      aria-describedby={options.message ? `${id}-message` : undefined}
      onCancel={(event) => { event.preventDefault(); onSettle(false); }}
    >
      <div className="dialog-body">
        <h2 id={`${id}-title`} className="dialog-title">{options.title}</h2>
        {options.message && <div id={`${id}-message`} className="dialog-message">{options.message}</div>}
      </div>
      <div className="dialog-actions">
        <button className="btn secondary" type="button" autoFocus={danger} onClick={() => onSettle(false)}>
          {options.cancelLabel ?? "Cancelar"}
        </button>
        <button className={`btn${danger ? " danger" : ""} confirm-dialog-accept`} type="button" autoFocus={!danger} onClick={() => onSettle(true)}>
          {options.confirmLabel ?? "Confirmar"}
        </button>
      </div>
    </dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Drawer (side panel)                                                 */
/* ------------------------------------------------------------------ */

export function Drawer({
  open,
  title,
  description,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const returnFocus = useRef<Element | null>(null);
  const id = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (open) {
      returnFocus.current = document.activeElement;
      openModal(dialog);
      // Start on the first form field rather than the close button.
      const firstField = dialog?.querySelector<HTMLElement>(".drawer-content :is(input, select, textarea):not([disabled])");
      firstField?.focus();
    } else if (returnFocus.current) {
      // The dialog unmounts when closed; return focus to the control that opened it.
      closeModal(dialog);
      restoreFocus(returnFocus.current);
      returnFocus.current = null;
    }
  }, [open]);

  if (!open) return null;
  return (
    <dialog
      ref={ref}
      className="dialog drawer"
      aria-modal="true"
      aria-labelledby={`${id}-title`}
      aria-describedby={description ? `${id}-description` : undefined}
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <div className="drawer-panel">
        <header className="drawer-header">
          <div>
            <h2 id={`${id}-title`} className="dialog-title">{title}</h2>
            {description && <p id={`${id}-description`} className="drawer-description">{description}</p>}
          </div>
          <button className="btn ghost icon-only" type="button" aria-label="Cerrar panel" onClick={onClose}>
            <Icon name="close" />
          </button>
        </header>
        <div className="drawer-content">{children}</div>
        {footer && <footer className="drawer-footer">{footer}</footer>}
      </div>
    </dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Tabs (WAI-ARIA tabs pattern, automatic activation)                  */
/* ------------------------------------------------------------------ */

export type TabItem<T extends string> = { id: T; label: string; count?: number };

export function Tabs<T extends string>({
  label,
  items,
  value,
  onChange,
  idBase,
}: {
  label: string;
  items: TabItem<T>[];
  value: T;
  onChange: (next: T) => void;
  idBase: string;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = items.findIndex((item) => item.id === value);
    let next = -1;
    if (event.key === "ArrowRight") next = (index + 1) % items.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + items.length) % items.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = items.length - 1;
    if (next < 0) return;
    event.preventDefault();
    const target = items[next];
    onChange(target.id);
    refs.current[target.id]?.focus();
  }

  return (
    <div className="tabs" role="tablist" aria-label={label} onKeyDown={onKeyDown}>
      {items.map((item) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            ref={(node) => { refs.current[item.id] = node; }}
            type="button"
            role="tab"
            id={`${idBase}-tab-${item.id}`}
            aria-selected={selected}
            aria-controls={`${idBase}-panel-${item.id}`}
            tabIndex={selected ? 0 : -1}
            className="tab"
            onClick={() => onChange(item.id)}
          >
            {item.label}
            {item.count !== undefined && <span className="tab-count">{item.count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({ idBase, id, children, active = true }: { idBase: string; id: string; children: ReactNode; active?: boolean }) {
  // Without a tablist (single scope) the content renders as a plain region.
  if (!active) return <div className="tab-panel tab-panel--plain">{children}</div>;
  return (
    <div role="tabpanel" id={`${idBase}-panel-${id}`} aria-labelledby={`${idBase}-tab-${id}`} tabIndex={0} className="tab-panel">
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Disabled-action explanation                                         */
/* ------------------------------------------------------------------ */

/** Visible reason shown next to a disabled action, linked with aria-describedby. */
export function DisabledReason({ id, children }: { id: string; children: ReactNode }) {
  return (
    <p id={id} className="disabled-reason">
      <Icon name="status-info" className="disabled-reason-icon" />
      <span>{children}</span>
    </p>
  );
}
