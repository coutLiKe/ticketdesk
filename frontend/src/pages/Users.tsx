import { useState } from "react";
import { api, type Role } from "../api";
import { useAuth } from "../auth";
import { Badge, ErrorNote, formatDate } from "../components/ui";
import { errorMessage, useApi } from "../useApi";

const ROLES: Role[] = ["requester", "technician", "admin"];

export default function Users() {
  const { user: me } = useAuth();
  const { data, error, reload } = useApi(() => api.listUsers(), []);
  const [actionError, setActionError] = useState<string | null>(null);

  async function change(id: number, changes: { role?: Role; is_active?: boolean }) {
    setActionError(null);
    try {
      await api.updateUser(id, changes);
      reload();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  return (
    <>
      <h1>Users</h1>
      <ErrorNote message={error ?? actionError} />
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Joined</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {data?.map((u) => (
            <tr key={u.id} className={u.is_active ? "" : "inactive"}>
              <td>{u.full_name}</td>
              <td className="muted">{u.email}</td>
              <td>
                {u.id === me?.id ? (
                  <Badge kind="role" value={u.role} />
                ) : (
                  <select aria-label={`Role for ${u.full_name}`} value={u.role} onChange={(e) => change(u.id, { role: e.target.value as Role })}>
                    {ROLES.map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                )}
              </td>
              <td>{u.is_active ? "Active" : "Deactivated"}</td>
              <td className="muted">{formatDate(u.created_at)}</td>
              <td>
                {u.id !== me?.id && (
                  <button className="link" onClick={() => change(u.id, { is_active: !u.is_active })}>
                    {u.is_active ? "Deactivate" : "Reactivate"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
