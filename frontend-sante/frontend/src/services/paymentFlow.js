import { appointmentsAPI, paymentsAPI } from './api.js';
import { getBackendAppointmentId } from '../utils/appointmentPresentation.js';

export const createCheckoutForAppointment = async (appointment) => {
  const localId = getBackendAppointmentId(appointment);

  if (!localId) {
    throw new Error('Rendez-vous introuvable pour le paiement.');
  }

  // Authoritative source of truth from backend before starting payment.
  const { data: backendAppointment } = await appointmentsAPI.getById(localId);
  const backendId = getBackendAppointmentId(backendAppointment);

  if (!backendId) {
    throw new Error('Rendez-vous introuvable pour le paiement.');
  }

  const { data } = await paymentsAPI.createIntent(backendId);

  if (!data?.checkout_url) {
    throw new Error('Lien de paiement indisponible.');
  }

  return data.checkout_url;
};
