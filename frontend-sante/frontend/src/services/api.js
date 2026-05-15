import httpClient, { API_BASE_URL } from './httpClient.js';

// Legacy compatibility shim — used by AuthContext and other contexts
const api = {
  get: (path) => httpClient.get(path),
  post: (path, body) => httpClient.post(path, body),
  put: (path, body) => httpClient.put(path, body),
  delete: (path) => httpClient.delete(path),
};

// Login via JSON (same credential validation as form login; avoids URL-encoding edge cases).
export const login = async (email, password) => {
  try {
    const response = await httpClient.post('/auth/login-json', {
      email: String(email || '').trim().toLowerCase(),
      password,
    });
    return response?.data;
  } catch (err) {
    const detail = err?.response?.data?.detail || err?.response?.data?.message;
    const loginError = new Error(detail || 'Login failed');
    loginError.response = err?.response;
    throw loginError;
  }
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
  getAll: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.location) qs.append('location', params.location);
    if (params.specialty) qs.append('specialty', params.specialty);
    if (params.search) qs.append('search', params.search);
    const s = qs.toString();
    return httpClient.get(s ? `/doctors/?${s}` : '/doctors/');
  },
  getNearby: (params) => {
    const qs = new URLSearchParams();
    qs.append('lat', String(params.lat));
    qs.append('lon', String(params.lon));
    if (params.radius_km != null) qs.append('radius_km', String(params.radius_km));
    if (params.specialty) qs.append('specialty', params.specialty);
    return httpClient.get(`/doctors/nearby?${qs.toString()}`);
  },
  patchMyGeo: (body) => httpClient.patch('/doctors/me/geo', body),
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
  confirmPayment: (appointmentId) => httpClient.post(`/payments/${appointmentId}/confirm-payment`),
  getStatus: (appointmentId) => httpClient.get(`/payments/${appointmentId}/status`),
  list: () => httpClient.get('/payments/'),
  railConfig: () => httpClient.get('/payments/rail-config'),
  mobileMoneyInitiate: (body) => httpClient.post('/payments/mobile-money/initiate', body),
};

export const notificationsAPI = {
  channels: () => httpClient.get('/notifications/channels'),
  list: () => httpClient.get('/notifications/'),
};

export const teleconsultationAPI = {
  getAccess: (appointmentId) => httpClient.get(`/teleconsultation/appointments/${appointmentId}/access`),
  endSession: (appointmentId) => httpClient.post(`/teleconsultation/appointments/${appointmentId}/end`),
  config: () => httpClient.get('/teleconsultation/config'),
};

export const messagesAPI = {
  getByAppointment: (appointmentId) => httpClient.get(`/messages/${appointmentId}`),
  sendToAppointment: (appointmentId, formData) => httpClient.post(`/messages/${appointmentId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

export default api;