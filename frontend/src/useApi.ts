import { useEffect, useState } from "react";
import { ApiError } from "./api";

interface Result<T> {
  key: string;
  data?: T;
  error?: string;
}

/**
 * Run an async request whenever `deps` change and expose {data, error, loading, reload}.
 * Keeps the previous data on screen while a reload is in flight, and ignores responses
 * that arrive after the component has moved on (the `cancelled` flag).
 */
export function useApi<T>(request: () => Promise<T>, deps: unknown[]) {
  const [version, setVersion] = useState(0);
  const [result, setResult] = useState<Result<T> | null>(null);
  const key = JSON.stringify(deps) + ":" + version;

  useEffect(() => {
    let cancelled = false;
    request()
      .then((data) => !cancelled && setResult({ key, data }))
      .catch((e: unknown) => {
        if (!cancelled) setResult({ key, error: e instanceof ApiError || e instanceof Error ? e.message : "Request failed" });
      });
    return () => {
      cancelled = true;
    };
    // `request` is a new closure every render; `key` already captures what really matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return {
    data: result?.data,
    error: result?.key === key ? result.error : undefined,
    loading: result?.key !== key,
    reload: () => setVersion((v) => v + 1),
  };
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}
