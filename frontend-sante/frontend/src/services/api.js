import axios from 'axios';

export const API_BASE_URL = 'https://web-production-ad6a36.up.railway.app';

// Single axios instance — token attached automatically via interceptor
const API = axios.create({
  baseURL: API_BASE_URL,
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('user_id');
    }
    return Promise.reject(error);
  }
);

// Legacy compatibility shim — used by AuthContext and other contexts
const api = {
  get: (path) => API.get(path),
  post: (path, body) => API.post(path, body),
  put: (path, body) => API.put(path, body),
  delete: (path) => API.delete(path),
};

// Login uses form-encoded POST (OAuth2PasswordRequestForm — must NOT use axios here)
export const login = async (email, password) => {
  const body = new URLSearchParams();
  body.append('username', email);
  body.append('password', password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text ? { message: text } : null; }

  if (!response.ok) {
    const err = new Error(data?.detail || data?.message || 'Login failed');
    err.response = { status: response.status, data };
    throw err;
  }
  return data;
};

export const getAuthenticatedUser = async () => {
  const { data } = await API.get('/auth/me');
  return data;
};

export const authAPI = {
  login,
  me: getAuthenticatedUser,
  signup: (userData) => API.post('/auth/register', userData),
};

export const patientsAPI = {
  getAll: () => API.get('/patients/'),
  getById: (id) => API.get(`/patients/${id}/`),
  create: (data) => API.post('/patients/', data),
  update: (id, data) => API.put(`/patients/${id}/`, data),
  delete: (id) => API.delete(`/patients/${id}/`),
};

export const doctorsAPI = {
  getAll: (location, specialty) => {
    const params = new URLSearchParams();
    if (location) params.append('location', location);
    if (specialty) params.append('specialty', specialty);
    const qs = params.toString();
    return API.get(`/doctors/${qs ? `?${qs}` : ''}`);
  },
  getById: (id) => API.get(`/doctors/${id}/`),
  create: (data) => API.post('/doctors/', data),
  update: (id, data) => API.put(`/doctors/${id}/`, data),
  delete: (id) => API.delete(`/doctors/${id}/`),
  getSchedule: (id) => API.get(`/doctors/${id}/schedule/`),
  getAvailability: (id) => API.get(`/doctors/${id}/availability/`),
};

export const appointmentsAPI = {
  getAll: () => API.get('/appointments/'),
  getById: (id) => API.get(`/appointments/${id}/`),
  create: (data) => API.post('/appointments/', data),
  updateStatus: (id, status) => API.put(`/appointments/${id}/`, { status }),
  cancel: (id) => API.delete(`/appointments/${id}/`),
  getMyAppointments: () => API.get('/appointments/'),
};

export const paymentsAPI = {
  createIntent: (appointmentId) => API.post('/payments/create-intent', { appointment_id: appointmentId }),
  confirmCheckout: (sessionId) => API.post('/payments/confirm-checkout', { session_id: sessionId }),
  getStatus: (appointmentId) => API.get(`/payments/${appointmentId}/status`),
};

export default api;