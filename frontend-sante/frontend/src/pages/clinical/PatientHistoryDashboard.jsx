import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import './clinical.css';

const MODULE_LABELS = {
  reception: 'Réception',
  doctor: 'Consultation',
  pev: 'PEV',
  nutrition: 'Nutrition',
  nursing: 'Soins infirmiers',
  hospitalization: 'Hospitalisation',
  lab: 'Laboratoire',
  pharmacy: 'Pharmacie',
};

const MODULE_COLORS = {
  reception: 'clinical-badge--muted',
  doctor: 'clinical-badge--accent',
  pev: 'clinical-badge--success',
  nutrition: 'clinical-badge--warning',
  nursing: 'clinical-badge--accent',
  hospitalization: 'clinical-badge--danger',
  lab: 'clinical-badge--accent',
  pharmacy: 'clinical-badge--success',
};

function formatWhen(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR');
  } catch {
    return String(value);
  }
}

export default function PatientHistoryDashboard() {
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [moduleFilter, setModuleFilter] = useState('all');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const loadTimeline = useCallback(async (patientId) => {
    setLoading(true);
    try {
      const { data } = await clinicalApi.patientTimeline(patientId);
      setTimeline(data);
      setError('');
    } catch (err) {
      setTimeline(null);
      setError(formatApiError(err, 'Historique patient indisponible'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedPatient?.id) {
      loadTimeline(selectedPatient.id);
    }
  }, [selectedPatient, loadTimeline]);

  const searchPatients = async () => {
    if (patientSearch.trim().length < 2) return;
    try {
      const { data } = await clinicalApi.searchPatients(patientSearch.trim());
      setPatientMatches(data || []);
    } catch (err) {
      setError(formatApiError(err, 'Recherche impossible'));
    }
  };

  const selectPatient = (patient) => {
    setSelectedPatient(patient);
    setPatientMatches([]);
    setModuleFilter('all');
  };

  const events = (timeline?.events || []).filter(
    (e) => moduleFilter === 'all' || e.module === moduleFilter
  );

  const counts = timeline?.counts || {};

  return (
    <div className="clinical-page">
      <h1>Dossier patient — parcours complet</h1>
      <p className="clinical-lead">
        Historique chronologique unifié : réception, consultations, PEV, nutrition, hospitalisation, soins, laboratoire et pharmacie.
      </p>
      {error && <p className="clinical-error">{String(error)}</p>}

      <section className="clinical-card">
        <h2>Rechercher un patient</h2>
        <div className="clinical-inline-form">
          <input
            type="search"
            placeholder="Nom ou téléphone (min. 2 caractères)"
            value={patientSearch}
            onChange={(e) => setPatientSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchPatients()}
          />
          <button type="button" className="clinical-btn secondary" onClick={searchPatients}>
            Rechercher
          </button>
        </div>
        {patientMatches.length > 0 && (
          <ul className="clinical-list">
            {patientMatches.map((p) => (
              <li key={p.id}>
                <button type="button" className="clinical-link-btn" onClick={() => selectPatient(p)}>
                  {p.first_name} {p.last_name} — {p.phone || 'sans téléphone'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {selectedPatient && (
        <>
          <section className="clinical-card">
            <h2>
              {selectedPatient.first_name} {selectedPatient.last_name}
              {timeline?.patient?.phone ? ` — ${timeline.patient.phone}` : ''}
            </h2>
            {counts && Object.keys(counts).length > 0 && (
              <div className="clinical-stat-chips">
                {Object.entries(counts).map(([mod, n]) => (
                  <span key={mod} className={`clinical-badge ${MODULE_COLORS[mod] || ''}`}>
                    {MODULE_LABELS[mod] || mod}: {n}
                  </span>
                ))}
              </div>
            )}
            <div className="clinical-tabs" role="tablist" style={{ marginTop: '1rem' }}>
              <button
                type="button"
                className={`clinical-tab${moduleFilter === 'all' ? ' active' : ''}`}
                onClick={() => setModuleFilter('all')}
              >
                Tout ({timeline?.events?.length || 0})
              </button>
              {Object.entries(MODULE_LABELS).map(([key, label]) =>
                counts[key] ? (
                  <button
                    key={key}
                    type="button"
                    className={`clinical-tab${moduleFilter === key ? ' active' : ''}`}
                    onClick={() => setModuleFilter(key)}
                  >
                    {label} ({counts[key]})
                  </button>
                ) : null
              )}
            </div>
          </section>

          <section className="clinical-card">
            <h2>Chronologie</h2>
            {loading && <p>Chargement…</p>}
            {!loading && events.length === 0 && <p>Aucun événement pour ce filtre.</p>}
            {!loading && events.length > 0 && (
              <ol className="clinical-timeline">
                {events.map((ev) => (
                  <li key={`${ev.module}-${ev.type}-${ev.id}`} className="clinical-timeline-item">
                    <div className="clinical-timeline-meta">
                      <span className={`clinical-badge ${MODULE_COLORS[ev.module] || ''}`}>
                        {MODULE_LABELS[ev.module] || ev.module}
                      </span>
                      <time>{formatWhen(ev.at)}</time>
                    </div>
                    <p className="clinical-timeline-summary">{ev.summary}</p>
                    {ev.detail && (
                      <ul className="clinical-list clinical-list--compact">
                        {Object.entries(ev.detail)
                          .filter(([, v]) => v != null && v !== '')
                          .map(([k, v]) => (
                            <li key={k}>
                              <strong>{k}:</strong> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                            </li>
                          ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  );
}
