import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { requestJson, setAccessToken, setUnauthorizedHandler } from "@/lib/api";

export type StaffRole = "field" | "estimator" | "manager";
export type StaffUser = { id: number; name: string; role: StaffRole };
type Auth = {
  user: StaffUser | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
};
const AuthContext = createContext<Auth | null>(null);
let client: SupabaseClient | undefined;
function supabase() {
  const url = process.env.EXPO_PUBLIC_SUPABASE_URL?.trim();
  const key = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY?.trim();
  if (!url || !key) throw new Error("Sign-in is not configured. Ask the team to set the app's public Supabase settings.");
  if (key.startsWith("sb_secret_")) throw new Error("A public Supabase key is required.");
  return client ??= createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false } });
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<StaffUser | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const generation = useRef(0);
  const pending = useRef(false);
  function signOut() {
    generation.current++;
    setAccessToken(null);
    setUser(null);
    if (timer.current) clearTimeout(timer.current);
    // Discard the SDK instance too: access/refresh tokens live only in memory.
    client = undefined;
  }
  useEffect(() => {
    setUnauthorizedHandler(signOut);
    return () => {
      generation.current = -1;
      setAccessToken(null);
      setUnauthorizedHandler(null);
      if (timer.current) clearTimeout(timer.current);
      client = undefined;
    };
  }, []);

  async function signIn(email: string, password: string) {
    if (pending.current) return;
    pending.current = true;
    const attempt = ++generation.current;
    try {
      const { data, error } = await supabase().auth.signInWithPassword({ email: email.trim(), password });
      if (error || !data.session) throw new Error("Sign-in failed. Check your email and password and try again.");
      const session = data.session;
      // The API verifies the token and owns the role. Never trust client metadata.
      const caller = await requestJson<StaffUser>("/api/v1/me", { headers: { Authorization: "Bearer " + session.access_token } });
      if (!Number.isInteger(caller.id) || typeof caller.name !== "string" || !["field", "estimator", "manager"].includes(caller.role)) {
        throw new Error("This account does not have a staff role. Ask the team to link your account.");
      }
      if (attempt !== generation.current) return;
      const remaining = (session.expires_at ?? 0) * 1000 - Date.now();
      if (!Number.isFinite(remaining) || remaining <= 0) throw new Error("Your session expired. Sign in again.");
      setAccessToken(session.access_token);
      setUser(caller);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(signOut, Math.min(remaining, 2_147_483_647));
    } finally {
      pending.current = false;
    }
  }
  return <AuthContext.Provider value={{ user, signIn, signOut }}>{children}</AuthContext.Provider>;
}
export function useSession() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("SessionProvider is required");
  return value;
}
