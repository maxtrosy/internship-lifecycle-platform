import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemeMode = "system" | "light" | "dark";
type ThemeContextValue = { mode: ThemeMode; setMode: (mode: ThemeMode) => void };
const STORAGE_KEY = "ilp-theme";
const ThemeContext = createContext<ThemeContextValue | null>(null);

function readMode(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch { /* Storage may be unavailable in restricted browsing contexts. */ }
  return "system";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(readMode);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const resolved = mode === "system" ? (media.matches ? "dark" : "light") : mode;
      document.documentElement.dataset.theme = resolved;
      document.documentElement.dataset.themeMode = mode;
      document.documentElement.style.colorScheme = resolved;
      document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')?.setAttribute(
        "content",
        resolved === "dark" ? "#111a18" : "#f2f6f3",
      );
    };
    const onSystemChange = () => { if (mode === "system") apply(); };
    apply();
    try { localStorage.setItem(STORAGE_KEY, mode); } catch { /* Keep the in-memory preference. */ }
    media.addEventListener?.("change", onSystemChange);
    return () => media.removeEventListener?.("change", onSystemChange);
  }, [mode]);

  const value = useMemo(() => ({ mode, setMode }), [mode]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside ThemeProvider");
  return context;
}

export function ThemeControl() {
  const { mode, setMode } = useTheme();
  return (
    <label className="theme-control">
      <span aria-hidden="true" className="theme-control-icon">◐</span>
      <span className="sr-only">Apariencia</span>
      <select aria-label="Apariencia" value={mode} onChange={(event) => setMode(event.target.value as ThemeMode)}>
        <option value="system">Sistema</option>
        <option value="light">Claro</option>
        <option value="dark">Oscuro</option>
      </select>
    </label>
  );
}
