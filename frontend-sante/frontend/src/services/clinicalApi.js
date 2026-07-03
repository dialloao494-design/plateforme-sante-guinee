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
  resetStaffPassword: (userId, data) =>
    httpClient.post(`/clinical/staff/${userId}/reset-password`, data),

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

  // Nurse triage / assessment
  nurseDashboard: () => httpClient.get('/clinical/nurse/dashboard'),
  nurseSearchPatients: (q) => httpClient.get('/clinical/nurse/patients/search', { params: { q } }),
  nurseGetPatient: (patientId) => httpClient.get(`/clinical/nurse/patients/${patientId}`),
  nurseQueueAssessmentsToday: () => httpClient.get('/clinical/nurse/queue/assessments-today'),
  nurseQueuePendingAdmissions: () => httpClient.get('/clinical/nurse/queue/pending-admissions'),
  nurseGetAssessment: (patientId, admissionId) =>
    httpClient.get(`/clinical/nurse/patients/${patientId}/assessment`, {
      params: admissionId ? { admission_id: admissionId } : {},
    }),
  nurseSaveAssessment: (data) => httpClient.post('/clinical/nurse/assessments', data),

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

  // Reception HIS
  receptionHisDashboard: (opts = {}) =>
    cachedGet('/clinical/reception/his/dashboard', {
      cacheTtlMs: 15000,
      forceRefresh: opts.forceRefresh,
    }),
  receptionHisBillingCatalog: () => httpClient.get('/clinical/reception/his/billing-catalog'),
  receptionHisSearch: (q) => httpClient.get('/clinical/reception/his/patients/search', { params: { q } }),
  receptionHisGetPatient: (patientId) => httpClient.get(`/clinical/reception/his/patients/${patientId}`),
  receptionHisCheckDuplicates: (data) =>
    httpClient.post('/clinical/reception/his/patients/check-duplicates', data),
  receptionHisRegister: (data) => {
    invalidateApiCache('/clinical/reception/');
    invalidateApiCache('/clinical/reception/his/');
    return httpClient.post('/clinical/reception/his/patients', data);
  },
  receptionHisCreateAdmission: (data) => {
    invalidateApiCache('/clinical/reception/his/');
    return httpClient.post('/clinical/reception/his/admissions', data);
  },
  receptionHisCreateInvoice: (data) => {
    invalidateApiCache('/clinical/reception/his/');
    invalidateApiCache('/clinical/billing/');
    return httpClient.post('/clinical/reception/his/invoices', data);
  },
  receptionHisListInvoices: (patientId) =>
    httpClient.get('/clinical/reception/his/invoices', {
      params: patientId ? { patient_id: patientId } : {},
    }),
  receptionHisGetInvoice: (id) => httpClient.get(`/clinical/reception/his/invoices/${id}`),
  receptionHisAddPayment: (invoiceId, data) => {
    invalidateApiCache('/clinical/reception/his/');
    invalidateApiCache('/clinical/billing/');
    return httpClient.post(`/clinical/reception/his/invoices/${invoiceId}/payments`, data);
  },
  receptionHisInvoiceReceipt: (invoiceId) =>
    httpClient.get(`/clinical/reception/his/invoices/${invoiceId}/receipt`, { responseType: 'blob' }),
  receptionHisCreateRefund: (data) => {
    invalidateApiCache('/clinical/reception/his/');
    return httpClient.post('/clinical/reception/his/refunds', data);
  },
  receptionHisListRefunds: (patientId) =>
    httpClient.get('/clinical/reception/his/refunds', {
      params: patientId ? { patient_id: patientId } : {},
    }),
  receptionHisUpdateRefund: (id, data) => {
    invalidateApiCache('/clinical/reception/his/');
    return httpClient.patch(`/clinical/reception/his/refunds/${id}`, data);
  },
  receptionHisRefundReceipt: (id) =>
    httpClient.get(`/clinical/reception/his/refunds/${id}/receipt`, { responseType: 'blob' }),
  receptionHisReport: ({ start, end }) =>
    httpClient.get('/clinical/reception/his/reports', { params: { start, end } }),
  receptionHisReportCsv: ({ start, end }) =>
    httpClient.get('/clinical/reception/his/reports/export.csv', { params: { start, end }, responseType: 'blob' }),
  receptionHisReportPdf: ({ start, end }) =>
    httpClient.get('/clinical/reception/his/reports/export.pdf', { params: { start, end }, responseType: 'blob' }),
  receptionHisSearchInvoice: (q, patientId) =>
    httpClient.get('/clinical/reception/his/invoices/search', {
      params: { q, ...(patientId ? { patient_id: patientId } : {}) },
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
  labQueueByStatus: (bucket) => httpClient.get('/clinical/lab/queue/by-status', { params: { bucket } }),
  labServiceRequests: (patientId) => httpClient.get(`/clinical/lab/patients/${patientId}/service-requests`),
  updateLabOrder: (id, data) => httpClient.patch(`/clinical/lab/orders/${id}`, data),
  recordLabResult: (orderId, data) => httpClient.post(`/clinical/lab/orders/${orderId}/results`, data),
  validateLabResult: (resultId) => httpClient.post(`/clinical/lab/results/${resultId}/validate`),

  // Pharmacy
  pharmacyQueue: (opts = {}) =>
    httpClient.get('/clinical/pharmacy/orders', { params: opts.scope ? { scope: opts.scope } : {} }),
  pharmacyPatientSearch: (q) => httpClient.get('/clinical/pharmacy/patients/search', { params: { q } }),
  pharmacyGetPatient: (patientId) => httpClient.get(`/clinical/pharmacy/patients/${patientId}`),
  createPharmacyServiceRequest: (data) => httpClient.post('/clinical/pharmacy/service-requests', data),
  payPharmacyServiceCharge: (chargeId, data) =>
    httpClient.post(`/clinical/pharmacy/charges/${chargeId}/pay`, data),
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
  pharmacyInventorySearch: (q) => httpClient.get('/clinical/pharmacy/inventory/search', { params: { q } }),
  upsertPharmacyInventory: (data) => {
    invalidateApiCache('/clinical/pharmacy/inventory');
    return httpClient.post('/clinical/pharmacy/inventory', data);
  },
  updatePharmacyInventoryItem: (id, data) => {
    invalidateApiCache('/clinical/pharmacy/inventory');
    return httpClient.put(`/clinical/pharmacy/inventory/${id}`, data);
  },
  deletePharmacyInventoryItem: (id) => {
    invalidateApiCache('/clinical/pharmacy/inventory');
    return httpClient.delete(`/clinical/pharmacy/inventory/${id}`);
  },
  adjustPharmacyInventory: (id, data) => httpClient.patch(`/clinical/pharmacy/inventory/${id}`, data),
  addPharmacyChargePayment: (chargeId, data) =>
    httpClient.post(`/clinical/pharmacy/charges/${chargeId}/payments`, data),
  pharmacyChargeReceiptUrl: (chargeId) =>
    `${httpClient.defaults.baseURL}/clinical/pharmacy/charges/${chargeId}/receipt`,

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
  labPatientSearch: (q) => httpClient.get('/clinical/lab/patients/search', { params: { q } }),
  labGetPatient: (patientId) => httpClient.get(`/clinical/lab/patients/${patientId}`),
  updateLabCatalogPrices: (items) => httpClient.patch('/clinical/lab/catalog/prices', { items }),
  createWalkInLabOrders: (data) => httpClient.post('/clinical/lab/walk-in-orders', data),
  labMonthlyReport: (year, month) =>
    httpClient.get('/clinical/lab/reports/monthly', { params: { year, month } }),
  labValidatedResults: (limit = 100) =>
    httpClient.get('/clinical/lab/results/validated', { params: { limit } }),
  pharmacyDashboardStats: () => httpClient.get('/clinical/pharmacy/dashboard'),
  pharmacyMonthlyReport: (year, month) =>
    httpClient.get('/clinical/pharmacy/reports/monthly', { params: { year, month } }),
  doctorMedicineDeliveries: () => httpClient.get('/clinical/pharmacy/doctor-deliveries'),
  createDoctorMedicineDelivery: (data) => httpClient.post('/clinical/pharmacy/doctor-deliveries', data),
};

export default clinicalApi;
