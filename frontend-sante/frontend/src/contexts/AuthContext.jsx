import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api.js';

/* eslint-disable react-refresh/only-export-components */
const AuthContext = createContext();

export const useAuth = () => {
  return useContext(AuthContext);
};
/* eslint-enable react-refresh/only-export-components */

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);

  const normalizeAndStoreUser = (data) => {
    if (!data) {
      return null;
    }

    const normalizedUser = {
      ...data,
      role: data.role || data.user_role,
    };

    if (normalizedUser.id) {
      localStorage.setItem('user_id', String(normalizedUser.id));
    }
    if (normalizedUser.role) {
      localStorage.setItem('user_role', normalizedUser.role);
    }

    return normalizedUser;
  };

  useEffect(() => {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      setAuthLoading(false);
      return;
    }

    authAPI
      .me()
      .then((response) => {
        const normalizedUser = normalizeAndStoreUser(response.data);
        console.log('[AuthContext] /auth/me user:', normalizedUser);
        setUser(normalizedUser);
      })
      .catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_role');
        localStorage.removeItem('user_id');
        setUser(null);
      })
      .finally(() => setAuthLoading(false));
  }, []);

  const login = async (email, password) => {
    setActionLoading(true);
    setError(null);

    try {
      const response = await authAPI.login(email, password);
      const { access_token, user_id, user_role, role, email: userEmail } = response.data;
      const resolvedRole = user_role || role;
      localStorage.setItem('access_token', access_token);
      if (user_id) {
        localStorage.setItem('user_id', String(user_id));
      }
      if (resolvedRole && userEmail) {
        localStorage.setItem('user_role', resolvedRole);
        const normalizedUser = normalizeAndStoreUser({ id: user_id, user_role: resolvedRole, email: userEmail });
        console.log('[AuthContext] login user:', normalizedUser);
        setUser(normalizedUser);
        return { success: true, role: normalizedUser?.role };
      } else {
        const meResponse = await authAPI.me();
        const normalizedUser = normalizeAndStoreUser(meResponse.data);
        console.log('[AuthContext] login fallback /auth/me user:', normalizedUser);
        setUser(normalizedUser);
        return { success: true, role: normalizedUser?.role };
      }
    } catch (err) {
      const message =
        err?.response?.data?.detail || err?.response?.data?.message || 'Impossible de se connecter';
      setError(message);
      return { success: false, error: message };
    } finally {
      setActionLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_id');
    setUser(null);
    setError(null);
    console.log('[AuthContext] logout: cleared user state and localStorage');
  };

  const value = {
    user,
    loading: actionLoading,
    authLoading,
    error,
    login,
    logout,
    isAuthenticated: Boolean(user),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};