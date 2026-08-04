import { formatGNF } from '../../../utils/appointmentPresentation.js';
import { SERVICE_REQUEST_CATEGORIES, SERVICE_REQUEST_STATUSES } from './constants.js';

export const serviceRequestStatusLabel = (status) =>
  SERVICE_REQUEST_STATUSES.find((s) => s.value === status)?.label || status || '—';

export const serviceRequestCategoryLabel = (cat) =>
  SERVICE_REQUEST_CATEGORIES.find((c) => c.value === cat)?.label || cat || '—';

export const formatDateTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return String(value);
  }
};

export const calcAge = (dob) => {
  if (!dob) return '';
  const b = new Date(dob);
  if (Number.isNaN(b.getTime())) return '';
  const n = new Date();
  let age = n.getFullYear() - b.getFullYear();
  const m = n.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && n.getDate() < b.getDate())) age -= 1;
  return age >= 0 ? age : '';
};

export const qrImageUrl = (token) =>
  token ? `https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(token)}` : '';

export const refundStatusLabel = (status) => {
  if (status === 'pending') return 'Demandé';
  if (status === 'approved') return 'Approuvé';
  if (status === 'paid') return 'Payé';
  if (status === 'rejected') return 'Rejeté';
  return status || '—';
};

export const invoiceStatusLabel = (status) => {
  if (status === 'paid') return 'Payée';
  if (status === 'partially_paid') return 'Partiellement payée';
  if (status === 'unpaid') return 'Impayée';
  return status || '—';
};

export const methodLabel = (methods, value) => methods.find((m) => m.value === value)?.label || value || '—';

export const genderLabel = (gender) => {
  if (gender === 'F') return 'Féminin';
  if (gender === 'M') return 'Masculin';
  if (gender === 'Autre') return 'Autre';
  return gender || '';
};

export const patientAge = (patient) => {
  if (!patient) return '';
  if (patient.date_of_birth) return calcAge(patient.date_of_birth);
  if (patient.age != null && patient.age !== '') return String(patient.age);
  return '';
};

export const patientFullName = (patient) => {
  if (!patient) return '';
  return `${patient.last_name || ''} ${patient.first_name || ''}`.trim();
};

export const lineTotalGnf = (line) => Number(line.quantity || 1) * Number(line.unit_price_gnf || 0);

export const formatLineTotal = (line) => formatGNF(lineTotalGnf(line));
