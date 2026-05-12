import axios from 'axios';

const isLocalDevApi = (u) =>
  /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?\b/i.test(String(u || ''));

// Resolve API base URL from environment variable
// Local dev: keep http:// for localhost / 127.0.0.1 so a local FastAPI instance works.
// Production: upgrade http -> https for non-local hosts only.
export const API_BASE_URL = (() => {
  let url = (import.meta.env.VITE_API_URL || '').trim();

  if (!url) {
    url = import.meta.env.PROD
      ? 'https://web-production-ad6a36.up.railway.app'
      : 'http://127.0.0.1:8000';
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

const isPublicRequest = (url = '') => {
  return PUBLIC_PATHS.some((path) => String(url).includes(path));
};

const redirectToLogin = () => {
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
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
  (response) => {
    const url = response.config?.url || 'unknown';
    const status = response.status;
    if (
      import.meta.env.DEV &&
      (url.includes('/auth/') || url.includes('/patients/') || url.includes('/appointments'))
    ) {
      console.log(`[HTTP ${status}] ${url}`);
    }
    return response;
  },
  (error) => {
    const url = error?.config?.url || 'unknown';
    const status = error?.response?.status || 'no-response';
    const message = error?.response?.data?.detail || error?.message || 'unknown';

    if (
      import.meta.env.DEV &&
      (url.includes('/auth/') || url.includes('/patients/') || url.includes('/appointments'))
    ) {
      console.error(`[HTTP ${status}] ${url}:`, message);
    }

    if (error?.response?.status === 401) {
      if (import.meta.env.DEV) {
        console.warn('[HTTP 401] Clearing token and redirecting to login');
      }
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('user_id');
      redirectToLogin();
    }

    return Promise.reject(error);
  }
);

export default httpClient;
