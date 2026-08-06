import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api.js';
import httpClient, { clearClientAuth, setAuthSessionReady } from '../services/httpClient.js';
import { invalidateCache } from '../utils/apiCache.js';
import { touchSessionActivity, getAuthItem, setAuthItem, removeAuthItem, clearLegacySharedAuth } from '../utils/authStorage.js';
import { CACHE_TTL, getCached, setCached, buildCacheKey } from '../utils/apiCache.js';
import {
  AUTH_BOOTSTRAP_TIMEOUT_MS,
  logAuthSessionFailure,
  toBootstrapErrorMessage,
  withTimeout,
} from '../utils/authSession.js';
import { useSessionTimeout } from '../hooks/useSessionTimeout.js';
import SessionTimeoutModal from '../components/SessionTimeoutModal.jsx';
import { startAutoSync, stopAutoSync } from '../offline/sync.js';

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
  const bootstrapStartedRef = useRef(false);

  const clearPasswordResetFlags = () => {
    removeAuthItem('password_reset_required');
  };

  const toUserFriendlyLoginMessage = (err) => {
    const status = err?.response?.status;
    const rawDetail = err?.response?.data?.detail ?? err?.response?.data?.message ?? '';
    const detailText = Array.isArray(rawDetail)
      ? rawDetail.map((d) => d?.msg || d?.detail || JSON.stringify(d)).join(' ')
      : String(rawDetail || '');
    const detail = detailText.toLowerCase();
    const code = String(err?.code || '').toLowerCase();

    if (status === 401 || status === 400) {
      return 'Email ou mot de passe incorrect';
    }

    // Account lockout / rate limit — never hide behind a generic message.
    if (status === 429 || /locked|too many failed|slow down|rate limit|try again later/.test(detail)) {
      const retryAfter = Number(err?.response?.headers?.['retry-after'] || 0);
      if (/locked/.test(detail)) {
        return retryAfter > 0
          ? `Compte temporairement verrouillé après trop d’échecs. Réessayez dans ${Math.ceil(retryAfter / 60)} min.`
          : 'Compte temporairement verrouillé après trop d’échecs. Réessayez dans quelques minutes.';
      }
      return 'Trop de tentatives. Patientez un instant puis réessayez.';
    }

    if (status === 403) {
      if (/password change required|must_change_password/.test(detail)) {
        return 'Changement de mot de passe requis avant de continuer.';
      }
      return detailText || 'Accès refusé.';
    }

    if (
      code === 'err_network' ||
      code === 'econnrefused' ||
      /failed to fetch|network error|network|econnrefused|connection refused|timeout|405 not allowed|nginx/.test(detail) ||
      (!status && /login failed|network error/i.test(String(err?.message || '')))
    ) {
      if (import.meta.env.PROD) {
        const host = typeof window !== 'undefined' ? String(window.location.hostname || '') : '';
        if (/seven-rust-94\.vercel\.app$/i.test(host)) {
          return 'Ancien lien désactivé. Ouvrez https://plateforme-sante-guinee.vercel.app pour vous connecter.';
        }
        return 'Impossible de joindre le serveur. Réessayez dans un instant. Vérifiez que vous utilisez https://plateforme-sante-guinee.vercel.app';
      }
      return 'Impossible de joindre l’API. Vérifiez que le backend tourne sur http://127.0.0.1:8000.';
    }

    if (/missing authentication token/.test(detail)) {
      return 'Session non établie après connexion. Réessayez ou videz le cache du navigateur.';
    }

    // Prefer the real backend detail over a opaque generic string.
    if (detailText && status && status >= 400) {
      return `Erreur ${status} : ${detailText}`;
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
    // Stop offline replay before clearing identity-bound IndexedDB/PHI caches.
    stopAutoSync();
    // Clear React state immediately; the logout request clears HttpOnly cookies server-side.
    void authAPI.logout().catch(() => {}).finally(() => clearClientAuth());
    clearPasswordResetFlags();
    setUser(null);
    setError(null);
  }, []);

  const fetchCurrentUser = useCallback(async ({ allowRefresh = false } = {}) => {
    try {
      return await withTimeout(
        authAPI.me({ forceRefresh: true }),
        AUTH_BOOTSTRAP_TIMEOUT_MS,
        '/auth/me'
      );
    } catch (err) {
      if (allowRefresh && err?.response?.status === 401) {
        await withTimeout(authAPI.refresh(), AUTH_BOOTSTRAP_TIMEOUT_MS, '/auth/refresh');
        return await withTimeout(
          authAPI.me({ forceRefresh: true }),
          AUTH_BOOTSTRAP_TIMEOUT_MS,
          '/auth/me'
        );
      }
      throw err;
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const data = await fetchCurrentUser({ allowRefresh: true });
    if (!data) {
      throw new Error('Profil utilisateur vide');
    }
    const normalizedUser = normalizeAndStoreUser(data);
    setUser(normalizedUser);
    setAuthInitError(null);
    return normalizedUser;
  }, [fetchCurrentUser, normalizeAndStoreUser]);

  const bootstrapSession = useCallback(async ({ force = false } = {}) => {
    if (bootstrapStartedRef.current && !force) {
      return;
    }
    bootstrapStartedRef.current = true;
    setAuthSessionReady(false);
    const cachedProfile = readCachedProfile();
    if (cachedProfile) {
      setUser(cachedProfile);
    }

    setAuthInitError(null);
    setAuthLoading(true);

    try {
      // Use refresh when the short-lived access cookie expired but refresh is still valid.
      const data = await fetchCurrentUser({ allowRefresh: true });
      if (!data) {
        throw new Error('Profil utilisateur vide');
      }
      const normalizedUser = normalizeAndStoreUser(data);
      setUser(normalizedUser);
      setAuthInitError(null);
      clearLegacySharedAuth();
      startAutoSync(httpClient);
    } catch (err) {
      logAuthSessionFailure('bootstrap', err);
      const status = err?.response?.status;
      if (status === 401 || status === 403) {
        // Quiet anonymous session — no cookies yet.
        stopAutoSync();
        setUser(null);
        setAuthInitError(null);
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
  }, [fetchCurrentUser, normalizeAndStoreUser]);

  const retrySessionBootstrap = useCallback(async () => {
    bootstrapStartedRef.current = false;
    await bootstrapSession({ force: true });
  }, [bootstrapSession]);

  useEffect(() => {
    void bootstrapSession();
  }, [bootstrapSession]);

  const establishSession = useCallback(
    async (loginPayload) => {
      authDebug('establishSession: start', loginPayload?.role || loginPayload?.user_role);
      clearPasswordResetFlags();
      invalidateCache();
      invalidateCache('/auth/me');
      clearLegacySharedAuth();

      const meResponse = await fetchCurrentUser();
      authDebug('establishSession: /auth/me ok', meResponse?.email, meResponse?.role);
      if (!meResponse) {
        throw new Error('Profil utilisateur vide après connexion');
      }
      const normalizedUser = normalizeAndStoreUser(meResponse);
      setUser(normalizedUser);
      startAutoSync(httpClient);
      authDebug('establishSession: user state set', normalizedUser?.role);
      return normalizedUser;
    },
    [fetchCurrentUser, normalizeAndStoreUser],
  );

  const loginWithToken = async (loginPayload) => {
    setActionLoading(true);
    setError(null);
    try {
      const normalizedUser = await establishSession(loginPayload);
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

  const login = async (email, password) => {
    setActionLoading(true);
    setError(null);

    try {
      const trimmedEmail = String(email || '').trim().toLowerCase();
      authDebug('login: request start', trimmedEmail);
      const loginPayload = await authAPI.login(trimmedEmail, password);
      authDebug('login: response ok', Boolean(loginPayload?.csrf_token), loginPayload?.role);
      const normalizedUser = await establishSession(loginPayload);
      authDebug('login: complete', { role: normalizedUser?.role, clinic_id: normalizedUser?.clinic_id });
      return {
        success: true,
        role: normalizedUser?.role,
        clinic_id: normalizedUser?.clinic_id,
        home: normalizedUser?.role,
        must_change_password: Boolean(normalizedUser?.must_change_password),
      };
    } catch (err) {
      authDebug('login: failed', err?.response?.status, err?.message);
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
