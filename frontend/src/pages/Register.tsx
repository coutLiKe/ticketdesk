import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { ErrorNote } from "../components/ui";
import { errorMessage } from "../useApi";

export default function Register() {
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(email, fullName, password);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth" onSubmit={submit}>
        <h1>Create account</h1>
        <p className="muted">New accounts are requesters. An admin can change your role.</p>
        <label>
          Full name
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} required maxLength={120} autoFocus />
        </label>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password (8+ characters)
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </label>
        <ErrorNote message={error} />
        <button className="primary" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
        <p className="muted small">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
