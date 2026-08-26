import { useEffect, useState } from 'react';
import { patientRecordAPI } from '../services/api.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import '../pages/clinical/clinical.css';

function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export default function PatientMedicalHistory() {
  const [history, setHistory] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await patientRecordAPI.getMyMedicalHistory();
        setHistory(data);
      } catch (err) {
        setError(err?.response?.data?.detail || 'Impossible de charger votre dossier médical.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="clinical-page">
        <h1>Dossier médical</h1>
        <PageSkeleton lines={8} />
      </div>
    );
  }
  if (error) {
    return (
      <div className="clinical-page">
        <h1>Dossier médical</h1>
        <p className="clinical-error" role="alert">{error}</p>
      </div>
    );
  }
  if (!history) {
    return (
      <div className="clinical-page">
        <h1>Dossier médical</h1>
        <p>Aucune donnée médicale disponible.</p>
      </div>
    );
  }

  const upcomingFollowUps = (history.follow_ups || []).filter(
    (f) => f.status === 'scheduled' || f.status === 'overdue'
  );

  return (
    <div className="clinical-page">
      <h1>Dossier médical</h1>
      <p className="clinical-lead">
        Historique permanent — consultations, prescriptions, examens et suivis.
      </p>

      <div className="clinical-grid">
        <section className="clinical-card">
          <h2>Allergies</h2>
          <ul className="clinical-list">
            {(history.allergies || []).map((a) => (
              <li key={a.id}>
                <strong>{a.allergen}</strong> · {a.severity}
                {a.reaction ? ` — ${a.reaction}` : ''}
              </li>
            ))}
            {(history.allergies || []).length === 0 && <li>Aucune allergie enregistrée.</li>}
          </ul>
        </section>

        <section className="clinical-card">
          <h2>Maladies chroniques</h2>
          <ul className="clinical-list">
            {(history.chronic_conditions || []).map((c) => (
              <li key={c.id}>
                <strong>{c.condition_name}</strong>
                <span className="clinical-badge">{c.status}</span>
              </li>
            ))}
            {(history.chronic_conditions || []).length === 0 && <li>Aucune pathologie chronique.</li>}
          </ul>
        </section>
      </div>

      <section className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Prochains suivis</h2>
        <ul className="clinical-list">
          {upcomingFollowUps.map((f) => (
            <li key={f.id}>
              <strong>{formatDate(f.scheduled_date)}</strong> — {f.visit_type === 'follow_up' ? 'Suivi' : 'Consultation'}
              {f.reason ? ` · ${f.reason}` : ''}
              <span className="clinical-badge">{f.status}</span>
            </li>
          ))}
          {upcomingFollowUps.length === 0 && <li>Aucun suivi planifié.</li>}
        </ul>
      </section>

      <section className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Chronologie médicale</h2>
        {(history.timeline || []).map((day) => (
          <article key={day.date} style={{ marginBottom: '1.25rem' }}>
            <h3>{formatDate(day.date)}</h3>
            <ul className="clinical-list">
              {day.events.map((ev, idx) => (
                <li key={`${day.date}-${idx}`}>
                  <strong>{ev.title}</strong>
                  {ev.details?.diagnosis && (
                    <>
                      <br />
                      Diagnostic : {ev.details.diagnosis}
                    </>
                  )}
                  {ev.details?.prescriptions?.length > 0 && (
                    <>
                      <br />
                      Prescription : {ev.details.prescriptions.join(', ')}
                    </>
                  )}
                  {ev.details?.clinical_notes && (
                    <>
                      <br />
                      {ev.details.clinical_notes}
                    </>
                  )}
                  {ev.details?.result_summary && (
                    <>
                      <br />
                      Résultat : {ev.details.result_summary}
                    </>
                  )}
                </li>
              ))}
            </ul>
          </article>
        ))}
        {(history.timeline || []).length === 0 && <p>Aucun événement clinique.</p>}
      </section>

      <section className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Ordonnances précédentes</h2>
        <ul className="clinical-list">
          {(history.prescriptions || []).map((rx) => (
            <li key={rx.id}>
              {formatDate(rx.date)} — {(rx.medications || []).map((m) => m.name).join(', ')}
              <span className="clinical-badge">{rx.status}</span>
            </li>
          ))}
          {(history.prescriptions || []).length === 0 && <li>Aucune ordonnance.</li>}
        </ul>
      </section>

      <section className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Résultats de laboratoire</h2>
        <ul className="clinical-list">
          {(history.lab_results || []).map((lr, idx) => (
            <li key={`${lr.lab_order_id}-${idx}`}>
              <strong>{lr.test_name}</strong>
              <br />
              {lr.result_summary}
              {lr.interpretation ? ` — ${lr.interpretation}` : ''}
            </li>
          ))}
          {(history.lab_results || []).length === 0 && <li>Aucun résultat validé.</li>}
        </ul>
      </section>

      <section className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Signes vitaux récents</h2>
        <ul className="clinical-list">
          {(history.vital_signs || []).slice(0, 5).map((v) => (
            <li key={v.id}>
              {formatDate(v.recorded_at)} — TA {v.bp_systolic}/{v.bp_diastolic}, FC {v.heart_rate},
              Temp {v.temperature_c}°C
            </li>
          ))}
          {(history.vital_signs || []).length === 0 && <li>Aucune mesure enregistrée.</li>}
        </ul>
      </section>
    </div>
  );
}
