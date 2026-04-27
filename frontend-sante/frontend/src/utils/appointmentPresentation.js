export const STATUS_META = {
  pending: { label: 'En attente', className: 'status-badge status-pending' },
  paid: { label: 'Payé', className: 'status-badge status-paid' },
  confirmed: { label: 'Confirmé', className: 'status-badge status-confirmed' },
  completed: { label: 'Terminé', className: 'status-badge status-confirmed' },
  cancelled: { label: 'Annulé', className: 'status-badge status-cancelled' },
};

export const getStatusMeta = (statusValue) => {
  const normalized = String(statusValue || '').toLowerCase().replace('é', 'e');
  return STATUS_META[normalized] || STATUS_META.pending;
};

export const getPaymentLabel = (paymentStatus) => {
  const normalized = String(paymentStatus || '').toLowerCase();
  if (normalized === 'paid') return 'Payé';
  if (normalized === 'pending') return 'En attente';
  if (normalized === 'unpaid') return 'Payer';
  return 'En attente';
};

export const formatGNF = (amount) => {
  const value = Number(amount || 0);
  return `${new Intl.NumberFormat('fr-FR').format(value)} GNF`;
};

export const getBackendAppointmentId = (appointment) => {
  const rawId = appointment?.id;
  const numericId = Number(rawId);
  return Number.isInteger(numericId) && numericId > 0 ? numericId : null;
};

export const isPendingAppointment = (appointment) => {
  const normalizedStatus = String(appointment?.status || '').toLowerCase().replace('é', 'e');
  return normalizedStatus === 'pending';
};

export const canPayAppointment = (appointment) => {
  return isPendingAppointment(appointment);
};
