import { formatGNF } from '../utils/appointmentPresentation.js';
import { PAYMENT_CHANNELS, getPaymentReadinessSummary } from '../config/paymentChannels.js';
import './PaymentConfirmationModal.css';

const PaymentConfirmationModal = ({ isOpen, appointment, onConfirm, onClose, isProcessing }) => {
  if (!isOpen || !appointment) {
    return null;
  }

  const paySummary = getPaymentReadinessSummary();

  return (
    <div className="payment-modal-overlay" role="presentation" onClick={onClose}>
      <div className="payment-modal" role="dialog" aria-modal="true" aria-labelledby="payment-modal-title" onClick={(e) => e.stopPropagation()}>
        <h2 id="payment-modal-title">Confirmer le paiement</h2>
        <p className="payment-modal-helper">
          Simulation Mobile Money — {paySummary.headline}. {paySummary.sub}
        </p>

        <ul className="payment-modal-channels" aria-label="Canaux prévus">
          {PAYMENT_CHANNELS.map((ch) => (
            <li key={ch.id}>
              <strong>{ch.label}</strong> <span className={`payment-modal-status payment-modal-status--${ch.status}`}>{ch.status}</span>
              <span className="payment-modal-channel-desc">{ch.description}</span>
            </li>
          ))}
        </ul>

        <div className="payment-modal-details">
          <p><span>Montant</span> {formatGNF(appointment.price)}</p>
          <p><span>Date</span> {new Date(appointment.date).toLocaleString('fr-FR')}</p>
        </div>

        <div className="payment-modal-actions">
          <button type="button" className="button-secondary" onClick={onClose} disabled={isProcessing}>
            Annuler
          </button>
          <button type="button" className="button-pay" onClick={() => onConfirm(appointment)} disabled={isProcessing}>
            {isProcessing ? 'Traitement...' : 'Confirmer le paiement'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PaymentConfirmationModal;
