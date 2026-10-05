import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, PRIORITIES, type Priority, type Ticket, type TicketStatus } from "../api";
import { isStaff, useAuth } from "../auth";
import { Badge, Card, ErrorNote, formatDate } from "../components/ui";
import { errorMessage, useApi } from "../useApi";

// Mirrors the server's state machine so we only offer moves the API will accept.
// The server re-checks every move; this is for convenience, not security.
function nextActions(status: TicketStatus, staff: boolean): { to: TicketStatus; text: string }[] {
  switch (status) {
    case "open":
      return staff ? [{ to: "in_progress", text: "Start work" }] : [];
    case "in_progress":
      return staff ? [{ to: "resolved", text: "Mark resolved" }] : [];
    case "resolved":
      return [
        { to: "closed", text: "Close ticket" },
        { to: "in_progress", text: "Reopen" },
      ];
    default:
      return [];
  }
}

export default function TicketDetail() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const staff = isStaff(user);
  const ticket = useApi(() => api.getTicket(id), [id]);
  const comments = useApi(() => api.listComments(id), [id]);
  const linked = useApi(() => api.ticketAssets(id), [id]);
  const assignable = useApi(() => (staff ? api.assignableUsers() : Promise.resolve([])), [staff]);
  const allAssets = useApi(() => (staff ? api.listAssets({ limit: 100, offset: 0 }) : Promise.resolve(null)), [staff]);

  const [actionError, setActionError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [internal, setInternal] = useState(false);
  const [linkId, setLinkId] = useState("");

  async function run(action: () => Promise<unknown>, after: () => void = ticket.reload) {
    setActionError(null);
    try {
      await action();
      after();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  async function postComment(e: FormEvent) {
    e.preventDefault();
    await run(async () => {
      await api.addComment(id, body, internal);
      setBody("");
      setInternal(false);
    }, comments.reload);
  }

  if (ticket.error) return <ErrorNote message={ticket.error} />;
  const t: Ticket | undefined = ticket.data;
  if (!t) return <p className="muted">Loading…</p>;

  const closed = t.status === "closed";
  const linkedIds = new Set(linked.data?.map((a) => a.id));
  const linkable = allAssets.data?.items.filter((a) => !linkedIds.has(a.id)) ?? [];

  return (
    <>
      <p>
        <Link to="/tickets">← All tickets</Link>
      </p>
      <div className="page-head">
        <h1>
          <span className="muted">#{t.id}</span> {t.title}
        </h1>
        <Badge kind="status" value={t.status} />
      </div>
      <ErrorNote message={actionError} />

      <div className="grid">
        <div className="stack">
          <Card title="Description">
            <p className="prewrap">{t.description}</p>
            <p className="muted small">
              Opened by {t.requester.full_name} on {formatDate(t.created_at)}
            </p>
          </Card>

          <Card title="Conversation">
            {comments.data?.length === 0 && <p className="muted">No comments yet.</p>}
            <ul className="comments">
              {comments.data?.map((c) => (
                <li key={c.id} className={c.is_internal ? "internal" : ""}>
                  <div className="comment-head">
                    <strong>{c.author.full_name}</strong> <Badge kind="role" value={c.author.role} />
                    {c.is_internal && <span className="badge internal-tag">internal note</span>}
                    <span className="muted small">{formatDate(c.created_at)}</span>
                  </div>
                  <p className="prewrap">{c.body}</p>
                </li>
              ))}
            </ul>
            {closed ? (
              <p className="muted">This ticket is closed, so new comments are disabled.</p>
            ) : (
              <form className="stack" onSubmit={postComment}>
                <textarea
                  placeholder="Write a comment…"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  required
                  rows={3}
                  maxLength={5000}
                />
                <div className="row">
                  {staff && (
                    <label className="inline">
                      <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
                      Internal note (hidden from requester)
                    </label>
                  )}
                  <span className="spacer" />
                  <button className="primary">Add comment</button>
                </div>
              </form>
            )}
          </Card>
        </div>

        <div className="stack">
          <Card title="Details">
            <dl>
              <dt>Priority</dt>
              <dd>
                {staff && !closed ? (
                  <select
                    value={t.priority}
                    onChange={(e) => run(() => api.setPriority(id, e.target.value as Priority))}
                    aria-label="Priority"
                  >
                    {PRIORITIES.map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                ) : (
                  <Badge kind="priority" value={t.priority} />
                )}
              </dd>
              <dt>Assignee</dt>
              <dd>
                {staff && !closed ? (
                  <select
                    value={t.assignee?.id ?? ""}
                    onChange={(e) => run(() => api.setAssignee(id, e.target.value ? Number(e.target.value) : null))}
                    aria-label="Assignee"
                  >
                    <option value="">Unassigned</option>
                    {assignable.data?.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name}
                      </option>
                    ))}
                  </select>
                ) : (
                  (t.assignee?.full_name ?? <span className="muted">Unassigned</span>)
                )}
              </dd>
              <dt>Requester</dt>
              <dd>{t.requester.full_name}</dd>
              <dt>Last updated</dt>
              <dd>{formatDate(t.updated_at)}</dd>
            </dl>
            <div className="actions">
              {nextActions(t.status, staff).map((a) => (
                <button key={a.to} className={a.to === "closed" ? "" : "primary"} onClick={() => run(() => api.setStatus(id, a.to))}>
                  {a.text}
                </button>
              ))}
            </div>
          </Card>

          <Card title="Linked assets">
            {linked.data?.length === 0 && <p className="muted">None linked.</p>}
            <ul className="plain">
              {linked.data?.map((a) => (
                <li key={a.id} className="row">
                  <Link to={`/assets/${a.id}`}>
                    {a.asset_tag} · {a.name}
                  </Link>
                  <span className="spacer" />
                  {staff && !closed && (
                    <button className="link danger" onClick={() => run(() => api.unlinkAsset(id, a.id), linked.reload)}>
                      Unlink
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {staff && !closed && (
              <div className="row">
                <select value={linkId} onChange={(e) => setLinkId(e.target.value)} aria-label="Asset to link">
                  <option value="">Link an asset…</option>
                  {linkable.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.asset_tag} · {a.name}
                    </option>
                  ))}
                </select>
                <button
                  disabled={!linkId}
                  onClick={() =>
                    run(async () => {
                      await api.linkAsset(id, Number(linkId));
                      setLinkId("");
                    }, linked.reload)
                  }
                >
                  Link
                </button>
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
