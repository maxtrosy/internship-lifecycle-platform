// Shared pattern for user-triggered async actions: one busy key, one error and
// one success notice per page, with the same messages and reset behaviour.
import { useCallback, useState } from "react";

export function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error && cause.message ? cause.message : fallback;
}

export function useAsyncAction() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  /** Runs `action` under `key`; resolves true on success so callers can reset forms. */
  const run = useCallback(async (
    key: string,
    action: () => Promise<unknown>,
    success?: string,
    fallback = "No fue posible completar la acción.",
  ): Promise<boolean> => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      if (success) setNotice(success);
      return true;
    } catch (cause) {
      setError(errorMessage(cause, fallback));
      return false;
    } finally {
      setBusy(null);
    }
  }, []);

  const clear = useCallback(() => { setError(null); setNotice(null); }, []);

  return { busy, error, notice, run, clear, setError, setNotice };
}
