import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { isStaff, useAuth } from "../auth";
import { Badge, Card, ErrorNote, formatDate } from "../components/ui";
import { errorMessage, useApi } from "../useApi";

export default function AssetDetail() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const staff = isStaff(user);
  const asset = useApi(() => api.getAsset(id), [id]);
  const tickets = useApi(() => api.assetTickets(id), [id]);
  const users = useApi(() => (staff ? api.userDirectory() : Promise.resolve([])), [staff]);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      asset.reload();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  if (asset.error) return <ErrorNote message={asset.error} />;
  const a = asset.data;
  if (!a) return <p className="muted">Loading…</p>;
  const retired = a.status === "retired";

  return (
    <>
      <p>
        <Link to="/assets">← All assets</Link>
      </p>
      <div className="page-head">
        <h1>
          <span className="muted">{a.asset_tag}</span> {a.name}
        </h1>
        <Badge kind="status" value={a.status} />
      </div>
      <ErrorNote message={actionError} />

      <div className="grid">
        <Card title="Details">
          <dl>
            <dt>Type</dt>
            <dd>{a.type}</dd>
            <dt>Serial number</dt>
            <dd>{a.serial_number ?? "—"}</dd>
            <dt>Added</dt>
            <dd>{formatDate(a.created_at)}</dd>
            <dt>Assigned to</dt>
            <dd>
              {staff && !retired ? (
                <select
                  aria-label="Assign to"
                  value={a.assigned_user?.id ?? ""}
                  onChange={(e) => run(() => api.assignAsset(id, e.target.value ? Number(e.target.value) : null))}
                >
                  <option value="">In stock (nobody)</option>
                  {users.data?.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name}
                    </option>
                  ))}
                </select>
              ) : (
                (a.assigned_user?.full_name ?? "—")
              )}
            </dd>
          </dl>
          {staff && !retired && (
            <div className="actions">
              <button
                className="danger"
                onClick={() => window.confirm("Retire this asset? This cannot be undone.") && run(() => api.retireAsset(id))}
              >
                Retire asset
              </button>
            </div>
          )}
        </Card>

        <Card title="Related tickets">
          {tickets.data?.length === 0 && <p className="muted">No tickets linked.</p>}
          <ul className="plain">
            {tickets.data?.map((t) => (
              <li key={t.id} className="row">
                <Link to={`/tickets/${t.id}`}>
                  #{t.id} {t.title}
                </Link>
                <span className="spacer" />
                <Badge kind="status" value={t.status} />
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
