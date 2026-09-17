/* ==========================================================================
   auth.jsx -- who is signed in, made available to every component.
   --------------------------------------------------------------------------
   The problem: the nav bar needs your name, the admin link needs to know
   whether you are an admin, the dashboard needs your profile. Passing that
   down through every component by hand gets painful quickly.

   React Context is the fix: one shared box at the top of the app that any
   component can read from with useAuth().
   ========================================================================== */

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, clearToken, getToken, setToken } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // `loading` starts true because on first paint we do not yet know whether
  // the saved token is still valid. Without it, the app would flash the
  // login screen for a moment before realising you are already signed in.
  const [loading, setLoading] = useState(true);

  /* --- on first load, turn any saved token back into a user ------------- */
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get('/api/auth/me')
      .then(setUser)
      .catch(() => clearToken())   // expired or invalid -> signed out
      .finally(() => setLoading(false));
  }, []);

  /* --- actions ---------------------------------------------------------- */
  const login = useCallback(async (email, password) => {
    const data = await api.post('/api/auth/login', { email, password }, { auth: false });
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const signup = useCallback(async (name, email, password) => {
    const data = await api.post('/api/auth/signup', { name, email, password }, { auth: false });
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  /** Called after editing the profile, so the nav bar updates immediately. */
  const refresh = useCallback(async () => {
    const fresh = await api.get('/api/auth/me');
    setUser(fresh);
    return fresh;
  }, []);

  const value = { user, loading, login, signup, logout, refresh, setUser };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Grab the auth box from anywhere: const { user, logout } = useAuth(); */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error('useAuth must be used inside <AuthProvider>.');
  }
  return ctx;
}
