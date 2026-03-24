"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";

interface AuthContextType {
  user: { email: string; role: string } | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = user !== null;

  // Hydration: validate stored token on mount
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }

    fetch("/api/auth/me", {
      headers: { Authorization: "Bearer " + token },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Invalid token");
        return res.json();
      })
      .then((data) => {
        setUser({ email: data.email, role: data.role });
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setUser(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(
        body?.detail || "Erro no servidor. Tente novamente em alguns instantes."
      );
    }

    const { access_token, refresh_token } = await res.json();
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);

    // Fetch user data with the new token
    const meRes = await fetch("/api/auth/me", {
      headers: { Authorization: "Bearer " + access_token },
    });
    if (meRes.ok) {
      const data = await meRes.json();
      setUser({ email: data.email, role: data.role });
    }

    window.location.href = "/dashboard";
  }, []);

  const register = useCallback(
    async (email: string, password: string) => {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          body?.detail || "Erro no servidor. Tente novamente em alguns instantes."
        );
      }

      // Auto-login after successful registration (per D-10)
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(async () => {
    const refresh_token = localStorage.getItem("refresh_token");

    // Best-effort server-side invalidation
    if (refresh_token) {
      fetch("/api/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token }),
      }).catch(() => {});
    }

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);

    window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
