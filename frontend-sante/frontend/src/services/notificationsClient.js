/**
 * Client stub for future SMS / push reminders (appointment, téléconsultation, no-show).
 * Backend: /notifications/channels exposes capability flags.
 */

import httpClient from './httpClient.js';

export async function fetchNotificationChannels() {
  try {
    const { data } = await httpClient.get('/notifications/channels');
    return data;
  } catch {
    return { channels: [], enabled: false };
  }
}

export const REMINDER_COPY = {
  appointment24h: 'Rappel J-1 (SMS / WhatsApp Business — bientôt)',
  teleconsult15m: 'Rappel 15 min avant la téléconsultation',
  noShow: 'Relance patient en cas d’absence signalée',
};
