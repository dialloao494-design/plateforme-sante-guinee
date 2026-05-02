import axios from 'axios';

export const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  'https://web-production-ad6a36.up.railway.app'
).trim();

const PUBLIC_PATHS = ['/auth/login', '/auth/register'];

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
  withCredentials: true,
});

httpClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token') || localStorage.getItem('access_token');
    config.headers = config.headers || {};

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    }

    delete config.headers.Authorization;

    if (!isPublicRequest(config.url)) {
      console.error('[AUTH] Missing token for protected request:', config.url);
      redirectToLogin();
      return Promise.reject(new Error('Missing authentication token'));
    }

    return config;
  },
  (error) => Promise.reject(error)
);

httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const method = String(error?.config?.method || 'GET').toUpperCase();
    const url = error?.config?.url || 'unknown-url';
    const status = error?.response?.status || 'NO_STATUS';
    const detail = error?.response?.data?.detail || error?.message || 'Unknown API error';
    console.error(`[API] ${method} ${url} -> ${status}`, detail);

    if (error?.response?.status === 401) {
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
