import { useCallback } from 'react';

import clinicalApi from '../../services/clinicalApi';
import { usePollingQuery } from '../../hooks/usePollingQuery.js';

import './clinical.css';

const EVENT_LABELS = {
  confirmed: 'Confirmé',
  cancelled: 'Annulé',
  reschedule_requested: 'Report demandé',
  sent: 'Rappel envoyé',
};

export default function StaffNotificationCenter() {
  const fetchNotifications = useCallback(
    () => clinicalApi.reminderNotifications().then((res) => ({ data: res.data || [] })),
    []
  );

  const { data: items, error } = usePollingQuery(fetchNotifications, {
    pollMs: 120_000,
    initialData: [],
  });

  const rows = Array.isArray(items) ? items : [];

  return (
    <div className="clinical-page">
      <header className="clinical-header">
        <h1>Centre de notifications</h1>
        <p>Confirmations, annulations et demandes de report (WhatsApp RDV).</p>
      </header>
      {error && <div className="clinical-alert clinical-alert--error">{String(error)}</div>}
      <section className="clinical-panel">
        <ul className="clinical-queue">
          {rows.length === 0 && <li>Aucune notification récente.</li>}
          {rows.map((n) => (
            <li key={n.id}>
              <span className="clinical-badge">{EVENT_LABELS[n.event_type] || n.event_type}</span>
              <div>RDV #{n.appointment_id} · Patient #{n.patient_id}</div>
              <small>{n.appointment_date ? new Date(n.appointment_date).toLocaleString('fr-GN') : '—'}</small>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
