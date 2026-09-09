import { toast } from 'react-toastify';

const cleanLabel = (field) => {
  const text = field.labels?.[0]?.textContent || field.getAttribute('aria-label') || field.name;
  return String(text || 'champ requis').replace(/\s+/g, ' ').replace(/\s*\*\s*$/, '').trim();
};

const revealInvalidField = (field) => {
  if (field.form?.querySelector(':invalid') !== field) return;
  field.closest('details:not([open])')?.setAttribute('open', '');
  field.setAttribute('aria-invalid', 'true');
  toast.error(`Envoi non effectué : vérifiez « ${cleanLabel(field)} ».`, {
    toastId: 'form-validation-feedback',
  });
  window.requestAnimationFrame(() => {
    field.scrollIntoView({ behavior: 'smooth', block: 'center' });
    field.focus({ preventScroll: true });
  });
  field.addEventListener('input', () => field.removeAttribute('aria-invalid'), { once: true });
};

const explainDisabledAction = (button) => {
  const label = button.textContent?.replace(/\s+/g, ' ').trim() || 'Cette action';
  const reason = button.dataset.disabledReason
    || `« ${label} » n’est pas disponible dans l’état actuel de cet écran.`;
  toast.info(reason, { toastId: 'disabled-action-feedback' });
};

export function installInteractionFeedback() {
  const onInvalid = (event) => revealInvalidField(event.target);
  const onPointerDown = (event) => {
    const button = event.target.closest?.('button:disabled');
    if (button) explainDisabledAction(button);
  };
  document.addEventListener('invalid', onInvalid, true);
  document.addEventListener('pointerdown', onPointerDown, true);
  return () => {
    document.removeEventListener('invalid', onInvalid, true);
    document.removeEventListener('pointerdown', onPointerDown, true);
  };
}
