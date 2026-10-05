import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, onUnauthorized, tokenStore } from "./api";

function respond(status: number, body?: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    status === 204 ? new Response(null, { status }) : new Response(JSON.stringify(body ?? {}), { status }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api client", () => {
  beforeEach(() => onUnauthorized(null));

  it("sends the saved token as a Bearer header", async () => {
    tokenStore.set("abc123");
    const fetchMock = respond(200, { id: 1 });

    await api.me();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/users/me");
    expect(init.headers.Authorization).toBe("Bearer abc123");
  });

  it("sends no Authorization header when logged out", async () => {
    const fetchMock = respond(200, {});

    await api.me();

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("turns an error response into an ApiError with the server's message", async () => {
    respond(404, { detail: "Ticket not found" });

    const error = await api.getTicket(99).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).message).toBe("Ticket not found");
  });

  it("formats validation errors as 'field: message'", async () => {
    respond(422, { detail: [{ loc: ["body", "title"], msg: "Field required" }] });

    await expect(api.createTicket("", "")).rejects.toThrow("title: Field required");
  });

  it("calls the unauthorized handler on a 401", async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    respond(401, { detail: "Not authenticated" });

    await api.me().catch(() => undefined);

    expect(handler).toHaveBeenCalledOnce();
  });

  it("does not log the user out when a login attempt itself fails with 401", async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    respond(401, { detail: "Incorrect email or password" });

    await expect(api.login("a@b.co", "wrong")).rejects.toThrow("Incorrect email or password");

    expect(handler).not.toHaveBeenCalled();
  });

  it("returns nothing for a 204 response", async () => {
    respond(204);

    await expect(api.unlinkAsset(1, 2)).resolves.toBeUndefined();
  });
});
