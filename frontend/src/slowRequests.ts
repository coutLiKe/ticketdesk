import { useSyncExternalStore } from "react";

// The free API host sleeps when idle and can take about a minute to wake. If a request is
// still waiting after a few seconds we say so, so the page doesn't just look broken.
const SLOW_AFTER_MS = 3000;

let slowCount = 0;
const listeners = new Set<() => void>();

function change(delta: number) {
  slowCount += delta;
  listeners.forEach((listener) => listener());
}

export async function trackSlow<T>(work: Promise<T>, afterMs = SLOW_AFTER_MS): Promise<T> {
  let flagged = false;
  const timer = setTimeout(() => {
    flagged = true;
    change(1);
  }, afterMs);
  try {
    return await work;
  } finally {
    clearTimeout(timer);
    if (flagged) change(-1);
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** True while at least one request has been waiting longer than a few seconds. */
export function useServerSlow(): boolean {
  return useSyncExternalStore(subscribe, () => slowCount > 0);
}
