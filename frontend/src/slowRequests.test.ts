import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { trackSlow, useServerSlow } from "./slowRequests";

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((r) => (resolve = r));
  return { promise, resolve };
}

describe("trackSlow", () => {
  it("flags a request that takes longer than the threshold, then clears it", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useServerSlow());
    const request = deferred();
    const tracked = trackSlow(request.promise);

    act(() => vi.advanceTimersByTime(2900));
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(200));
    expect(result.current).toBe(true);

    await act(async () => {
      request.resolve();
      await tracked;
    });
    expect(result.current).toBe(false);
  });

  it("never flags a request that finishes quickly", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useServerSlow());
    const request = deferred();
    const tracked = trackSlow(request.promise);

    await act(async () => {
      request.resolve();
      await tracked;
    });
    act(() => vi.advanceTimersByTime(10_000));

    expect(result.current).toBe(false);
  });
});
