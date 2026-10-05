import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { ErrorNote, WakingNotice } from "../components/ui";
import { errorMessage } from "../useApi";

// The hosted demo sets VITE_DEMO_LOGINS=true to show one-click buttons that fill in the form.
const SHOW_DEMO_LOGINS = import.meta.env.VITE_DEMO_LOGINS === "true";
const DEMO_PASSWORD = "demo1234";
const DEMO_ACCOUNTS = [
  { label: "Requester", email: "rita@ticketdesk.dev" },
  { label: "Technician", email: "tom@ticketdesk.dev" },
  { label: "Admin", email: "admin@ticketdesk.dev" },
];

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function fill(demoEmail: string) {
    setEmail(demoEmail);
    setPassword(DEMO_PASSWORD);
    setError(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth" onSubmit={submit}>
        <h1>TicketDesk</h1>
        <p className="muted">Sign in to continue</p>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <WakingNotice />
        <ErrorNote message={error} />
        <button className="primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="muted small">
          No account? <Link to="/register">Register</Link>
        </p>
        {SHOW_DEMO_LOGINS ? (
          <div className="demo">
            <p className="muted small">Demo accounts (made-up data, password demo1234):</p>
            <div className="row">
              {DEMO_ACCOUNTS.map((a) => (
                <button type="button" key={a.email} onClick={() => fill(a.email)}>
                  {a.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <p className="muted small demo">Demo: admin@ticketdesk.dev, tom@ticketdesk.dev or rita@ticketdesk.dev, password demo1234</p>
        )}
      </form>
    </div>
  );
}
