import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => {
    const credentials = new URLSearchParams();
    credentials.append('username', email);
    credentials.append('password', password);
    return api.post('/auth/login', credentials.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
  loginJson: (email, password) => api.post('/auth/login-json', { email, password }),
  me: () => api.get('/auth/me'),
  signup: (userData) => api.post('/auth/register', userData),
};

// Patients API
export const patientsAPI = {
  getAll: () => api.get('/patients'),
  getById: (id) => api.get(`/patients/${id}`),
  create: (patientData) => api.post('/patients', patientData),
  update: (id, patientData) => api.put(`/patients/${id}`, patientData),
  delete: (id) => api.delete(`/patients/${id}`),
};

// Doctors API
export const doctorsAPI = {
  getAll: () => api.get('/doctors'),
};

// Appointments API
export const appointmentsAPI = {
  getAll: () => api.get('/rendezvous'),
  getById: (id) => api.get(`/rendezvous/${id}`),
  create: (appointmentData) => api.post('/rendezvous/', appointmentData),
  updateStatus: (id, status) => api.patch(`/rendezvous/${id}`, { status }),
  cancel: (id) => api.post(`/rendezvous/${id}/cancel`),
};

export const paymentsAPI = {
  createIntent: (appointmentId) => api.post('/payments/create-intent', { appointment_id: appointmentId }),
  getStatus: (appointmentId) => api.get(`/payments/${appointmentId}/status`),
};

export default api;