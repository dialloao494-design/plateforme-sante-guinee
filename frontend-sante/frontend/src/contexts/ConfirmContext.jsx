import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

const ConfirmContext = createContext(null);

export function ConfirmProvider({ children }) {
  const [request, setRequest] = useState(null);
  const cancelButtonRef = useRef(null);
  const dialogRef = useRef(null);
  const resolverRef = useRef(null);

  const confirm = useCallback((options) => new Promise((resolve) => {
    resolverRef.current?.(false);
    resolverRef.current = resolve;
    setRequest({
      title: 'Confirmer cette action', message: '', confirmLabel: 'Confirmer',
      cancelLabel: 'Annuler', tone: 'danger', ...options,
    });
  }), []);

  const finish = useCallback((accepted) => {
    resolverRef.current?.(accepted);
    resolverRef.current = null;
    setRequest(null);
  }, []);

  useEffect(() => {
    if (!request) return undefined;
    const previousFocus = document.activeElement;
    cancelButtonRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === 'Escape') finish(false);
      if (event.key === 'Tab') {
        const controls = [...(dialogRef.current?.querySelectorAll('button') || [])];
        const first = controls[0];
        const last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first?.focus();
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      previousFocus?.focus?.();
    };
  }, [finish, request]);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {request && (
        <div className="app-confirm-backdrop">
          <section ref={dialogRef} className="app-confirm" role="alertdialog" aria-modal="true" aria-labelledby="app-confirm-title" aria-describedby="app-confirm-message">
            <span className={`app-confirm__mark app-confirm__mark--${request.tone}`} aria-hidden="true">!</span>
            <div>
              <h2 id="app-confirm-title">{request.title}</h2>
              <p id="app-confirm-message">{request.message}</p>
            </div>
            <div className="app-confirm__actions">
              <button ref={cancelButtonRef} type="button" className="clinical-btn clinical-btn--secondary" onClick={() => finish(false)}>{request.cancelLabel}</button>
              <button type="button" className="clinical-btn clinical-btn--danger" onClick={() => finish(true)}>{request.confirmLabel}</button>
            </div>
          </section>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

/* eslint-disable react-refresh/only-export-components */
export function useConfirm() {
  const confirm = useContext(ConfirmContext);
  if (!confirm) throw new Error('useConfirm must be used within ConfirmProvider');
  return confirm;
}
/* eslint-enable react-refresh/only-export-components */
