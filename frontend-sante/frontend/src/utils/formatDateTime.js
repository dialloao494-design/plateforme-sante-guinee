import { formatClinicalDateTime, formatClinicalTime } from './clinicalPresentation.js';

export function formatDateTimeShort(iso) {
  return formatClinicalDateTime(iso);
}

export function formatTimeOnly(iso) {
  return formatClinicalTime(iso);
}

export function formatRelativeDay(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  if (sameDay) return "Aujourd'hui";
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  if (d.toDateString() === tomorrow.toDateString()) return 'Demain';
  return new Intl.DateTimeFormat('fr-GN', { weekday: 'long', day: 'numeric', month: 'short' }).format(d);
}
