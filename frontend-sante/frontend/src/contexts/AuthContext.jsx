import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api.js';
import { clearClientAuth, setAuthSessionReady } from '../services/httpClient.js';
import { invalidateCache } from '../utils/apiCache.js';
import { touchSessionActivity, getAuthItem, setAuthItem, removeAuthItem, setAuthToken, getAuthToken, clearLegacySharedAuth, setRefreshToken, getRefreshToken } from '../utils/authStorage.js';
import { CACHE_TTL, getCached, setCached, buildCacheKey } from '../utils/apiCache.js';
import {
  AUTH_BOOTSTRAP_TIMEOUT_MS,
  logAuthSessionFailure,
  toBootstrapErrorMessage,
  withTimeout,
} from '../utils/authSession.js';
import { useSessionTimeout } from '../hooks/useSessionTimeout.js';
import SessionTimeoutModal from '../components/SessionTimeoutModal.jsx';

const AUTH_PROFILE_STORAGE_KEY = 'sg_auth_profile';

function authProfileCacheKey() {
  const uid = getAuthItem('user_id') || '0';
  return buildCacheKey('get', '/auth/me', { uid });
}

function readCachedProfile() {
  try {
    const raw = getAuthItem(AUTH_PROFILE_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.id) {
        return parsed;
      }
    }
  } catch {
    /* ignore */
  }
  return getCached(authProfileCacheKey(), { persist: true }) ?? null;
}

function cacheProfile(user) {
  if (!user) {
    return;
  }
  try {
    setAuthItem(AUTH_PROFILE_STORAGE_KEY, JSON.stringify(user));
  } catch {
    /* ignore */
  }
  setCached(authProfileCacheKey(), user, CACHE_TTL.authProfile, { persist: true });
}

