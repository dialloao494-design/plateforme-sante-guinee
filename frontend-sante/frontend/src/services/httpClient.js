import axios from 'axios';

/** Localhost or private LAN (RFC1918) — never force HTTPS upgrade in dev. */
const isPrivateDevHost = (hostname) =>
  /^(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})$/i.test(
    String(hostname || '')
  );

const isLocalDevApi = (u) => {
  try {
    const host = new URL(u, 'http://dummy').hostname;
    return isPrivateDevHost(host);
  } catch {
    return /^https?:\/\/(localhost|127\.0\.0\.1)/i.test(String(u || ''));
  }
};

const defaultApiPort = () => String(import.meta.env.VITE_API_PORT || '8000').trim();

/** Map browser hostname to a stable API host (Windows: localhost often hits ::1 / Jitsi on :8000). */
const resolveDevApiHost = (hostname) => {
  if (/^localhost$/i.test(hostname)) {
    return '127.0.0.1';
  }
  return hostname;
};

/** When opened as http://192.168.x.x:5173, API must be http://192.168.x.x:8000 (not localhost). */
const resolveDevApiFromBrowser = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  const { hostname, protocol } = window.location;
  if (!isPrivateDevHost(hostname)) {
    return null;
  }
  const apiHost = resolveDevApiHost(hostname);
  return `${protocol}//${apiHost}:${defaultApiPort()}`;
};

const rewriteLocalhostToCurrentHost = (url) => {
  if (typeof window === 'undefined' || !url) {
    return url;
  }
  const host = window.location.hostname;
  if (!isPrivateDevHost(host) || /^localhost|127\.0\.0\.1$/i.test(host)) {
    return url;
  }
  return url.replace(/\/\/(localhost|127\.0\.0\.1)(?=:\d+|\/|$)/gi, `//${host}`);
};

/** Nginx/docker serves API under /api — prefix paths when base is page origin only. */
const usesNginxApiPrefix = (baseUrl) => {
  if (import.meta.env.DEV && import.meta.env.VITE_USE_RELATIVE_API === 'true') {
    return false;
  }
  if (typeof window === 'undefined') {
    return false;
  }
  try {
    const base = new URL(baseUrl, window.location.origin);
    return base.origin === window.location.origin && !base.pathname.replace(/\/$/, '').endsWith('/api');
  } catch {
    return false;
  }
};

const ensureNginxApiPath = (url = '') => {
  if (!url || /^https?:\/\//i.test(url)) {
    return url;
  }
  const path = url.startsWith('/') ? url : `/${url}`;
  if (path.startsWith('/api/') || path === '/api') {
    return path;
  }
  return `/api${path}`;
};

// Resolve API base URL from environment variable
export const API_BASE_URL = (() => {
  const explicitUrl = (import.meta.env.VITE_API_URL || '').trim();
  const sameOriginApi =
    import.meta.env.VITE_SAME_ORIGIN_API === 'true' ||
    import.meta.env.VITE_USE_RELATIVE_API === 'true' ||
    explicitUrl === '/api';

  if (sameOriginApi && typeof window !== 'undefined') {
    return window.location.origin;
  }

  const useRelativeApi =
    import.meta.env.VITE_USE_RELATIVE_API === 'true' && typeof window !== 'undefined';

  if (useRelativeApi) {
    return window.location.origin;
  }

  let url = explicitUrl;

  if (!url) {
    if (import.meta.env.PROD) {
      if (typeof window !== 'undefined') {
        return window.location.origin;
      }
      const fallback = (import.meta.env.VITE_PUBLIC_API_FALLBACK || '').trim();
      url = fallback || 'https://web-production-ad6a36.up.railway.app';
      if (!explicitUrl) {
        console.warn(
          '[API] VITE_API_URL non défini : utilisation de l’API publique par défaut. Définissez VITE_API_URL (et optionnellement VITE_PUBLIC_API_FALLBACK) sur Vercel / votre hébergeur.'
        );
      }
    } else {
      url = resolveDevApiFromBrowser() || 'http://127.0.0.1:8000';
    }
  } else if (import.meta.env.DEV) {
    url = rewriteLocalhostToCurrentHost(url);
  }

  if (import.meta.env.DEV && !explicitUrl) {
    const fromBrowser = resolveDevApiFromBrowser();
    if (fromBrowser) {
      url = fromBrowser;
    }
  }

  // Docker/nginx/mobile tunnel: baked localhost must follow the page origin at runtime.
  if (typeof window !== 'undefined' && import.meta.env.PROD && /localhost|127\.0\.0\.1/i.test(url)) {
    return window.location.origin;
  }

  if (import.meta.env.PROD && /localhost|127\.0\.0\.1/i.test(url)) {
    throw new Error('Invalid API URL in production: localhost is not allowed');
  }

  if (url.startsWith('http://') && !isLocalDevApi(url)) {
    return url.replace('http://', 'https://');
  }

  return url;
})();

