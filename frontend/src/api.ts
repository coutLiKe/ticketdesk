// Typed client for the TicketDesk API. Every request goes through request(), which
// attaches the login token and turns error responses into ApiError.

export type Role = "requester" | "technician" | "admin";
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type Priority = "low" | "medium" | "high" | "urgent";
export type AssetType = "laptop" | "desktop" | "monitor" | "phone" | "other";
export type AssetStatus = "in_stock" | "assigned" | "retired";

export const STATUSES: TicketStatus[] = ["open", "in_progress", "resolved", "closed"];
export const PRIORITIES: Priority[] = ["low", "medium", "high", "urgent"];
export const ASSET_TYPES: AssetType[] = ["laptop", "desktop", "monitor", "phone", "other"];
export const ASSET_STATUSES: AssetStatus[] = ["in_stock", "assigned", "retired"];

export interface UserBrief {
  id: number;
  full_name: string;
  role: Role;
}
export interface User extends UserBrief {
  email: string;
  is_active: boolean;
  created_at: string;
}
export interface Ticket {
  id: number;
  title: string;
  description: string;
  status: TicketStatus;
  priority: Priority;
  requester: UserBrief;
  assignee: UserBrief | null;
  created_at: string;
  updated_at: string;
}
export interface Comment {
  id: number;
  ticket_id: number;
  author: UserBrief;
  body: string;
  is_internal: boolean;
  created_at: string;
}
export interface Asset {
  id: number;
  asset_tag: string;
  name: string;
  type: AssetType;
  serial_number: string | null;
  status: AssetStatus;
  assigned_user: UserBrief | null;
  created_at: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// Where the API lives. Locally "/api" is proxied by the dev server. For a deployment where the
// front end and API are on different domains, set VITE_API_URL at build time, e.g.
// "https://ticketdesk-api.onrender.com" (no trailing slash).
const API_BASE: string = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "/api";

const TOKEN_KEY = "ticketdesk_token";

// localStorage survives page reloads but is readable by any script on the page (XSS risk).
// An httpOnly cookie would be safer; for this project we accept the trade-off for simplicity.
export const tokenStore = {
  get: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string) => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable: the user just has to log in again next time */
    }
  },
  clear: () => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Called when the server says our token is no longer valid, so the app can log out.
let unauthorizedHandler: (() => void) | null = null;
export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

function describeError(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc: [...], msg: "..."}]
    return detail.map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return fallback;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const isLoginAttempt = path === "/auth/login";
    if (response.status === 401 && !isLoginAttempt) unauthorizedHandler?.();
    throw new ApiError(response.status, describeError(data, response.statusText));
  }
  return data as T;
}

function query(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "" && value !== false) search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("POST", "/auth/login", { email, password }),
  register: (email: string, full_name: string, password: string) =>
    request<User>("POST", "/auth/register", { email, full_name, password }),
  me: () => request<User>("GET", "/users/me"),

  listUsers: () => request<User[]>("GET", "/users"),
  userDirectory: () => request<UserBrief[]>("GET", "/users/directory"),
  assignableUsers: () => request<User[]>("GET", "/users/assignable"),
  updateUser: (id: number, changes: { role?: Role; is_active?: boolean }) =>
    request<User>("PATCH", `/users/${id}`, changes),

  listTickets: (p: {
    status?: string;
    priority?: string;
    q?: string;
    unassigned?: boolean;
    limit: number;
    offset: number;
  }) => request<Page<Ticket>>("GET", `/tickets${query(p)}`),
  getTicket: (id: number) => request<Ticket>("GET", `/tickets/${id}`),
  createTicket: (title: string, description: string) =>
    request<Ticket>("POST", "/tickets", { title, description }),
  setStatus: (id: number, status: TicketStatus) =>
    request<Ticket>("PUT", `/tickets/${id}/status`, { status }),
  setPriority: (id: number, priority: Priority) =>
    request<Ticket>("PUT", `/tickets/${id}/priority`, { priority }),
  setAssignee: (id: number, assignee_id: number | null) =>
    request<Ticket>("PUT", `/tickets/${id}/assignee`, { assignee_id }),

  listComments: (ticketId: number) => request<Comment[]>("GET", `/tickets/${ticketId}/comments`),
  addComment: (ticketId: number, body: string, is_internal: boolean) =>
    request<Comment>("POST", `/tickets/${ticketId}/comments`, { body, is_internal }),

  listAssets: (p: { type?: string; status?: string; q?: string; limit: number; offset: number }) =>
    request<Page<Asset>>("GET", `/assets${query(p)}`),
  getAsset: (id: number) => request<Asset>("GET", `/assets/${id}`),
  createAsset: (a: { asset_tag: string; name: string; type: AssetType; serial_number?: string }) =>
    request<Asset>("POST", "/assets", a),
  updateAsset: (id: number, changes: { name?: string; type?: AssetType; serial_number?: string }) =>
    request<Asset>("PATCH", `/assets/${id}`, changes),
  assignAsset: (id: number, user_id: number | null) =>
    request<Asset>("PUT", `/assets/${id}/assignee`, { user_id }),
  retireAsset: (id: number) => request<Asset>("POST", `/assets/${id}/retire`),
  assetTickets: (id: number) => request<Ticket[]>("GET", `/assets/${id}/tickets`),

  ticketAssets: (ticketId: number) => request<Asset[]>("GET", `/tickets/${ticketId}/assets`),
  linkAsset: (ticketId: number, assetId: number) =>
    request<Asset[]>("PUT", `/tickets/${ticketId}/assets/${assetId}`),
  unlinkAsset: (ticketId: number, assetId: number) =>
    request<void>("DELETE", `/tickets/${ticketId}/assets/${assetId}`),
};
