/**
 * Clinic-first directory — production clinics only, card grid.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { loadClinicDirectory } from '../../services/platformClinicData.js';
import { formatApiError } from '../../utils/apiError.js';
import './PlatformOwner.css';
import '../clinical/clinical.css';

export default function PlatformClinicDirectory() {
  const { user } = useAuth();
  const [clinics, setClinics] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const rows = await loadClinicDirectory({ category: 'production', search });
      setClinics(rows);
    } catch (err) {
      setError(formatApiError(err, 'Impossible de charger les cliniques'));
      setClinics([]);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(load, search ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  return (
    <div className="clinical-page platform-clinic-directory">
      <header className="clinical-page-header">
        <p className="clinical-eyebrow">Plateforme</p>
        <h1>Cliniques</h1>
        <p className="clinical-lead">
          Bienvenue, {user?.full_name || user?.email}. Sélectionnez une clinique pour gérer son personnel et son activité.
        </p>
      </header>

      <Link to="/platform/overview" className="platform-back-link">← Vue d’ensemble</Link>

      {error && <p className="clinical-error">{error}</p>}

      <div className="platform-toolbar">
        <div className="platform-search">
          <input
            type="search"
            placeholder="Rechercher par nom, ville ou ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Rechercher une clinique"
          />
        </div>
      </div>

      <section className="clinical-card">
        <h2>
          Cliniques en production
          {!loading && <span className="platform-count-badge">{clinics.length}</span>}
        </h2>
        {loading ? (
          <p className="clinical-lead">Chargement…</p>
        ) : clinics.length === 0 ? (
          <p className="clinical-lead">Aucune clinique production trouvée.</p>
        ) : (
          <div className="platform-clinic-grid">
            {clinics.map((clinic) => (
              <Link key={clinic.id} to={`/platform/clinics/${clinic.id}`} className="platform-clinic-card">
                <div className="platform-clinic-card__header">
                  <h3>{clinic.name}</h3>
                  <span className="platform-status platform-status--active">{clinic.status || 'Active'}</span>
                </div>
                <p className="platform-clinic-card__meta">
                  ID {clinic.id}
                  {clinic.city ? ` · ${clinic.city}` : ''}
                </p>
                {clinic.admin_email && (
                  <p className="platform-clinic-card__admin">Admin : {clinic.admin_email}</p>
                )}
                <div className="platform-clinic-card__stats">
                  <span>Personnel <strong>{clinic.staff_count ?? '—'}</strong></span>
                  {clinic.patient_count != null && (
                    <span>Patients <strong>{clinic.patient_count}</strong></span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
