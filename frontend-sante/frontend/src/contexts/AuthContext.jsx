import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api.js';
import { clearClientAuth } from '../services/httpClient.js';
import { touchSessionActivity } from '../utils/authStorage.js';
import { useSessionTimeout } from '../hooks/useSessionTimeout.js';
import SessionTimeoutModal from '../components/SessionTimeoutModal.jsx';

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
      /failed to fetch|network error|network|econnrefused|connection refused|timeout|405 not allowed|nginx/.test(detail) ||
      (!status && /login failed|network error/i.test(String(err?.message || '')))
    ) {
      return 'Impossible de joindre l’API. Vérifiez que le backend tourne sur http://127.0.0.1:8000.';
    }

    if (/missing authentication token/.test(detail)) {
      return 'Session non établie après connexion. Réessayez ou videz le cache du navigateur.';
    }

    return 'Une erreur est survenue, veuillez réessayer';
  };

  const normalizeAndStoreUser = useCallback((data) => {
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
    touchSessionActivity();

    return normalizedUser;
  }, []);

  const logout = useCallback(() => {
    clearPasswordResetFlags();
    clearClientAuth();
    setUser(null);
    setError(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const data = await authAPI.me();
    const normalizedUser = normalizeAndStoreUser(data);
    setUser(normalizedUser);
    return normalizedUser;
  }, [normalizeAndStoreUser]);

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
  }, [normalizeAndStoreUser]);

  const applyLoginToken = useCallback(
    async (loginPayload) => {
      const access_token =
        loginPayload?.access_token ||
        loginPayload?.accessToken ||
        loginPayload?.token;

      if (!access_token) {
        throw new Error('Login response missing access_token');
      }

      clearPasswordResetFlags();
      localStorage.setItem('token', access_token);
      localStorage.setItem('access_token', access_token);

      const meResponse = await authAPI.me();
      const normalizedUser = normalizeAndStoreUser(meResponse);
      setUser(normalizedUser);
      return normalizedUser;
    },
    [normalizeAndStoreUser],
  );

  const loginWithToken = async (loginPayload) => {
    setActionLoading(true);
    setError(null);
    try {
      const normalizedUser = await applyLoginToken(loginPayload);
      return { success: true, role: normalizedUser?.role };
    } catch (err) {
      clearClientAuth();
      setUser(null);
      const message = toUserFriendlyLoginMessage(err);
      setError(message);
      return { success: false, error: message };
    } finally {
      setActionLoading(false);
    }
  };

  const login = async (email, password) => {
    setActionLoading(true);
    setError(null);

    try {
      const trimmedEmail = String(email || '').trim();
      devLog('[AUTH] Logging in:', trimmedEmail);
      const loginPayload = await authAPI.login(trimmedEmail, password);
      devLog('[AUTH] Login successful, storing token');
      const normalizedUser = await applyLoginToken(loginPayload);
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

  const changePassword = async (currentPassword, newPassword) => {
    setActionLoading(true);
    setError(null);
    try {
      await authAPI.changePassword(currentPassword, newPassword);
      return { success: true };
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        'Impossible de modifier le mot de passe. Vérifiez le mot de passe actuel.';
      setError(message);
      return { success: false, error: message };
    } finally {
      setActionLoading(false);
    }
  };

  const value = {
    user,
    loading: actionLoading,
    authLoading,
    error,
    login,
    loginWithToken,
    logout,
    refreshUser,
    changePassword,
    isAuthenticated: Boolean(user),
  };

  return (
    <AuthContext.Provider value={value}>
      <SessionTimeoutBridge logout={logout} isAuthenticated={Boolean(user)} authLoading={authLoading}>
        {children}
      </SessionTimeoutBridge>
    </AuthContext.Provider>
  );
};

function SessionTimeoutBridge({ children, logout, isAuthenticated, authLoading }) {
  const navigate = useNavigate();

  const handleExpire = useCallback(() => {
    logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  const { warningVisible, secondsLeft, staySignedIn } = useSessionTimeout({
    enabled: isAuthenticated && !authLoading,
    onExpire: handleExpire,
  });

  const handleLogoutFromModal = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <>
      {children}
      <SessionTimeoutModal
        open={warningVisible}
        secondsLeft={secondsLeft}
        onStaySignedIn={staySignedIn}
        onLogout={handleLogoutFromModal}
      />
    </>
  );
}
