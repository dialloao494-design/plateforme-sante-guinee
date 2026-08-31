import httpClient from './httpClient';

const platformApi = {
  getSummary: (category = 'production') =>
    httpClient.get('/platform/summary', { params: { category } }),

  listClinicDirectory: (opts = {}) =>
    httpClient.get('/platform/clinics/directory', {
      params: {
        category: opts.category || 'production',
        ...(opts.search ? { search: opts.search } : {}),
      },
    }),

  getClinicDetail: (clinicId) => httpClient.get(`/platform/clinics/${clinicId}/detail`),

  listClinicStaff: (clinicId) => httpClient.get(`/platform/clinics/${clinicId}/staff`),

  setClinicActive: (clinicId, isActive) =>
    httpClient.patch(`/platform/clinics/${clinicId}/active`, { is_active: isActive }),

  resetStaffPassword: (clinicId, userId, newPassword) =>
    httpClient.post(`/platform/clinics/${clinicId}/staff/${userId}/reset-password`, {
      new_password: newPassword,
    }),

  listAccounts: (params = {}) => httpClient.get('/platform/accounts', { params }),
  deactivateStaff: (clinicId, userId, reason) =>
    httpClient.patch(`/platform/clinics/${clinicId}/staff/${userId}/deactivate`, { reason }),
  reactivateStaff: (clinicId, userId, reason) =>
    httpClient.patch(`/platform/clinics/${clinicId}/staff/${userId}/reactivate`, { reason }),
  deleteStaff: (clinicId, userId, reason) =>
    httpClient.delete(`/platform/clinics/${clinicId}/staff/${userId}`, { data: { reason } }),
  revokeStaffSessions: (clinicId, userId, reason) =>
    httpClient.post(`/platform/clinics/${clinicId}/staff/${userId}/sessions/revoke`, { reason }),
  listStaffSessions: (clinicId, userId) =>
    httpClient.get(`/platform/clinics/${clinicId}/staff/${userId}/sessions`),
  sendStaffResetLink: (clinicId, userId, reason) =>
    httpClient.post(`/platform/clinics/${clinicId}/staff/${userId}/password-reset-link`, { reason }),
  bulkAccounts: (data) => httpClient.post('/platform/accounts/bulk', data),
  auditLogs: (params = {}) => httpClient.get('/platform/audit-logs', { params }),
  auditCsvUrl: '/platform/audit-logs/export.csv',
  auditPdfUrl: '/platform/audit-logs/export.pdf',
  updateClinicConfiguration: (clinicId, data) =>
    httpClient.patch(`/platform/clinics/${clinicId}/configuration`, data),
  changeClinicState: (clinicId, data) =>
    httpClient.post(`/platform/clinics/${clinicId}/state`, data),
  clinicHealth: (clinicId) => httpClient.get(`/platform/clinics/${clinicId}/health`),
  clinicDataGovernance: (clinicId) => httpClient.get(`/platform/clinics/${clinicId}/data-governance`),
  resetClinicData: (clinicId, data) => httpClient.post(`/platform/clinics/${clinicId}/data-reset`, data),
  mergePatients: (clinicId, data) => httpClient.post(`/platform/clinics/${clinicId}/patients/merge`, data),
};

export default platformApi;
