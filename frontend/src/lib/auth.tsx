"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, apiLogin, apiLogout, apiMe, apiSignup } from "@/lib/api";
import type { AuthResponse, AuthUser } from "@/types/api";

const TOKEN_KEY = "zorvi_auth_token";

interface AuthContextValue {
  user: AuthUser | null;
  /** True until the saved session (if any) has been checked once on page load. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  /** Resolves with verificationRequired=true when the user must confirm their email before signing in. */
  signup: (
    name: string,
    email: string,
    password: string,
  ) => Promise<{ verificationRequired: boolean }>;
  logout: () => Promise<void>;
  /** The current session token, for calling protected backend routes. */
  getToken: () => string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage blocked: the user simply stays signed in for this tab only */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore the session on first load.
  useEffect(() => {
    const token = readToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiMe(token)
      .then(setUser)
      .catch((e) => {
        // Only discard the token if the server says it is invalid, not when the backend is merely offline.
        if (e instanceof ApiError && e.status === 401) writeToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const accept = useCallback((res: AuthResponse) => {
    writeToken(res.token);
    setUser(res.user);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => accept(await apiLogin({ email, password })),
    [accept],
  );

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      const res = await apiSignup({ name, email, password });
      if (res.token) accept({ token: res.token, user: res.user });
      return { verificationRequired: res.verification_required };
    },
    [accept],
  );

  const logout = useCallback(async () => {
    const token = readToken();
    writeToken(null);
    setUser(null);
    if (token) {
      try {
        await apiLogout(token);
      } catch {
        /* already signed out locally; the server session expires on its own */
      }
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, signup, logout, getToken: readToken }),
    [user, loading, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>.");
  return ctx;
}
