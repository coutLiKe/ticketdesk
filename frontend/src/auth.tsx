import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, onUnauthorized, tokenStore, type User } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean; // true while we check a saved token on first load
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => tokenStore.get() !== null);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  // On first load, if a token is saved, ask the server who it belongs to.
  useEffect(() => {
    if (tokenStore.get() === null) return;
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  // Any 401 from the API (expired token, deactivated account) logs the user out.
  useEffect(() => {
    onUnauthorized(logout);
    return () => onUnauthorized(null);
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.login(email, password);
    tokenStore.set(access_token);
    setUser(await api.me());
  }, []);

  const register = useCallback(
    async (email: string, fullName: string, password: string) => {
      await api.register(email, fullName, password);
      await login(email, password);
    },
    [login],
  );

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export const isStaff = (user: User | null) => user?.role === "technician" || user?.role === "admin";
