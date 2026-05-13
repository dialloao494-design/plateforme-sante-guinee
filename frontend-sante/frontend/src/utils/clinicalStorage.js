const STORAGE_KEY = 'psg_clinical_summaries_v1';

function safeParse(raw) {
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

export function getAllConsultationSummaries() {
  if (typeof window === 'undefined' || !window.localStorage) return {};
  return safeParse(window.localStorage.getItem(STORAGE_KEY) || '{}');
}

/**
 * @param {number|string} appointmentId
 * @param {number|string} patientId
 * @param {string} text
 */
export function setConsultationSummary(appointmentId, patientId, text) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  const all = getAllConsultationSummaries();
  const key = String(appointmentId);
  all[key] = {
    appointmentId: Number(appointmentId),
    patientId: Number(patientId),
    text: String(text || '').trim(),
    savedAt: new Date().toISOString(),
  };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

/** @param {number|string} appointmentId */
export function getConsultationSummary(appointmentId) {
  return getAllConsultationSummaries()[String(appointmentId)] || null;
}
