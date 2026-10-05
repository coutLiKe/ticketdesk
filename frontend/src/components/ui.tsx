import type { ReactNode } from "react";
import { useServerSlow } from "../slowRequests";

export function label(value: string): string {
  return value.replace("_", " ");
}

export function Badge({ kind, value }: { kind: "status" | "priority" | "role"; value: string }) {
  return <span className={`badge ${kind} ${value}`}>{label(value)}</span>;
}

export function ErrorNote({ message }: { message?: string | null }) {
  return message ? <p className="error" role="alert">{message}</p> : null;
}

export function Pagination(props: { total: number; limit: number; offset: number; onChange: (offset: number) => void }) {
  const { total, limit, offset, onChange } = props;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  return (
    <div className="pagination">
      <button disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
        Previous
      </button>
      <span className="muted">
        Page {page} of {pages} · {total} total
      </span>
      <button disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
        Next
      </button>
    </div>
  );
}

export function Card({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <div className="card-head">
          <h2>{title}</h2>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** Shown when the API is slow to answer, which on the free host usually means it is waking up. */
export function WakingNotice() {
  const slow = useServerSlow();
  if (!slow) return null;
  return (
    <p className="notice" role="status">
      The server is waking up (free hosting sleeps when idle). This can take up to a minute.
    </p>
  );
}
