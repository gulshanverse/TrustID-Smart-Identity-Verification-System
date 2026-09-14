"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Role = "ADMIN" | "OFFICER" | "SUPERVISOR" | "AUDITOR";
export interface AuthUser { id: string; email: string; display_name: string; roles: Role[]; permissions: string[]; is_active: boolean; }
interface AuthContextValue { user: AuthUser | null; loading: boolean; error: string | null; signIn: (identifier: string, password: string) => Promise<boolean>; signOut: () => Promise<void>; refresh: () => Promise<void>; }

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AuthContext = createContext<AuthContextValue | null>(null);

async function readResponse(response: Response): Promise<{ user?: AuthUser; detail?: string }> {
  try { return await response.json() as { user?: AuthUser; detail?: string }; } catch { return {}; }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/me`, { credentials: "include", cache: "no-store" });
      if (!response.ok) { setUser(null); return; }
      const data = await response.json() as AuthUser;
      setUser(data);
    } catch { setUser(null); }
  };

  useEffect(() => { void refresh().finally(() => setLoading(false)); }, []);

  const signIn = async (identifier: string, password: string) => {
    setError(null); setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ identifier, password }) });
      const data = await readResponse(response);
      if (!response.ok || !data.user) { setError(data.detail ?? "Invalid credentials."); return false; }
      setUser(data.user); return true;
    } catch { setError("Unable to connect to the authentication service."); return false; } finally { setLoading(false); }
  };

  const signOut = async () => {
    try { await fetch(`${API_URL}/api/v1/auth/logout`, { method: "POST", credentials: "include" }); } finally { setUser(null); }
  };

  const value = useMemo(() => ({ user, loading, error, signIn, signOut, refresh }), [user, loading, error]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
