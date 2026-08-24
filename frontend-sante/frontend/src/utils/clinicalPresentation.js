const LOCALE = 'fr-GN';

const currencyFormatter = new Intl.NumberFormat(LOCALE, {
  style: 'currency',
  currency: 'GNF',
  currencyDisplay: 'code',
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium' });
const dateTimeFormatter = new Intl.DateTimeFormat(LOCALE, {
  dateStyle: 'medium',
  timeStyle: 'short',
});
const timeFormatter = new Intl.DateTimeFormat(LOCALE, {
  hour: '2-digit',
  minute: '2-digit',
});

function validDate(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatClinicalDate(value, fallback = '—') {
  const date = validDate(value);
  return date ? dateFormatter.format(date) : fallback;
}

export function formatClinicalDateTime(value, fallback = '—') {
  const date = validDate(value);
  return date ? dateTimeFormatter.format(date) : fallback;
}

export function formatClinicalTime(value, fallback = '—') {
  const date = validDate(value);
  return date ? timeFormatter.format(date) : fallback;
}

export function formatGNF(value, fallback = '0 GNF') {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return fallback;
  return currencyFormatter.format(amount).replace(/\s?GNF/, ' GNF');
}

export function patientDisplayName(patient, fallback = 'Identité non renseignée') {
  return patient?.full_name
    || patient?.patient_name
    || [patient?.last_name, patient?.first_name].filter(Boolean).join(' ')
    || fallback;
}

export function patientAge(patient, fallback = '—', now = new Date()) {
  if (patient?.age != null && patient.age !== '') return String(patient.age);
  const birthDate = validDate(patient?.date_of_birth);
  if (!birthDate) return fallback;
  let age = now.getFullYear() - birthDate.getFullYear();
  const monthDifference = now.getMonth() - birthDate.getMonth();
  if (monthDifference < 0 || (monthDifference === 0 && now.getDate() < birthDate.getDate())) age -= 1;
  return age >= 0 ? String(age) : fallback;
}

export function patientGenderLabel(value, fallback = '—') {
  const normalized = String(value || '').toLowerCase();
  if (normalized === 'f' || normalized === 'female' || normalized === 'féminin') return 'Féminin';
  if (normalized === 'm' || normalized === 'male' || normalized === 'masculin') return 'Masculin';
  if (normalized === 'autre' || normalized === 'other') return 'Autre';
  return value || fallback;
}

export function patientAddress(patient, fallback = '—') {
  const parts = [patient?.address || patient?.quartier, patient?.city, patient?.region].filter(Boolean);
  return parts.join(', ') || fallback;
}

const CLINICAL_STATUS_LABELS = {
  ordered: 'Commandé', pending: 'En attente', sample_collected: 'Prélèvement effectué',
  in_sampling: 'En prélèvement', in_analysis: 'En analyse', in_progress: 'En cours',
  completed: 'Terminé', validated: 'Validé', rejected: 'Rejeté', cancelled: 'Annulé',
  issued: 'Émise', paid: 'Payé', unpaid: 'Impayé', partially_paid: 'Partiellement payé',
};

export function formatClinicalStatus(value, fallback = '—') {
  if (!value) return fallback;
  return CLINICAL_STATUS_LABELS[String(value).toLowerCase()] || String(value);
}
