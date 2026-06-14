import {
  formatGNF,
  getConsultationTypeLabel,
  getConsultationTypeBadgeClass,
  getAppointmentActions,
} from '../utils/appointmentPresentation.js';
import AppointmentActions from './AppointmentActions.jsx';
import './AppointmentCard.css';

const AppointmentCard = ({
  appointment,
  title,
  onPay,
  onConfirm,
  onCancel,
  onOpenMessages,
  onJoinConsultation,
  presentation,
  actions,
  isPaying,
  isCancelling,
}) => {
  const resolvedActions = Array.isArray(actions) ? actions : getAppointmentActions(appointment);

  return (
    <li className="appointment-card">
      <div className="appointment-card-info">
        <p className="appointment-card-title">{title}</p>
        <div className="consultation-type-row">
          <span
            className={`consultation-type-badge ${getConsultationTypeBadgeClass(
              appointment?.consultation_type
            )}`}
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
          <span className="appointment-card-label">Prix indicatif</span>
          <span className="appointment-card-value">{formatGNF(appointment.price)}</span>
        </p>
        <p>
          <span className="appointment-card-label">Statut</span>
          <span className={presentation.statusColor}>{presentation.displayStatus}</span>
        </p>

      </div>

      <AppointmentActions
        actions={resolvedActions}
        appointment={appointment}
        onPay={onPay}
        onConfirm={onConfirm}
        onCancel={onCancel}
        onOpenMessages={onOpenMessages}
        onJoinConsultation={onJoinConsultation}
        isPaying={isPaying}
        isCancelling={isCancelling}
      />
    </li>
  );
};

export default AppointmentCard;
