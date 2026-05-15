const normalizeStatus = (statusValue) => {
  const normalized = String(statusValue || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

  if (normalized === 'annule' || normalized === 'annulee' || normalized === 'canceled' || normalized === 'cancelled')
    return 'cancelled';
  if (normalized === 'expire' || normalized === 'expired') return 'expired';
  if (normalized === 'checked_in' || normalized === 'checked in' || normalized === 'present') return 'checked_in';
  if (normalized === 'active' || normalized === 'in_progress' || normalized === 'en cours') return 'active';
  if (normalized === 'termine' || normalized === 'completed' || normalized === 'done') return 'completed';
  if (normalized === 'confirme' || normalized === 'confirmee' || normalized === 'confirmed') return 'confirmed';
  if (normalized === 'paid' || normalized === 'paye' || normalized === 'payee') return 'paid';
  if (normalized === 'pending' || normalized === 'en attente') return 'pending';
  return normalized;
};

const normalizePaymentStatus = (paymentStatus) => {
  const normalized = String(paymentStatus || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

  if (normalized === 'paid' || normalized === 'paye' || normalized === 'payee') return 'paid';
  if (normalized === 'unpaid' || normalized === 'non paye') return 'unpaid';
  if (normalized === 'pending' || normalized === 'en attente') return 'pending';
  return normalized;
};

const STATUS_LABELS = {
  pending: 'En attente',
  confirmed: 'Confirmé',
  completed: 'Terminé',
  cancelled: 'Annulé',
  expired: 'Expiré',
  checked_in: 'Présent',
  active: 'En consultation',
  paid: 'Payé',
};

const PAYMENT_LABELS = {
  paid: 'Payé',
  unpaid: 'Non payé',
  pending: 'En attente',
};

const STATUS_COLORS = {
  pending: 'status-badge status-pending',
  confirmed: 'status-badge status-confirmed',
  completed: 'status-badge status-confirmed',
  cancelled: 'status-badge status-cancelled',
  expired: 'status-badge status-cancelled',
  checked_in: 'status-badge status-confirmed',
  active: 'status-badge status-confirmed',
  paid: 'status-badge status-paid',
};

const CONSULTATION_LABELS = {
  teleconsultation: 'Téléconsultation',
  physical: 'Consultation physique',
};

const resolveDisplayStatus = (status, paymentStatus) => {
  if (status === 'cancelled') {
    return 'cancelled';
  }
  if (status === 'expired') {
    return 'expired';
  }

  if (paymentStatus === 'paid' && status === 'pending') {
    return 'confirmed';
  }

  if (status === 'completed') {
    return 'completed';
  }

  if (STATUS_LABELS[status]) {
    return status;
  }

  return 'pending';
};

const resolveConsultationType = (appointment) => {
  if (typeof appointment === 'string') {
    return appointment;
  }
  return appointment?.consultation_type;
};

const resolvePaymentStatusInput = (appointmentOrPaymentStatus) => {
  if (appointmentOrPaymentStatus && typeof appointmentOrPaymentStatus === 'object') {
    return appointmentOrPaymentStatus.payment_status;
  }
  return appointmentOrPaymentStatus;
};

const resolveAppointmentState = (appointment = {}) => {
  const rawStatus = appointment?.status;
  const rawPaymentStatus = appointment?.payment_status;
  const status = normalizeStatus(rawStatus);
  const paymentStatus = normalizePaymentStatus(rawPaymentStatus);
  const displayStatusKey = resolveDisplayStatus(status, paymentStatus);
  const isJoinEligibleStatus =
    status === 'confirmed' || status === 'completed' || status === 'checked_in' || status === 'active';
  const isTeleconsultation = appointment?.consultation_type === 'teleconsultation';

  const finalState =
    status === 'cancelled' || status === 'expired'
      ? 'cancelled'
      : isJoinEligibleStatus
        ? 'confirmed'
        : 'pending';

  const resolved = {
    canPay: status === 'pending' && paymentStatus !== 'paid',
    canCancel: status === 'pending' && paymentStatus !== 'paid',
    /* In-app room is available for confirmed teleconsultations; external link is optional */
    canJoin: isJoinEligibleStatus && isTeleconsultation,
    hasExternalMeetingLink: Boolean(appointment?.meeting_link),
    canMessage: finalState !== 'cancelled',
    displayStatus: STATUS_LABELS[displayStatusKey],
    paymentLabel:
      paymentStatus === 'paid'
        ? PAYMENT_LABELS.paid
        : paymentStatus === 'pending'
          ? PAYMENT_LABELS.pending
          : PAYMENT_LABELS.unpaid,
    statusColor: STATUS_COLORS[displayStatusKey] || STATUS_COLORS.pending,

    state: finalState,
    isCancelled: finalState === 'cancelled',
    isConfirmed: finalState === 'confirmed',
    isPending: finalState === 'pending',
    consultationLabel: CONSULTATION_LABELS[appointment?.consultation_type] || 'Consultation',
  };

  return resolved;
};

export const getAppointmentState = (appointment) => resolveAppointmentState(appointment);

/** Raw workflow status from API (lowercased canonical token). */
export const normalizeAppointmentStatus = (appointment) => normalizeStatus(appointment?.status);

/** Appointments visible on the doctor queue (excludes cancelled, expired, completed). */
export const isDoctorQueueAppointment = (appointment) => {
  const raw = normalizeAppointmentStatus(appointment);
  if (raw === 'cancelled' || raw === 'expired' || raw === 'completed') return false;
  return true;
};
export const getAppointmentStatusLabel = (appointment) => resolveAppointmentState(appointment).displayStatus;
export const getAppointmentStatusColor = (appointment) => resolveAppointmentState(appointment).statusColor;
export const getPaymentLabel = (appointmentOrPaymentStatus) => {
  const paymentStatus = normalizePaymentStatus(resolvePaymentStatusInput(appointmentOrPaymentStatus));
  if (paymentStatus === 'paid') return PAYMENT_LABELS.paid;
  if (paymentStatus === 'pending') return PAYMENT_LABELS.pending;
  return PAYMENT_LABELS.unpaid;
};
export const getConsultationTypeLabel = (appointmentOrConsultationType) => {
  const consultationType = resolveConsultationType(appointmentOrConsultationType);
  return CONSULTATION_LABELS[consultationType] || 'Consultation';
};
export const canJoinConsultation = (appointment) => resolveAppointmentState(appointment).canJoin;
export const canPayAppointment = (appointment) => resolveAppointmentState(appointment).canPay;
export const canCancelAppointment = (appointment) => resolveAppointmentState(appointment).canCancel;
export const canMessageAppointment = (appointment) => resolveAppointmentState(appointment).canMessage;
export const isCancelledAppointment = (appointment) => resolveAppointmentState(appointment).isCancelled;
export const isConfirmedAppointment = (appointment) => resolveAppointmentState(appointment).isConfirmed;
export const isPendingAppointment = (appointment) => resolveAppointmentState(appointment).isPending;

export const formatGNF = (amount) => {
  const value = Number(amount || 0);
  return `${new Intl.NumberFormat('fr-FR').format(value)} GNF`;
};

export const getBackendAppointmentId = (appointment) => {
  const rawId = appointment?.id;
  const numericId = Number(rawId);
  return Number.isInteger(numericId) && numericId > 0 ? numericId : null;
};

export const getStatusMeta = (appointment) => {
  const resolved = resolveAppointmentState(appointment);
  return { label: resolved.displayStatus, className: resolved.statusColor };
};

export const getAppointmentActions = (appointment, options = {}) => {
  const resolved = resolveAppointmentState(appointment);
  const viewerRole = String(options.viewerRole || 'patient').toLowerCase();
  const isDoctorLike = viewerRole === 'doctor' || viewerRole === 'admin';
  const paymentStatus = normalizePaymentStatus(appointment?.payment_status);

  if (['cancelled', 'expired'].includes(normalizeStatus(appointment?.status))) {
    return [];
  }

  if (resolved.canJoin) {
    const actions = [
      {
        key: 'join',
        kind: 'join',
        label: resolved.hasExternalMeetingLink ? 'Rejoindre la consultation' : 'Ouvrir la salle de téléconsultation',
      },
    ];
    if (isDoctorLike) {
      actions.push({ key: 'message', kind: 'message', label: 'Messages' });
    }
    return actions;
  }

  if (isDoctorLike && resolved.state === 'pending') {
    const actions = [];
    if (paymentStatus === 'paid') {
      actions.push({ key: 'confirm', kind: 'confirm', label: 'Confirmer le rendez-vous' });
    }
    actions.push({ key: 'message', kind: 'message', label: 'Messages' });
    return actions;
  }

  if (!resolved.canPay && resolved.state === 'pending') {
    return [{ key: 'message', kind: 'message', label: 'Messages' }];
  }

  if (resolved.state === 'pending') {
    const actions = [];
    if (resolved.canPay) {
      actions.push({ key: 'pay', kind: 'pay', label: 'Payer via Mobile Money' });
    }
    if (resolved.canCancel) {
      actions.push({ key: 'cancel', kind: 'cancel', label: 'Annuler' });
    }
    actions.push({ key: 'message', kind: 'message', label: 'Messages' });
    return actions;
  }

  return [];
};

export const getConsultationTypeBadgeClass = (consultationType) => {
  return consultationType === 'teleconsultation' ? 'consultation-type-tele' : 'consultation-type-physical';
};