const AppointmentActions = ({
  actions,
  appointment,
  onPay,
  onCancel,
  onOpenMessages,
  onJoinConsultation,
  isPaying = false,
  isCancelling = false,
}) => {
  if (!Array.isArray(actions) || actions.length === 0) {
    return null;
  }

  const handlers = {
    pay: onPay,
    cancel: onCancel,
    message: onOpenMessages,
    join: onJoinConsultation,
  };

  return (
    <div className="appointment-card-actions">
      {actions.map((action) => {
        const handler = handlers[action.kind];
        const isLoadingPay = action.kind === 'pay' && isPaying;
        const isLoadingCancel = action.kind === 'cancel' && isCancelling;
        const buttonClassName =
          action.kind === 'pay'
            ? 'button-pay'
            : action.kind === 'cancel'
              ? 'delete-btn'
              : action.kind === 'join'
                ? 'button-secondary join-consultation-btn'
                : 'button-secondary';

        return (
          <button
            key={action.key}
            type="button"
            onClick={() => handler?.(appointment)}
            disabled={isLoadingPay || isLoadingCancel}
            className={buttonClassName}
          >
            {isLoadingPay ? 'Traitement...' : isLoadingCancel ? 'Annulation...' : action.label}
          </button>
        );
      })}
      {actions.some((action) => action.kind === 'pay') && <small className="payment-helper-text">Simulation de paiement</small>}
    </div>
  );
};

export default AppointmentActions;