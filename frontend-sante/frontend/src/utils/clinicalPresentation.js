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
