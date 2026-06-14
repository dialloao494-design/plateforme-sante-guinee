import { useCallback, useEffect, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';

import './clinical.css';

const EVENT_LABELS = {
  confirmed: 'Confirmé',
  cancelled: 'Annulé',
  reschedule_requested: 'Report demandé',
  sent: 'Rappel envoyé',
};

export default function StaffNotificationCenter() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await clinicalApi.reminderNotifications();
      setItems(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Notifications indisponibles');
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="clinical-page">
      <header className="clinical-header">
        <h1>Centre de notifications</h1>
        <p>Confirmations, annulations et demandes de report (WhatsApp RDV).</p>
      </header>
      {error && <div className="clinical-alert clinical-alert--error">{error}</div>}
      <section className="clinical-panel">
        <ul className="clinical-queue">
          {items.length === 0 && <li>Aucune notification récente.</li>}
          {items.map((n) => (
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
