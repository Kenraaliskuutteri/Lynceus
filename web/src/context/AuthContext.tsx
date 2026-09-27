import React, { createContext, useContext, useEffect, useState } from 'react';
import { normalizeHost } from '../utils/host';
import { login as apiLogin, logoutSession, refreshSession, getSession, setSessionExpiredHandler, Role } from '../services/api';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  host: string;
  username: string | null;
  role: Role | null;
  login: (host: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function loadStoredHost(): string {
  const raw = localStorage.getItem('lynceus_host');
  if (!raw) return '';
  try {
    return normalizeHost(raw);
  } catch {
    localStorage.removeItem('lynceus_host');
    return '';
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [host, setHost] = useState<string>(loadStoredHost());
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setIsAuthenticated(false);
      setUsername(null);
      setRole(null);
    });
    return () => setSessionExpiredHandler(null);
  }, []);

  useEffect(() => {
    if (!host) {
      setIsLoading(false);
      return;
    }

    refreshSession(host)
      .then((ok) => {
        if (ok) {
          const session = getSession();
          setUsername(session.username);
          setRole(session.role);
          setIsAuthenticated(true);
        }
      })
      .finally(() => setIsLoading(false));
  }, [host]);

  const login = async (newHost: string, uname: string, password: string) => {
    const normalized = normalizeHost(newHost);
    const result = await apiLogin(normalized, uname, password);
    localStorage.setItem('lynceus_host', normalized);
    setHost(normalized);
    setUsername(result.username);
    setRole(result.role);
    setIsAuthenticated(true);
  };

  const logout = async () => {
    await logoutSession();
    setIsAuthenticated(false);
    setUsername(null);
    setRole(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, host, username, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}