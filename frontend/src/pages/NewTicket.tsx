import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Card, ErrorNote } from "../components/ui";
import { errorMessage } from "../useApi";

export default function NewTicket() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const ticket = await api.createTicket(title, description);
      navigate(`/tickets/${ticket.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <>
      <h1>New ticket</h1>
      <Card>
        <form className="stack" onSubmit={submit}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} autoFocus />
          </label>
          <label>
            What is going wrong?
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} required rows={6} maxLength={10000} />
          </label>
          <ErrorNote message={error} />
          <div>
            <button className="primary" disabled={busy}>
              {busy ? "Submitting…" : "Submit ticket"}
            </button>
          </div>
        </form>
      </Card>
    </>
  );
}
