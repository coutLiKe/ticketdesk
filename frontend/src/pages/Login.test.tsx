import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import Login from "./Login";

function renderLogin() {
  render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Login page", () => {
  it("shows the server's error message when the login is rejected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Incorrect email or password" }), { status: 401 })),
    );
    renderLogin();

    await userEvent.type(screen.getByLabelText("Email"), "rita@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password");
  });

  it("links to the registration page", () => {
    renderLogin();

    expect(screen.getByRole("link", { name: "Register" })).toHaveAttribute("href", "/register");
  });
});