const authDebug = (...args) => {
  console.info('[AUTH-DEBUG]', ...args);
};

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
  const [authInitError, setAuthInitError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);

  const clearPasswordResetFlags = () => {
    removeAuthItem('password_reset_required');
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
      return import.meta.env.PROD
        ? 'Impossible de joindre le serveur. Réessayez dans un instant.'
        : 'Impossible de joindre l’API. Vérifiez que le backend tourne sur http://127.0.0.1:8000.';
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
      setAuthItem('user_id', String(normalizedUser.id));
    }
    if (normalizedUser.role) {
      setAuthItem('user_role', normalizedUser.role);
    }
    touchSessionActivity();

    cacheProfile(normalizedUser);

    return normalizedUser;
  }, []);

  const logout = useCallback(() => {
    const refresh = getRefreshToken();
    clearPasswordResetFlags();
    // Fire-and-forget server revoke; always clear client state.
    authAPI.logout(refresh).catch(() => {});
    clearClientAuth();
    setUser(null);
    setError(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const data = await withTimeout(
      authAPI.me({ forceRefresh: true }),
      AUTH_BOOTSTRAP_TIMEOUT_MS,
      '/auth/me'
    );
    if (!data) {
      throw new Error('Profil utilisateur vide');
    }
    const normalizedUser = normalizeAndStoreUser(data);
    setUser(normalizedUser);
    setAuthInitError(null);
    return normalizedUser;
  }, [normalizeAndStoreUser]);

  const bootstrapSession = useCallback(async () => {
    setAuthSessionReady(false);
    const storedToken = getAuthToken();
    if (!storedToken) {
      setUser(null);
      setAuthInitError(null);
      setAuthLoading(false);
      setAuthSessionReady(true);
      return;
    }

    const cachedProfile = readCachedProfile();
    if (cachedProfile) {
      setUser(cachedProfile);
    }

    if (!getAuthItem('token')) {
      setAuthToken(storedToken);
    }

    setAuthInitError(null);
    setAuthLoading(true);

    try {
      const data = await withTimeout(
        authAPI.me({ forceRefresh: true }),
        AUTH_BOOTSTRAP_TIMEOUT_MS,
        '/auth/me'
      );
      if (!data) {
        throw new Error('Profil utilisateur vide');
      }
      const normalizedUser = normalizeAndStoreUser(data);
      setUser(normalizedUser);
      setAuthInitError(null);
      clearLegacySharedAuth();
    } catch (err) {
      logAuthSessionFailure('bootstrap', err);
      const status = err?.response?.status;
      if (status === 401 || status === 403) {
        clearClientAuth();
        setUser(null);
        setAuthInitError(toBootstrapErrorMessage(err));
      } else {
        setAuthInitError(toBootstrapErrorMessage(err));
        if (!cachedProfile) {
          setUser(null);
        }
      }
    } finally {
      setAuthLoading(false);
      setAuthSessionReady(true);
    }
  }, [normalizeAndStoreUser]);

  const retrySessionBootstrap = useCallback(async () => {
    await bootstrapSession();
  }, [bootstrapSession]);

  useEffect(() => {
    bootstrapSession();
  }, [bootstrapSession]);

  const applyLoginToken = useCallback(
    async (loginPayload) => {
      authDebug('applyLoginToken: start');
      const access_token =
        loginPayload?.access_token ||
        loginPayload?.accessToken ||
        loginPayload?.token;

      if (!access_token) {
        authDebug('applyLoginToken: missing access_token in payload', loginPayload);
        throw new Error('Login response missing access_token');
      }

      clearPasswordResetFlags();
      invalidateCache();
      invalidateCache('/auth/me');
      setAuthToken(access_token);
      if (loginPayload?.refresh_token) {
        setRefreshToken(loginPayload.refresh_token);
      }
      if (loginPayload?.must_change_password != null) {
        setAuthItem('must_change_password', loginPayload.must_change_password ? '1' : '0');
      }
      clearLegacySharedAuth();
      authDebug('applyLoginToken: token stored', Boolean(access_token));

      const meResponse = await withTimeout(
        authAPI.me({ forceRefresh: true }),
        AUTH_BOOTSTRAP_TIMEOUT_MS,
        '/auth/me'
      );
      authDebug('applyLoginToken: /auth/me ok', meResponse?.email, meResponse?.role);
      if (!meResponse) {
        throw new Error('Profil utilisateur vide après connexion');
      }
      const normalizedUser = normalizeAndStoreUser(meResponse);
      setUser(normalizedUser);
      authDebug('applyLoginToken: user state set', normalizedUser?.role);
      return normalizedUser;
    },
    [normalizeAndStoreUser],
  );

  const loginWithToken = async (loginPayload) => {
    setActionLoading(true);
    setError(null);
    try {
      const normalizedUser = await applyLoginToken(loginPayload);
      return { success: true, role: normalizedUser?.role, clinic_id: normalizedUser?.clinic_id };
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

  const login = async (email, password, mfaCode) => {
    setActionLoading(true);
    setError(null);

    try {
      const trimmedEmail = String(email || '').trim().toLowerCase();
      authDebug('login: request start', trimmedEmail);
      const loginPayload = await authAPI.login(trimmedEmail, password, mfaCode);
      authDebug('login: response ok', Boolean(loginPayload?.access_token), loginPayload?.role);
      const normalizedUser = await applyLoginToken(loginPayload);
      authDebug('login: complete', { role: normalizedUser?.role, clinic_id: normalizedUser?.clinic_id });
      return {
        success: true,
        role: normalizedUser?.role,
        clinic_id: normalizedUser?.clinic_id,
        home: normalizedUser?.role,
        must_change_password: Boolean(
          normalizedUser?.must_change_password || loginPayload?.must_change_password
        ),
      };
    } catch (err) {
      authDebug('login: failed', err?.response?.status, err?.message);
      const detail = String(err?.response?.data?.detail || err?.message || '');
      if (/mfa code required/i.test(detail)) {
        setError('Code MFA requis');
        return { success: false, error: 'Code MFA requis', mfaRequired: true };
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
      const response = await authAPI.changePassword(currentPassword, newPassword);
      const data = response?.data || response;
      if (data?.access_token) {
        setAuthToken(data.access_token);
        if (data.refresh_token) {
          setRefreshToken(data.refresh_token);
        }
      }
      removeAuthItem('must_change_password');
      invalidateCache('/auth/me');
      const updated = await refreshUser();
      return { success: true, user: updated };
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
    authInitError,
    error,
    login,
    loginWithToken,
    logout,
    refreshUser,
    retrySessionBootstrap,
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
