import httpClient from './httpClient';
import { CACHE_TTL } from '../utils/apiCache.js';
import { cachedGet, invalidateApiCache } from '../utils/cachedHttp.js';

const clinicalApi = {
  operationsSummary: (opts = {}) =>
    cachedGet('/clinical/operations/summary', {
      cacheTtlMs: CACHE_TTL.operationsSummary,
      forceRefresh: opts.forceRefresh,
    }),

  // Admin
  createClinic: (data) => {
    invalidateApiCache('/clinical/clinics');
    return httpClient.post('/clinical/clinics', data);
  },
  listClinics: (opts = {}) =>
    cachedGet('/clinical/clinics', {
      cacheTtlMs: CACHE_TTL.clinicConfig,
      cachePersist: true,
      forceRefresh: opts.forceRefresh,
    }),
  createStaff: (data) => httpClient.post('/clinical/staff', data),
  listStaff: (clinicId, role) =>
    httpClient.get('/clinical/staff', {
      params: { clinic_id: clinicId, ...(role ? { role } : {}) },
    }),
  updateStaffRole: (userId, data) => httpClient.patch(`/clinical/staff/${userId}/role`, data),
  deactivateStaff: (userId, clinicId) =>
    httpClient.patch(`/clinical/staff/${userId}/deactivate`, null, { params: { clinic_id: clinicId } }),

  // Nutrition
  nutritionHistory: (patientId) => httpClient.get(`/clinical/nutrition/patients/${patientId}/history`),
  recordNutritionAssessment: (data) => httpClient.post('/clinical/nutrition/assessments', data),
  nutritionDashboard: () => httpClient.get('/clinical/nutrition/dashboard'),
  nutritionMonthlyReport: (year, month) =>
    httpClient.get('/clinical/nutrition/reports/monthly', { params: { year, month } }),

  // Immunization (PEV)
  immunizationSchedule: (opts = {}) =>
    cachedGet('/clinical/immunization/schedule', {
      cacheTtlMs: CACHE_TTL.immunizationSchedule,
      cachePersist: true,
      forceRefresh: opts.forceRefresh,
    }),
  immunizationFieldOptions: () => httpClient.get('/clinical/immunization/field-options'),
  immunizationHistory: (patientId) => httpClient.get(`/clinical/immunization/patients/${patientId}/history`),
  immunizationStatus: (patientId) => httpClient.get(`/clinical/immunization/patients/${patientId}/status`),
  recordImmunization: (data) => httpClient.post('/clinical/immunization/records', data),
  immunizationDashboard: () => httpClient.get('/clinical/immunization/dashboard'),
  immunizationRegister: (year, month) =>
    httpClient.get('/clinical/immunization/register', { params: { year, month } }),
  immunizationMonthlyReport: (year, month) =>
    httpClient.get('/clinical/immunization/reports/monthly', { params: { year, month } }),

  // Nursing care (Soins)
  nursingDashboard: () => httpClient.get('/clinical/nursing-care/dashboard'),
  nursingMonthlyReport: (year, month) =>
    httpClient.get('/clinical/nursing-care/reports/monthly', { params: { year, month } }),
  nursingProcedures: (procedureDate) =>
    httpClient.get('/clinical/nursing-care/procedures', {
      params: procedureDate ? { procedure_date: procedureDate } : {},
    }),
  recordNursingProcedure: (data) => httpClient.post('/clinical/nursing-care/procedures', data),

  // Visit workflow queues
  startVisit: (data) => {
    invalidateApiCache('/clinical/workflow/');
    return httpClient.post('/clinical/workflow/visits', data);
  },
  workflowQueue: (department, opts = {}) =>
    cachedGet(`/clinical/workflow/queue/${department}`, {
      cacheTtlMs: CACHE_TTL.workflowQueue,
      forceRefresh: opts.forceRefresh,
    }),
  completeWorkflowStep: (workflowId, department) => {
    invalidateApiCache('/clinical/workflow/');
    return httpClient.post(`/clinical/workflow/visits/${workflowId}/complete/${department}`);
  },
  getWorkflowVisit: (workflowId) => httpClient.get(`/clinical/workflow/visits/${workflowId}`),

  // Reception
  intakePatient: (data) => {
    invalidateApiCache('/clinical/reception/');
    invalidateApiCache('/clinical/workflow/');
    return httpClient.post('/clinical/reception/patients', data);
  },
  searchPatients: (q) => httpClient.get('/clinical/reception/patients', { params: { q } }),
  createAppointment: (data) => httpClient.post('/clinical/reception/appointments', data),
  receptionQueue: () => httpClient.get('/clinical/reception/queue'),
  checkIn: (appointmentId) => {
    invalidateApiCache('/clinical/reception/');
    return httpClient.post(`/clinical/reception/appointments/${appointmentId}/check-in`);
  },
  clinicDoctors: (opts = {}) =>
    cachedGet('/clinical/reception/doctors', {
      cacheTtlMs: CACHE_TTL.clinicDoctors,
      forceRefresh: opts.forceRefresh,
    }),

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
  pharmacyQueue: (opts = {}) =>
    httpClient.get('/clinical/pharmacy/orders', { params: opts.scope ? { scope: opts.scope } : {} }),
  updatePharmacyOrder: (id, data) => {
    invalidateApiCache('/clinical/pharmacy/');
    return httpClient.patch(`/clinical/pharmacy/orders/${id}`, data);
  },

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
  hospitalDashboard: () => httpClient.get('/clinical/hospitalization/dashboard'),
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

  // Clinical reporting
  clinicalReportSummary: (params) => httpClient.get('/clinical/reports/summary', { params }),
  clinicalReportRevenue: (params) => httpClient.get('/clinical/reports/revenue', { params }),
  downloadClinicalReportCsv: (params) =>
    httpClient.get('/clinical/reports/export.csv', { params, responseType: 'blob' }),
  downloadClinicalReportPdf: (params, filename) =>
    import('../utils/downloadPdf').then(({ downloadAuthenticatedPdf }) =>
      downloadAuthenticatedPdf('/clinical/reports/export.pdf', filename, params)
    ),

  // Medical history (staff)
  patientMedicalHistory: (patientId) => httpClient.get(`/patients/${patientId}/medical-history`),

  // Pharmacy inventory
  pharmacyInventory: () => httpClient.get('/clinical/pharmacy/inventory'),
  upsertPharmacyInventory: (data) => {
    invalidateApiCache('/clinical/pharmacy/inventory');
    return httpClient.post('/clinical/pharmacy/inventory', data);
  },
  adjustPharmacyInventory: (id, data) => httpClient.patch(`/clinical/pharmacy/inventory/${id}`, data),

  // Bed / room management
  updateHospitalRoom: (roomId, data) => httpClient.patch(`/clinical/hospitalization/rooms/${roomId}`, data),
  updateHospitalBed: (bedId, data) => httpClient.patch(`/clinical/hospitalization/beds/${bedId}`, data),

  // Authenticated PDF downloads
  downloadInvoicePdf: (id, filename) =>
    import('../utils/downloadPdf').then(({ downloadAuthenticatedPdf }) =>
      downloadAuthenticatedPdf(`/clinical/billing/unified/invoices/${id}/pdf`, filename)
    ),
  downloadDischargePdf: (id, filename) =>
    import('../utils/downloadPdf').then(({ downloadAuthenticatedPdf }) =>
      downloadAuthenticatedPdf(`/clinical/discharge/summaries/${id}/pdf`, filename)
    ),
  downloadRadiologyPdf: (resultId, filename) =>
    import('../utils/downloadPdf').then(({ downloadAuthenticatedPdf }) =>
      downloadAuthenticatedPdf(`/clinical/radiology/results/${resultId}/pdf`, filename)
    ),
  downloadLabPdf: (resultId, filename) =>
    import('../utils/downloadPdf').then(({ downloadAuthenticatedPdf }) =>
      downloadAuthenticatedPdf(`/clinical/lab/results/${resultId}/pdf`, filename)
    ),

  // Phase 2 — unified timeline & registers
  patientTimeline: (patientId) => httpClient.get(`/clinical/patients/${patientId}/timeline`),
  kolomaMonthlyReports: (year, month) =>
    httpClient.get('/clinical/reports/koloma/monthly', { params: { year, month } }),
  nursingRegister: (year, month) =>
    httpClient.get('/clinical/nursing-care/register', { params: { year, month } }),
  nutritionRegister: (year, month) =>
    httpClient.get('/clinical/nutrition/register', { params: { year, month } }),
  hospitalizationMonthlyReport: (year, month) =>
    httpClient.get('/clinical/hospitalization/reports/monthly', { params: { year, month } }),
  labDashboardStats: () => httpClient.get('/clinical/lab/dashboard'),
  labCatalog: () => httpClient.get('/clinical/lab/catalog'),
  labMonthlyReport: (year, month) =>
    httpClient.get('/clinical/lab/reports/monthly', { params: { year, month } }),
  labValidatedResults: (limit = 100) =>
    httpClient.get('/clinical/lab/results/validated', { params: { limit } }),
  pharmacyDashboardStats: () => httpClient.get('/clinical/pharmacy/dashboard'),
  pharmacyMonthlyReport: (year, month) =>
    httpClient.get('/clinical/pharmacy/reports/monthly', { params: { year, month } }),
};

export default clinicalApi;
