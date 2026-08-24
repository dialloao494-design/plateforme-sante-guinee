import httpClient, { API_BASE_URL, refreshAuthSession } from './httpClient.js';
import { CACHE_TTL } from '../utils/apiCache.js';
import { cachedGet } from '../utils/cachedHttp.js';

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

export const getAuthenticatedUser = async (opts = {}) => {
  const { data } = await cachedGet('/auth/me', {
    cacheTtlMs: CACHE_TTL.authProfile,
    cachePersist: true,
    forceRefresh: opts.forceRefresh,
  });
  return data;
};

export const authAPI = {
  login,
  me: (opts) => getAuthenticatedUser(opts),
  updateProfile: async (profile) => {
    const { data } = await httpClient.patch('/auth/me', profile);
    return data;
  },
  refresh: () => refreshAuthSession(),
  logout: async () => {
    const { data } = await httpClient.post('/auth/logout');
    return data;
  },
  signup: async (userData) => {
    const { data } = await httpClient.post('/auth/register', userData);
    return data;
  },
  changePassword: async (currentPassword, newPassword) => {
    const { data } = await httpClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  },
  forgotPassword: (email) =>
    httpClient.post('/auth/forgot-password', { email: String(email || '').trim().toLowerCase() }),
  resetPassword: (token, newPassword) =>
    httpClient.post('/auth/reset-password', { token, new_password: newPassword }),
  verifyEmail: (token) => httpClient.post('/auth/verify-email', { token }),
  resendVerification: (email) =>
    httpClient.post('/auth/resend-verification', { email: String(email || '').trim().toLowerCase() }),
  inspectStaffActivation: (token) => httpClient.post('/auth/staff-activation/inspect', { token }),
  completeStaffActivation: (token, password) =>
    httpClient.post('/auth/staff-activation/complete', { token, password }),
};

export const patientsAPI = {
  getAll: () => httpClient.get('/patients/'),
  getById: (id) => httpClient.get(`/patients/${id}/`),
  create: (data) => httpClient.post('/patients/', data),
  update: (id, data) => httpClient.put(`/patients/${id}/`, data),
  delete: (id) => httpClient.delete(`/patients/${id}/`),
  searchAccountCandidates: (q) =>
    httpClient.get('/patients/account-candidates', { params: { q: String(q || '').trim() } }),
};

export const patientRecordAPI = {
  getPatient: (id) => httpClient.get(`/patients/${id}/`),
  listNotes: (patientId) => httpClient.get(`/patients/${patientId}/notes`),
  createNote: (patientId, data) => httpClient.post(`/patients/${patientId}/notes`, data),
  listSummaries: (patientId) => httpClient.get(`/patients/${patientId}/summaries`),
  createSummary: (patientId, data) => httpClient.post(`/patients/${patientId}/summaries`, data),
  listDocuments: (patientId) => httpClient.get(`/patients/${patientId}/documents`),
  uploadDocument: (patientId, formData) =>
    httpClient.post(`/patients/${patientId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  downloadDocument: (patientId, documentId) =>
    httpClient.get(`/patients/${patientId}/documents/${documentId}/download`, {
      responseType: 'blob',
    }),
  getTimeline: (patientId) => httpClient.get(`/patients/${patientId}/timeline`),
  getMedicalHistory: (patientId) => httpClient.get(`/patients/${patientId}/medical-history`),
  getMyMedicalHistory: () => httpClient.get('/patients/me/medical-history'),
  getTimelineGrouped: (patientId) => httpClient.get(`/patients/${patientId}/timeline-grouped`),
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

export const notificationsAPI = {
  channels: () => httpClient.get('/notifications/channels'),
  list: () => httpClient.get('/notifications/'),
};

export const teleconsultationAPI = {
  getRoomStatus: (appointmentId) =>
    httpClient.get(`/teleconsultation/appointments/${appointmentId}/room-status`),
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

export const platformSetupAPI = {
  getStatus: async () => {
    const { data } = await httpClient.get('/platform/setup/status');
    return data;
  },
  completeSetup: async (payload) => {
    const { data } = await httpClient.post('/platform/setup', payload);
    return data;
  },
};

export default api;
