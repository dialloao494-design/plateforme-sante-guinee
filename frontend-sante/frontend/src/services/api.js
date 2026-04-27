import httpClient, { API_BASE_URL } from './httpClient.js';

// Legacy compatibility shim — used by AuthContext and other contexts
const api = {
  get: (path) => httpClient.get(path),
  post: (path, body) => httpClient.post(path, body),
  put: (path, body) => httpClient.put(path, body),
  delete: (path) => httpClient.delete(path),
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
  const { data } = await httpClient.get('/auth/me');
  return data;
};

export const authAPI = {
  login,
  me: getAuthenticatedUser,
  signup: (userData) => httpClient.post('/auth/register', userData),
};

export const patientsAPI = {
  getAll: () => httpClient.get('/patients/'),
  getById: (id) => httpClient.get(`/patients/${id}/`),
  create: (data) => httpClient.post('/patients/', data),
  update: (id, data) => httpClient.put(`/patients/${id}/`, data),
  delete: (id) => httpClient.delete(`/patients/${id}/`),
};

export const doctorsAPI = {
  getAll: (location, specialty) => {
    const params = new URLSearchParams();
    if (location) params.append('location', location);
    if (specialty) params.append('specialty', specialty);
    const qs = params.toString();
    return httpClient.get(`/doctors/${qs ? `?${qs}` : ''}`);
  },
  getById: (id) => httpClient.get(`/doctors/${id}/`),
  create: (data) => httpClient.post('/doctors/', data),
  update: (id, data) => httpClient.put(`/doctors/${id}/`, data),
  delete: (id) => httpClient.delete(`/doctors/${id}/`),
  getSchedule: (id) => httpClient.get(`/doctors/${id}/schedule/`),
  getAvailability: (id) => httpClient.get(`/doctors/${id}/availability/`),
};

export const appointmentsAPI = {
  getAll: () => httpClient.get('/appointments/'),
  getById: (id) => httpClient.get(`/appointments/${id}/`),
  create: (data) => httpClient.post('/appointments/', data),
  updateStatus: (id, status) => httpClient.put(`/appointments/${id}/`, { status }),
  cancel: (id) => httpClient.post(`/appointments/${id}/cancel`),
  getMyAppointments: () => httpClient.get('/appointments/me'),
};

export const doctorDashboardAPI = {
  getAppointments: () => httpClient.get('/doctor/appointments'),
};

export const paymentsAPI = {
  createIntent: (appointmentId) => httpClient.post('/payments/create-intent', { appointment_id: appointmentId }),
  confirmCheckout: (sessionId) => httpClient.post('/payments/confirm-checkout', { session_id: sessionId }),
  getStatus: (appointmentId) => httpClient.get(`/payments/${appointmentId}/status`),
};

export const messagesAPI = {
  getByAppointment: (appointmentId) => httpClient.get(`/messages/${appointmentId}`),
  sendToAppointment: (appointmentId, formData) => httpClient.post(`/messages/${appointmentId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

export default api;