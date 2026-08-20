const AppointmentActions = ({
  actions,
  appointment,
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
    confirm: onConfirm,
    cancel: onCancel,
    message: onOpenMessages,
    join: onJoinConsultation,
  };

  return (
    <div className="appointment-card-actions">
      {actions.map((action) => {
        const handler = handlers[action.kind];
        const isLoadingCancel = action.kind === 'cancel' && isCancelling;
        const isLoadingConfirm = action.kind === 'confirm' && isPaying;
        let buttonClassName = 'button-secondary';
        if (action.kind === 'confirm') {
          buttonClassName = 'button-pay';
        } else if (action.kind === 'cancel') {
          buttonClassName = 'delete-btn';
        } else if (action.kind === 'join') {
          buttonClassName = 'button-secondary join-consultation-btn';
        }

        const isBusy = isLoadingCancel || isLoadingConfirm;

        return (
          <button
            key={action.key}
            type="button"
            onClick={() => handler?.(appointment)}
            disabled={isBusy}
            className={buttonClassName}
          >
            {isLoadingConfirm && action.kind === 'confirm'
              ? 'Confirmation…'
              : isLoadingCancel
                ? 'Annulation…'
                : action.label}
          </button>
        );
      })}
    </div>
  );
};

export default AppointmentActions;
