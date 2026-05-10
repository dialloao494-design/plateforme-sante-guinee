export const STATUS_META = {
  pending: { label: 'En attente', className: 'status-badge status-pending' },
  paid: { label: 'Payé', className: 'status-badge status-paid' },
  confirmed: { label: 'Confirmé', className: 'status-badge status-confirmed' },
  completed: { label: 'Terminé', className: 'status-badge status-confirmed' },
  cancelled: { label: 'Annulé', className: 'status-badge status-cancelled' },
};

const normalizeStatus = (statusValue) => String(statusValue || '').toLowerCase().replace('é', 'e');

const resolveDisplayStatus = (appointmentOrStatus, paymentStatus) => {
  if (appointmentOrStatus && typeof appointmentOrStatus === 'object') {
    const normalizedStatus = normalizeStatus(appointmentOrStatus.status);
    const normalizedPaymentStatus = String(appointmentOrStatus.payment_status || '').toLowerCase();

    if (normalizedStatus === 'cancelled') {
      return 'cancelled';
    }

    if (normalizedPaymentStatus === 'paid') {
      return 'confirmed';
    }

    return normalizedStatus;
  }

  const normalizedStatus = normalizeStatus(appointmentOrStatus);
  const normalizedPaymentStatus = String(paymentStatus || '').toLowerCase();

  if (normalizedStatus === 'cancelled') {
    return 'cancelled';
  }

  if (normalizedPaymentStatus === 'paid') {
    return 'confirmed';
  }

  return normalizedStatus;
};

export const getStatusMeta = (appointmentOrStatus, paymentStatus) => {
  const displayStatus = resolveDisplayStatus(appointmentOrStatus, paymentStatus);
  return STATUS_META[displayStatus] || STATUS_META.pending;
};

export const getPaymentLabel = (paymentStatus) => {
  const normalized = String(paymentStatus || '').toLowerCase();
  if (normalized === 'paid') return 'Payé';
  if (normalized === 'pending') return 'En attente';
  if (normalized === 'unpaid') return 'Non payé';
  return 'En attente';
};

export const getConsultationTypeLabel = (consultationType) => {
  return consultationType === 'teleconsultation' ? 'Téléconsultation' : 'Consultation physique';
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
  return resolveDisplayStatus(appointment) === 'pending';
};

export const canPayAppointment = (appointment) => {
  return isPendingAppointment(appointment);
};
