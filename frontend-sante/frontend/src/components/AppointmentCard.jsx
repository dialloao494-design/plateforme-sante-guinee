import {
  canPayAppointment,
  formatGNF,
  getConsultationTypeLabel,
  getPaymentLabel,
  getStatusMeta,
  isPendingAppointment,
} from '../utils/appointmentPresentation.js';
import './AppointmentCard.css';

const AppointmentCard = ({
  appointment,
  title,
  onPay,
  onCancel,
  onOpenMessages,
  onJoinConsultation,
  canPay,
  canCancel,
  canMessage,
  isPaying,
  isCancelling,
}) => {
  const statusMeta = getStatusMeta(appointment);
  const isPending = isPendingAppointment(appointment);
  const showPay = isPending && (canPay ?? canPayAppointment(appointment));
  const showCancel = isPending && Boolean(canCancel);
  const showMessage = isPending && Boolean(canMessage);
  const showJoinConsultation =
    appointment?.consultation_type === 'teleconsultation' && Boolean(appointment?.meeting_link);
  const hasActions = showPay || showCancel || showMessage || showJoinConsultation;

  return (
    <li className="appointment-card">
      <div className="appointment-card-info">
        <p className="appointment-card-title">{title}</p>
        <div className="consultation-type-row">
          <span
            className={`consultation-type-badge ${
              appointment?.consultation_type === 'teleconsultation'
                ? 'consultation-type-tele'
                : 'consultation-type-physical'
            }`}
          >
            {getConsultationTypeLabel(appointment?.consultation_type)}
          </span>
        </div>
        <p>
          <span className="appointment-card-label">Date</span>
          <span className="appointment-card-value">{new Date(appointment.date).toLocaleString('fr-FR')}</span>
        </p>
        <p>
          <span className="appointment-card-label">Durée</span>
          <span className="appointment-card-value">{appointment.duration_minutes} minutes</span>
        </p>
        <p>
          <span className="appointment-card-label">Prix</span>
          <span className="appointment-card-value">{formatGNF(appointment.price)}</span>
        </p>
        <p>
          <span className="appointment-card-label">Paiement</span>
          <span className="appointment-card-value">{getPaymentLabel(appointment.payment_status)}</span>
        </p>
        <p>
          <span className="appointment-card-label">Statut</span>
          <span className={statusMeta.className}>{statusMeta.label}</span>
        </p>
      </div>

      {hasActions && (
        <div className="appointment-card-actions">
          {showPay && (
          <>
            <button type="button" onClick={() => onPay(appointment)} disabled={isPaying} className="button-pay">
              {isPaying ? 'Traitement...' : 'Payer via Mobile Money'}
            </button>
            <small className="payment-helper-text">Simulation de paiement</small>
          </>
          )}
          {showCancel && (
            <button type="button" onClick={() => onCancel(appointment)} disabled={isCancelling} className="delete-btn">
              {isCancelling ? 'Annulation...' : 'Annuler'}
            </button>
          )}
          {showMessage && (
            <button type="button" onClick={() => onOpenMessages(appointment)} className="button-secondary">
              Messages
            </button>
          )}
          {showJoinConsultation && (
            <button type="button" onClick={() => onJoinConsultation?.(appointment)} className="button-secondary join-consultation-btn">
              Rejoindre la consultation
            </button>
          )}
        </div>
      )}
    </li>
  );
};

export default AppointmentCard;
