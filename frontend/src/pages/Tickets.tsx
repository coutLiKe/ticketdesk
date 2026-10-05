import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, PRIORITIES, STATUSES } from "../api";
import { isStaff, useAuth } from "../auth";
import { Badge, ErrorNote, formatDate, Pagination } from "../components/ui";
import { useApi } from "../useApi";

const LIMIT = 10;

export default function Tickets() {
  const { user } = useAuth();
  const staff = isStaff(user);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [unassigned, setUnassigned] = useState(false);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState(""); // the search actually applied (set on submit)
  const [offset, setOffset] = useState(0);

  const { data, error, loading } = useApi(
    () => api.listTickets({ status, priority, q, unassigned, limit: LIMIT, offset }),
    [status, priority, q, unassigned, offset],
  );

  // Changing any filter returns to the first page.
  const filter = <T,>(set: (v: T) => void) => (v: T) => {
    set(v);
    setOffset(0);
  };
  function submitSearch(e: FormEvent) {
    e.preventDefault();
    filter(setQ)(search.trim());
  }

  return (
    <>
      <div className="page-head">
        <h1>{staff ? "All tickets" : "My tickets"}</h1>
        <Link className="button primary" to="/tickets/new">
          New ticket
        </Link>
      </div>

      <div className="filters">
        <form onSubmit={submitSearch} className="search">
          <input placeholder="Search title or description…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button>Search</button>
        </form>
        <select aria-label="Status" value={status} onChange={(e) => filter(setStatus)(e.target.value)}>
          <option value="">Any status</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
        <select aria-label="Priority" value={priority} onChange={(e) => filter(setPriority)(e.target.value)}>
          <option value="">Any priority</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        {staff && (
          <label className="inline">
            <input type="checkbox" checked={unassigned} onChange={(e) => filter(setUnassigned)(e.target.checked)} />
            Unassigned only
          </label>
        )}
      </div>

      <ErrorNote message={error} />
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Title</th>
            <th>Status</th>
            <th>Priority</th>
            {staff && <th>Requester</th>}
            <th>Assignee</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((t) => (
            <tr key={t.id}>
              <td className="muted">{t.id}</td>
              <td>
                <Link to={`/tickets/${t.id}`}>{t.title}</Link>
              </td>
              <td>
                <Badge kind="status" value={t.status} />
              </td>
              <td>
                <Badge kind="priority" value={t.priority} />
              </td>
              {staff && <td>{t.requester.full_name}</td>}
              <td>{t.assignee?.full_name ?? <span className="muted">Unassigned</span>}</td>
              <td className="muted">{formatDate(t.created_at)}</td>
            </tr>
          ))}
          {data?.items.length === 0 && (
            <tr>
              <td colSpan={7} className="muted center">
                No tickets match.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {loading && !data && <p className="muted">Loading…</p>}
      {data && <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}
