const normalizeStatus = (statusValue) => {
  const normalized = String(statusValue || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

  if (normalized === 'annule' || normalized === 'annulee' || normalized === 'canceled' || normalized === 'cancelled')
    return 'cancelled';
  if (normalized === 'checked_in' || normalized === 'checked in' || normalized === 'present') return 'checked_in';
  if (normalized === 'active' || normalized === 'in_progress' || normalized === 'in_consultation' || normalized === 'en cours')
    return 'checked_in';
  if (normalized === 'termine' || normalized === 'completed' || normalized === 'done') return 'completed';
  if (normalized === 'confirme' || normalized === 'confirmee' || normalized === 'confirmed') return 'confirmed';
  if (normalized === 'paid' || normalized === 'paye' || normalized === 'payee') return 'confirmed';
  if (normalized === 'pending' || normalized === 'en attente') return 'pending';
  return normalized;
};

const STATUS_LABELS = {
  pending: 'En attente',
  confirmed: 'Confirmé',
  checked_in: 'Présent',
  completed: 'Terminé',
  cancelled: 'Annulé',
};

const STATUS_COLORS = {
  pending: 'status-badge status-pending',
  confirmed: 'status-badge status-confirmed',
  checked_in: 'status-badge status-confirmed',
  completed: 'status-badge status-confirmed',
  cancelled: 'status-badge status-cancelled',
};

const CONSULTATION_LABELS = {
  teleconsultation: 'Téléconsultation',
  physical: 'Consultation physique',
};

const ACTIVE_STATUSES = new Set(['confirmed', 'checked_in']);

const resolveAppointmentState = (appointment = {}) => {
  const status = normalizeStatus(appointment?.status);
  const isTeleconsultation = appointment?.consultation_type === 'teleconsultation';
  const displayStatusKey = STATUS_LABELS[status] ? status : 'pending';

  const isCancelled = status === 'cancelled';
  const isCompleted = status === 'completed';
  const isPending = status === 'pending';
  const isActive = ACTIVE_STATUSES.has(status);

  return {
    canPay: false,
    canCancel: isPending || status === 'confirmed',
    canJoin: isActive && isTeleconsultation && !isCancelled && !isCompleted,
    hasExternalMeetingLink: isActive && isTeleconsultation,
    canMessage: !isCancelled,
    displayStatus: STATUS_LABELS[displayStatusKey] || STATUS_LABELS.pending,
    statusColor: STATUS_COLORS[displayStatusKey] || STATUS_COLORS.pending,
    state: isCancelled ? 'cancelled' : isCompleted ? 'completed' : isActive ? 'confirmed' : 'pending',
    isCancelled,
    isConfirmed: isActive,
    isPending,
    consultationLabel: CONSULTATION_LABELS[appointment?.consultation_type] || 'Consultation',
  };
};

export const getAppointmentState = (appointment) => resolveAppointmentState(appointment);

export const normalizeAppointmentStatus = (appointment) => normalizeStatus(appointment?.status);

export const isDoctorQueueAppointment = (appointment) => {
  const raw = normalizeAppointmentStatus(appointment);
  return raw !== 'cancelled' && raw !== 'completed';
};

export const getAppointmentStatusLabel = (appointment) => resolveAppointmentState(appointment).displayStatus;
export const getAppointmentStatusColor = (appointment) => resolveAppointmentState(appointment).statusColor;
export const getConsultationTypeLabel = (appointmentOrConsultationType) => {
  const consultationType =
    typeof appointmentOrConsultationType === 'string'
      ? appointmentOrConsultationType
      : appointmentOrConsultationType?.consultation_type;
  return CONSULTATION_LABELS[consultationType] || 'Consultation';
};
export const canJoinConsultation = (appointment) => resolveAppointmentState(appointment).canJoin;
export const canPayAppointment = () => false;
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
  const status = normalizeStatus(appointment?.status);

  if (status === 'cancelled' || status === 'completed') {
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

  if (isDoctorLike && status === 'pending') {
    return [
      { key: 'confirm', kind: 'confirm', label: 'Confirmer le rendez-vous' },
      { key: 'message', kind: 'message', label: 'Messages' },
    ];
  }

  const actions = [];
  if (resolved.canCancel) {
    actions.push({ key: 'cancel', kind: 'cancel', label: 'Annuler' });
  }
  actions.push({ key: 'message', kind: 'message', label: 'Messages' });
  return actions;
};

export const getConsultationTypeBadgeClass = (consultationType) => {
  return consultationType === 'teleconsultation' ? 'consultation-type-tele' : 'consultation-type-physical';
};

/** @deprecated Payment removed from patient portal */
export const getPaymentLabel = () => '—';
