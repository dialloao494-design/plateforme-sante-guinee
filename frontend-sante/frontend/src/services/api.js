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

// Add response interceptor to enforce global auth handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('user_id');

      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/signup') {
        window.location.href = '/login';
      }
    }

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
  getAll: (location, specialty) => {
    const params = new URLSearchParams();
    if (location) params.append('location', location);
    if (specialty) params.append('specialty', specialty);
    const queryString = params.toString();
    return api.get(`/doctors${queryString ? '?' + queryString : ''}`);
  },
  getById: (id) => api.get(`/doctors/${id}`),
  create: (doctorData) => api.post('/doctors', doctorData),
  update: (id, doctorData) => api.put(`/doctors/${id}`, doctorData),
  delete: (id) => api.delete(`/doctors/${id}`),
  getSchedule: (id) => api.get(`/doctors/${id}/schedule`),
  getAvailability: (id) => api.get(`/doctors/${id}/availability`),
};

// Appointments API
export const appointmentsAPI = {
  getAll: () => api.get('/appointments/'),
  getById: (id) => api.get(`/appointments/${id}`),
  create: (appointmentData) => api.post('/appointments/', appointmentData),
  updateStatus: (id, status) => api.put(`/appointments/${id}`, { status }),
  cancel: (id) => api.delete(`/appointments/${id}`),
  getMyAppointments: () => api.get('/appointments/'),
};

export const paymentsAPI = {
  createIntent: (appointmentId) => api.post('/payments/create-intent', { appointment_id: appointmentId }),
  confirmCheckout: (sessionId) => api.post('/payments/confirm-checkout', { session_id: sessionId }),
  getStatus: (appointmentId) => api.get(`/payments/${appointmentId}/status`),
};

export default api;