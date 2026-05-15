import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api.js';
import { clearClientAuth } from '../services/httpClient.js';

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
    const code = String(err?.code || '').toLowerCase();

    if (status === 401 || status === 400) {
      return 'Email ou mot de passe incorrect';
    }

    if (
      code === 'err_network' ||
      code === 'econnrefused' ||
      /failed to fetch|network error|network|econnrefused|connection refused|timeout/.test(detail)
    ) {
      return 'Impossible de joindre l’API. Vérifiez que le backend tourne (port 8000) et VITE_API_URL dans .env.development.local.';
    }

    if (/missing authentication token/.test(detail)) {
      return 'Session non établie après connexion. Réessayez ou videz le cache du navigateur.';
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
        clearClientAuth();
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
      const loginPayload = await authAPI.login(trimmedEmail, password);
      const access_token =
        loginPayload?.access_token ||
        loginPayload?.accessToken ||
        loginPayload?.token;

      if (!access_token) {
        throw new Error('Login response missing access_token');
      }

      // Ignore any legacy password-reset markers to avoid blocking access after login.
      clearPasswordResetFlags();
      devLog('[AUTH] Login successful, storing token');
      localStorage.setItem('token', access_token);
      localStorage.setItem('access_token', access_token);

      const meResponse = await authAPI.me();
      const normalizedUser = normalizeAndStoreUser(meResponse);
      setUser(normalizedUser);
      devLog('[AUTH] Login completed with role:', normalizedUser?.role, 'doctor_id:', normalizedUser?.doctor_id);
      return { success: true, role: normalizedUser?.role };
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error('[AUTH] Login failed:', err?.response?.status, err?.message);
      }
      clearClientAuth();
      setUser(null);
      const message = toUserFriendlyLoginMessage(err);
      setError(message);
      return { success: false, error: message };
    } finally {
      setActionLoading(false);
    }
  };

  const logout = () => {
    clearPasswordResetFlags();
    clearClientAuth();
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