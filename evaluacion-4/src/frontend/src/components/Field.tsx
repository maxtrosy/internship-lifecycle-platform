// Generic form field: visible label, optional hint and an error message that is
// associated with the control (aria-describedby + aria-invalid), so assistive
// technology announces why a value was rejected.
import { cloneElement, isValidElement, useState, type ReactElement, type ReactNode } from "react";

type ControlProps = {
  id?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean | "true" | "false";
};

export function Field({
  id,
  label,
  hint,
  error,
  className = "",
  children,
}: {
  id: string;
  label: ReactNode;
  hint?: ReactNode;
  error?: string | null;
  className?: string;
  children: ReactElement<ControlProps>;
}) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [children.props["aria-describedby"], hintId, errorId].filter(Boolean).join(" ") || undefined;
  const control = isValidElement(children)
    ? cloneElement(children, { id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })
    : children;
  return (
    <div className={`field${error ? " field--invalid" : ""}${className ? ` ${className}` : ""}`}>
      <label htmlFor={id}>{label}</label>
      {hint && <p className="field-hint" id={hintId}>{hint}</p>}
      {control}
      {error && <p className="field-error" id={errorId}>{error}</p>}
    </div>
  );
}

export type FieldErrors<K extends string> = Partial<Record<K, string>>;

/**
 * Small helper for per-field validation: keeps the error map and moves focus
 * to the first invalid control after a failed submit.
 */
export function useFieldErrors<K extends string>(idFor: (key: K) => string) {
  const [errors, setErrors] = useState<FieldErrors<K>>({});
  function report(next: FieldErrors<K>): boolean {
    setErrors(next);
    const first = Object.keys(next)[0] as K | undefined;
    if (first) window.setTimeout(() => document.getElementById(idFor(first))?.focus(), 0);
    return first === undefined;
  }
  function clear(key: K) {
    setErrors((current) => {
      if (!(key in current)) return current;
      const next = { ...current };
      delete next[key];
      return next;
    });
  }
  return { errors, report, clear, reset: () => setErrors({}) };
}
