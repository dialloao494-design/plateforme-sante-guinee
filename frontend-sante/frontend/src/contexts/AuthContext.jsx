import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api.js';

const devLog = (...args) => {
  if (import.meta.env.DEV) {
    console.log(...args);
  }
};

const devWarn = (...args) => {
  if (import.meta.env.DEV) {
    console.warn(...args);
  }
};

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

  const clearPasswordResetFlags = () => {
    localStorage.removeItem('must_change_password');
    localStorage.removeItem('password_reset_required');
    localStorage.removeItem('force_password_change');
  };

  const toUserFriendlyLoginMessage = (err) => {
    const status = err?.response?.status;
    const detail = String(err?.response?.data?.detail || err?.response?.data?.message || err?.message || '').toLowerCase();

    if (status === 401 || status === 400) {
      return 'Email ou mot de passe incorrect';
    }

    if (/failed to fetch|network|timeout|token|missing authentication/.test(detail)) {
      return 'Une erreur est survenue, veuillez réessayer';
    }

    return 'Une erreur est survenue, veuillez réessayer';
  };

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
    clearPasswordResetFlags();

    const storedToken = localStorage.getItem('token') || localStorage.getItem('access_token');
    if (!storedToken) {
      devLog('[AUTH] No token in localStorage on app load');
      setAuthLoading(false);
      return;
    }

    devLog('[AUTH] Found token in localStorage, verifying with backend');

    if (!localStorage.getItem('token')) {
      localStorage.setItem('token', storedToken);
    }

    authAPI
      .me()
      .then((data) => {
        devLog('[AUTH] Successfully verified user:', data?.email, data?.role);
        const normalizedUser = normalizeAndStoreUser(data);
        setUser(normalizedUser);
      })
      .catch((err) => {
        devWarn('[AUTH] Failed to verify token:', err?.response?.status, err?.message);
        localStorage.removeItem('token');
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
      const trimmedEmail = String(email || '').trim();
      devLog('[AUTH] Logging in:', trimmedEmail);
      const response = await authAPI.login(trimmedEmail, password);

      // Ignore any legacy password-reset markers to avoid blocking access after login.
      clearPasswordResetFlags();
      const { access_token, user_id, user_role, role, email: userEmail } = response;
      const resolvedRole = user_role || role;
      devLog('[AUTH] Login successful, storing token');
      localStorage.setItem('token', access_token);
      localStorage.setItem('access_token', access_token);
      if (user_id) {
        localStorage.setItem('user_id', String(user_id));
      }
      if (resolvedRole && userEmail) {
        localStorage.setItem('user_role', resolvedRole);
        const normalizedUser = normalizeAndStoreUser({ id: user_id, user_role: resolvedRole, email: userEmail });
        setUser(normalizedUser);
        devLog('[AUTH] Login completed with role:', resolvedRole);
        return { success: true, role: normalizedUser?.role };
      } else {
        devLog('[AUTH] Fetching user via /auth/me');
        const meResponse = await authAPI.me();
        const normalizedUser = normalizeAndStoreUser(meResponse);
        setUser(normalizedUser);
        devLog('[AUTH] User verified, role:', meResponse?.role);
        return { success: true, role: normalizedUser?.role };
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('[AUTH] Login failed:', err?.response?.status, err?.message);
      }
      const message = toUserFriendlyLoginMessage(err);
      setError(message);
      return { success: false, error: message };
    } finally {
      setActionLoading(false);
    }
  };

  const logout = () => {
    clearPasswordResetFlags();
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_id');
    setUser(null);
    setError(null);
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