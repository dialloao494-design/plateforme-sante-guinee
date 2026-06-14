import httpClient from './httpClient';

const clinicalApi = {
  operationsSummary: () => httpClient.get('/clinical/operations/summary'),

  // Admin
  createClinic: (data) => httpClient.post('/clinical/clinics', data),
  listClinics: () => httpClient.get('/clinical/clinics'),
  createStaff: (data) => httpClient.post('/clinical/staff', data),

  // Reception
  intakePatient: (data) => httpClient.post('/clinical/reception/patients', data),
  createAppointment: (data) => httpClient.post('/clinical/reception/appointments', data),
  receptionQueue: () => httpClient.get('/clinical/reception/queue'),
  checkIn: (appointmentId) =>
    httpClient.post(`/clinical/reception/appointments/${appointmentId}/check-in`),
  clinicDoctors: () => httpClient.get('/clinical/reception/doctors'),

  // Doctor
  doctorQueue: () => httpClient.get('/clinical/doctor/queue'),
  startConsultation: (data) => httpClient.post('/clinical/consultations', data),
  updateConsultation: (id, data) => httpClient.patch(`/clinical/consultations/${id}`, data),
  orderLab: (consultationId, data) =>
    httpClient.post(`/clinical/consultations/${consultationId}/lab-orders`, data),
  prescribe: (consultationId, data) =>
    httpClient.post(`/clinical/consultations/${consultationId}/prescriptions`, data),

  // Lab
  labQueue: () => httpClient.get('/clinical/lab/orders'),
  updateLabOrder: (id, data) => httpClient.patch(`/clinical/lab/orders/${id}`, data),
  recordLabResult: (orderId, data) => httpClient.post(`/clinical/lab/orders/${orderId}/results`, data),
  validateLabResult: (resultId) => httpClient.post(`/clinical/lab/results/${resultId}/validate`),

  // Pharmacy
  pharmacyQueue: () => httpClient.get('/clinical/pharmacy/orders'),
  updatePharmacyOrder: (id, data) => httpClient.patch(`/clinical/pharmacy/orders/${id}`, data),

  receptionFollowUps: () => httpClient.get('/clinical/reception/follow-ups'),
  recordVitals: (consultationId, data) =>
    httpClient.post(`/clinical/consultations/${consultationId}/vitals`, data),
  scheduleFollowUp: (consultationId, data) =>
    httpClient.post(`/clinical/consultations/${consultationId}/follow-ups`, data),
  patientJourney: (patientId) => httpClient.get(`/clinical/patients/${patientId}/journey`),

  // Audit
  auditLogs: (params) => httpClient.get('/clinical/audit-logs', { params }),

  // Billing
  pendingCharges: () => httpClient.get('/clinical/billing/charges/pending'),
  payCharge: (chargeId, paymentMethod) =>
    httpClient.post(`/clinical/billing/charges/${chargeId}/pay`, { payment_method: paymentMethod }),
  dailyRevenue: (day) =>
    httpClient.get('/clinical/billing/revenue/daily', { params: day ? { day } : {} }),

  // Admin ops
  backupStatus: () => httpClient.get('/clinical/admin/backup-status'),

  // Hospitalization
  hospitalOccupancy: () => httpClient.get('/clinical/hospitalization/occupancy'),
  hospitalRooms: () => httpClient.get('/clinical/hospitalization/rooms'),
  createHospitalRoom: (data) => httpClient.post('/clinical/hospitalization/rooms', data),
  hospitalBeds: (roomId) =>
    httpClient.get('/clinical/hospitalization/beds', { params: roomId ? { room_id: roomId } : {} }),
  addHospitalBed: (roomId, data) => httpClient.post(`/clinical/hospitalization/rooms/${roomId}/beds`, data),
  hospitalAdmissions: (status) =>
    httpClient.get('/clinical/hospitalization/admissions', { params: status ? { status } : {} }),
  createAdmission: (data) => httpClient.post('/clinical/hospitalization/admissions', data),
  getAdmission: (id) => httpClient.get(`/clinical/hospitalization/admissions/${id}`),
  updateAdmissionStatus: (id, data) => httpClient.patch(`/clinical/hospitalization/admissions/${id}/status`, data),
  assignBed: (id, data) => httpClient.post(`/clinical/hospitalization/admissions/${id}/assign-bed`, data),

  // Unified billing
  listInvoices: (status) =>
    httpClient.get('/clinical/billing/unified/invoices', { params: status ? { status } : {} }),
  generateInvoice: (data) => httpClient.post('/clinical/billing/unified/invoices/generate', data),
  payInvoice: (id, data) => httpClient.post(`/clinical/billing/unified/invoices/${id}/pay`, data),
  invoicePdfUrl: (id) => `${httpClient.defaults.baseURL}/clinical/billing/unified/invoices/${id}/pdf`,

  // Discharge
  dischargeOpenVisits: () => httpClient.get('/clinical/discharge/visits/open'),
  dischargeChecklist: (visitId) => httpClient.get(`/clinical/discharge/checklist/${visitId}`),
  executeDischarge: (data) => httpClient.post('/clinical/discharge/execute', data),
  dischargeSummaries: (patientId) =>
    httpClient.get('/clinical/discharge/summaries', { params: patientId ? { patient_id: patientId } : {} }),
  dischargePdfUrl: (summaryId) =>
    `${httpClient.defaults.baseURL}/clinical/discharge/summaries/${summaryId}/pdf`,

  // Radiology
  radiologyQueue: (status) =>
    httpClient.get('/clinical/radiology/orders', { params: status ? { status } : {} }),
  orderImaging: (consultationId, data) =>
    httpClient.post(`/clinical/radiology/consultations/${consultationId}/orders`, data),
  updateRadiologyOrder: (orderId, data) =>
    httpClient.patch(`/clinical/radiology/orders/${orderId}`, data),
  submitRadiologyReport: (orderId, data) =>
    httpClient.post(`/clinical/radiology/orders/${orderId}/report`, data),
  validateRadiologyResult: (resultId) =>
    httpClient.post(`/clinical/radiology/results/${resultId}/validate`),

  // Reminders / notifications
  reminderNotifications: () => httpClient.get('/clinical/reminders/notifications'),
  respondToReminder: (appointmentId, data) =>
    httpClient.post(`/clinical/reminders/appointments/${appointmentId}/respond`, data),
};

export default clinicalApi;
