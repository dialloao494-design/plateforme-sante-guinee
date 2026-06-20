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

  setUserStatus: (userId, isActive) =>
    httpClient.patch(`/platform/users/${userId}/status`, { is_active: isActive }),
};

export default platformApi;
