import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ASSET_STATUSES, ASSET_TYPES, type AssetType } from "../api";
import { isStaff, useAuth } from "../auth";
import { Badge, Card, ErrorNote, label, Pagination } from "../components/ui";
import { errorMessage, useApi } from "../useApi";

const LIMIT = 10;

export default function Assets() {
  const { user } = useAuth();
  const staff = isStaff(user);
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [showForm, setShowForm] = useState(false);

  const { data, error, reload } = useApi(() => api.listAssets({ type, status, q, limit: LIMIT, offset }), [type, status, q, offset]);

  return (
    <>
      <div className="page-head">
        <h1>{staff ? "Assets" : "My assets"}</h1>
        {staff && (
          <button className="primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "New asset"}
          </button>
        )}
      </div>

      {showForm && (
        <NewAssetForm
          onCreated={() => {
            setShowForm(false);
            reload();
          }}
        />
      )}

      <div className="filters">
        <form
          className="search"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setQ(search.trim());
            setOffset(0);
          }}
        >
          <input placeholder="Search tag, name or serial…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button>Search</button>
        </form>
        <select
          aria-label="Type"
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">Any type</option>
          {ASSET_TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select
          aria-label="Status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">Any status</option>
          {ASSET_STATUSES.map((s) => (
            <option key={s} value={s}>
              {label(s)}
            </option>
          ))}
        </select>
      </div>

      <ErrorNote message={error} />
      <table className="table">
        <thead>
          <tr>
            <th>Tag</th>
            <th>Name</th>
            <th>Type</th>
            <th>Status</th>
            <th>Assigned to</th>
            <th>Serial</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((a) => (
            <tr key={a.id}>
              <td>
                <Link to={`/assets/${a.id}`}>{a.asset_tag}</Link>
              </td>
              <td>{a.name}</td>
              <td>{a.type}</td>
              <td>
                <Badge kind="status" value={a.status} />
              </td>
              <td>{a.assigned_user?.full_name ?? <span className="muted">—</span>}</td>
              <td className="muted">{a.serial_number ?? "—"}</td>
            </tr>
          ))}
          {data?.items.length === 0 && (
            <tr>
              <td colSpan={6} className="muted center">
                No assets match.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {data && <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}

function NewAssetForm({ onCreated }: { onCreated: () => void }) {
  const [tag, setTag] = useState("");
  const [name, setName] = useState("");
  const [type, setType] = useState<AssetType>("laptop");
  const [serial, setSerial] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.createAsset({ asset_tag: tag, name, type, serial_number: serial || undefined });
      onCreated();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <Card title="New asset">
      <form className="form-row" onSubmit={submit}>
        <label>
          Asset tag
          <input value={tag} onChange={(e) => setTag(e.target.value)} required maxLength={50} />
        </label>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} />
        </label>
        <label>
          Type
          <select value={type} onChange={(e) => setType(e.target.value as AssetType)}>
            {ASSET_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <label>
          Serial (optional)
          <input value={serial} onChange={(e) => setSerial(e.target.value)} maxLength={100} />
        </label>
        <button className="primary">Create</button>
      </form>
      <ErrorNote message={error} />
    </Card>
  );
}
