const LOCALE = 'fr-GN';

export function formatDateTimeShort(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(LOCALE, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return '—';
  }
}

export function formatTimeOnly(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString(LOCALE, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '—';
  }
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
  return d.toLocaleDateString(LOCALE, { weekday: 'long', day: 'numeric', month: 'short' });
}