if (import.meta.env.DEV) {
  console.info('[API_BASE_URL]', API_BASE_URL);
}

const PUBLIC_PATHS = ['/auth/login', '/auth/login-json', '/auth/register'];

export function clearClientAuth() {
  if (typeof window === 'undefined') {
    return;
  }
  localStorage.removeItem('token');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  localStorage.removeItem('user_id');
  syncAuthHeader();
}

const isPublicRequest = (url = '') => {
  return PUBLIC_PATHS.some((path) => String(url).includes(path));
};

const redirectToLogin = () => {
  if (typeof window === 'undefined' || window.location.pathname === '/login') {
    return;
  }
  window.location.replace('/login');
};

const httpClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: false,
});

const syncAuthHeader = () => {
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  if (token) {
    httpClient.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else if (httpClient.defaults.headers.common?.Authorization) {
    delete httpClient.defaults.headers.common.Authorization;
  }
};

syncAuthHeader();

httpClient.interceptors.request.use(
  (config) => {
    syncAuthHeader();

    const runtimeBase = config.baseURL || httpClient.defaults.baseURL || API_BASE_URL;
    if (usesNginxApiPrefix(runtimeBase) && typeof config.url === 'string') {
      config.url = ensureNginxApiPath(config.url);
    }

    if (
      typeof config.baseURL === 'string' &&
      config.baseURL.startsWith('http://') &&
      !isLocalDevApi(config.baseURL)
    ) {
      config.baseURL = config.baseURL.replace('http://', 'https://');
    }

    if (typeof config.url === 'string' && /^http:\/\//i.test(config.url) && !isLocalDevApi(config.url)) {
      config.url = config.url.replace(/^http:\/\//i, 'https://');
    }

    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    config.headers = config.headers || {};

    if (token) {
      if (typeof config.headers.set === 'function') {
        config.headers.set('Authorization', `Bearer ${token}`);
      } else {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    }

    delete config.headers.Authorization;

    if (!isPublicRequest(config.url)) {
      if (import.meta.env.DEV) {
        console.warn(`[HTTP] Protected request without token: ${config.url}`);
      }
      redirectToLogin();
      return Promise.reject(new Error('Missing authentication token'));
    }

    return config;
  },
  (error) => Promise.reject(error)
);

httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error?.config;
    const url = config?.url || 'unknown';
    const statusCode = error?.response?.status;
    const message = error?.response?.data?.detail || error?.message || 'unknown';

    const method = String(config?.method || 'get').toLowerCase();
    const retryableGet =
      Boolean(config) &&
      method === 'get' &&
      statusCode !== 401 &&
      (!error.response || statusCode === 408 || statusCode === 429 || (statusCode >= 500 && statusCode < 600));

    if (retryableGet) {
      const attempt = Number(config.__retryAttempt || 0);
      if (attempt < 2) {
        config.__retryAttempt = attempt + 1;
        await new Promise((resolve) => {
          window.setTimeout(resolve, 350 * config.__retryAttempt);
        });
        return httpClient(config);
      }
    }

    if (import.meta.env.DEV && statusCode >= 400) {
      console.error(`[HTTP ${statusCode}] ${url}:`, message);
    }

    if (error?.response?.status === 401) {
      if (import.meta.env.DEV) {
        console.warn('[HTTP 401] Clearing token and redirecting to login');
      }
      clearClientAuth();
      redirectToLogin();
    }

    return Promise.reject(error);
  }
);

export default httpClient;
