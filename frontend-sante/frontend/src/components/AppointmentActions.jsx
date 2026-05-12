const AppointmentActions = ({
  actions,
  appointment,
  onPay,
  onConfirm,
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
    confirm: onConfirm,
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
        const isLoadingConfirm = action.kind === 'confirm' && isPaying;
        let buttonClassName = 'button-secondary';
        if (action.kind === 'pay' || action.kind === 'confirm') {
          buttonClassName = 'button-pay';
        } else if (action.kind === 'cancel') {
          buttonClassName = 'delete-btn';
        } else if (action.kind === 'join') {
          buttonClassName = 'button-secondary join-consultation-btn';
        }

        const isBusy = isLoadingPay || isLoadingCancel || isLoadingConfirm;

        return (
          <button
            key={action.key}
            type="button"
            onClick={() => handler?.(appointment)}
            disabled={isBusy}
            className={buttonClassName}
          >
            {isLoadingPay && action.kind === 'pay'
              ? 'Traitement...'
              : isLoadingConfirm && action.kind === 'confirm'
                ? 'Confirmation...'
                : isLoadingCancel
                  ? 'Annulation...'
                  : action.label}
          </button>
        );
      })}
      {actions.some((action) => action.kind === 'pay') && <small className="payment-helper-text">Simulation de paiement</small>}
    </div>
  );
};

export default AppointmentActions;