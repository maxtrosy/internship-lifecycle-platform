const isLoopbackHost = typeof window !== "undefined"
  && ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);

export const demoLoginPassword = import.meta.env.VITE_DEMO_LOGIN_PASSWORD
  || (import.meta.env.DEV ? "Demo-Only-2026!" : "");

export function isDemoLoginEnabled(): boolean {
  const enabled = import.meta.env.DEV || import.meta.env.VITE_DEMO_LOGIN_ENABLED === "true";
  return enabled && isLoopbackHost && Boolean(demoLoginPassword);
}
