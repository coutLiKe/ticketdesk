import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { tokenStore } from "./api";
import { AuthProvider } from "./auth";

function user(role: "requester" | "technician" | "admin") {
  return { id: 1, email: "me@example.com", full_name: "Test Person", role, is_active: true, created_at: "2026-01-01T00:00:00Z" };
}

/** Pretend to be the API: /users/me returns the given user, everything else is empty. */
function stubApi(role: "requester" | "technician" | "admin") {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
      if (input.endsWith("/users/me")) return json(user(role));
      if (input.includes("/tickets")) return json({ items: [], total: 0, limit: 10, offset: 0 });
      return json([]);
    }),
  );
}

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("App routing and role-aware UI", () => {
  it("sends a logged-out visitor to the login page", async () => {
    renderAt("/tickets");

    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows a requester only their own tickets and no Users link", async () => {
    tokenStore.set("token");
    stubApi("requester");
    renderAt("/tickets");

    expect(await screen.findByRole("heading", { name: "My tickets" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("redirects a requester away from the admin Users page", async () => {
    tokenStore.set("token");
    stubApi("requester");
    renderAt("/users");

    expect(await screen.findByRole("heading", { name: "My tickets" })).toBeInTheDocument();
  });

  it("shows technicians every ticket", async () => {
    tokenStore.set("token");
    stubApi("technician");
    renderAt("/tickets");

    expect(await screen.findByRole("heading", { name: "All tickets" })).toBeInTheDocument();
  });

  it("gives an admin the Users page", async () => {
    tokenStore.set("token");
    stubApi("admin");
    renderAt("/users");

    expect(await screen.findByRole("heading", { name: "Users" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
  });
});
