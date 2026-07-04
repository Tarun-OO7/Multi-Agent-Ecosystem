import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authApi } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    try {
      const res = await authApi.me();
      setUser(res.data);
    } catch {
      setUser(null);
      localStorage.removeItem("sentinel_access");
      localStorage.removeItem("sentinel_refresh");
    }
  }, []);

  useEffect(() => {
    (async () => {
      const t = localStorage.getItem("sentinel_access");
      if (t) await loadMe();
      setLoading(false);
    })();
  }, [loadMe]);

  const login = async (email, password) => {
    const res = await authApi.login(email, password);
    localStorage.setItem("sentinel_access", res.data.access_token);
    localStorage.setItem("sentinel_refresh", res.data.refresh_token);
    setUser(res.data.user);
    return res.data.user;
  };

  const logout = () => {
    localStorage.removeItem("sentinel_access");
    localStorage.removeItem("sentinel_refresh");
    setUser(null);
  };

  const register = async (payload) => {
    const res = await authApi.register(payload);
    return res.data;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register, reload: loadMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
