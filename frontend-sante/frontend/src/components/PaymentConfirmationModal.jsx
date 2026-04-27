import { formatGNF } from '../utils/appointmentPresentation.js';
import './PaymentConfirmationModal.css';

const PaymentConfirmationModal = ({ isOpen, appointment, onConfirm, onClose, isProcessing }) => {
  if (!isOpen || !appointment) {
    return null;
  }

  return (
    <div className="payment-modal-overlay" role="presentation" onClick={onClose}>
      <div className="payment-modal" role="dialog" aria-modal="true" aria-labelledby="payment-modal-title" onClick={(e) => e.stopPropagation()}>
        <h2 id="payment-modal-title">Confirmer le paiement</h2>
        <p className="payment-modal-helper">Simulation de paiement Mobile Money</p>

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
