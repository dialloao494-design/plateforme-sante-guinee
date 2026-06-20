/**
 * Platform owner — clinic-first directory with filters and search.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import platformApi from '../../services/platformApi';
import { formatApiError } from '../../utils/apiError.js';
import { filterProductionClinics } from '../../utils/clinicProductionFilter.js';
import ClinicalStatGrid from '../clinical/ClinicalStatGrid.jsx';
import '../clinical/clinical.css';
import './PlatformOwner.css';

const CATEGORY_FILTERS = [
  { value: 'production', label: 'Cliniques production' },
  { value: 'demo', label: 'Cliniques démo' },
  { value: 'test', label: 'Comptes test' },
  { value: 'archived', label: 'Archivées' },
  { value: 'all', label: 'Toutes' },
];

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '—';
  }
}

export default function PlatformClinicDirectory() {
  const { user } = useAuth();
  const [category, setCategory] = useState('production');
  const [search, setSearch] = useState('');
  const [clinics, setClinics] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [viewMode, setViewMode] = useState('cards');
  const [clinicForm, setClinicForm] = useState({ name: '', city: 'Conakry', phone: '', address: '' });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      try {
        const [dirRes, sumRes] = await Promise.all([
          platformApi.listClinicDirectory({ category, search: search.trim() || undefined }),
          platformApi.getSummary(category),
        ]);
        setClinics(Array.isArray(dirRes.data) ? dirRes.data : []);
        setSummary(sumRes.data || null);
      } catch {
        const { data } = await clinicalApi.listClinics({ forceRefresh: true });
        let rows = filterProductionClinics(data || []);
        if (category === 'archived') rows = (data || []).filter((c) => !c.is_active);
        else if (category !== 'production' && category !== 'all') rows = [];
        const q = search.trim().toLowerCase();
        if (q) {
          rows = rows.filter(
            (c) =>
              String(c.name || '').toLowerCase().includes(q)
              || String(c.id) === q
              || String(c.city || '').toLowerCase().includes(q)
          );
        }
        setClinics(rows);
        setSummary({
          total_clinics: rows.length,
          active_clinics: rows.filter((c) => c.is_active).length,
          total_staff: 0,
          total_patients: 0,
          monthly_consultations: 0,
        });
      }
    } catch (err) {
      setError(formatApiError(err, 'Impossible de charger les cliniques'));
      setClinics([]);
    } finally {
      setLoading(false);
    }
  }, [category, search]);

  useEffect(() => {
    const timer = setTimeout(loadData, search ? 300 : 0);
    return () => clearTimeout(timer);
  }, [loadData, search]);

  const createClinic = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const { data } = await clinicalApi.createClinic(clinicForm);
      setMessage(`Clinique créée : ${data.name} (#${data.id})`);
      setClinicForm({ name: '', city: 'Conakry', phone: '', address: '' });
      setShowCreate(false);
      loadData();
    } catch (err) {
      setError(formatApiError(err, 'Création clinique impossible'));
    }
  };

  const stats = useMemo(
    () =>
      summary
        ? [
            { label: 'Cliniques', value: summary.total_clinics, variant: 'accent' },
            { label: 'Actives', value: summary.active_clinics, variant: 'success' },
            { label: 'Personnel', value: summary.total_staff },
            { label: 'Patients', value: summary.total_patients },
            { label: 'Consultations (mois)', value: summary.monthly_consultations },
          ]
        : [],
    [summary]
  );

  return (
    <div className="clinical-page clinical-page--platform-owner platform-clinic-directory">
      <header className="clinical-page-header">
        <p className="clinical-eyebrow">Propriétaire plateforme</p>
        <h1>Cliniques</h1>
        <p className="clinical-lead">
          Bienvenue, {user?.full_name || user?.email}. Gérez les cliniques comme entités distinctes —
          chaque établissement regroupe son personnel, ses patients et son activité.
        </p>
      </header>

      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <div className="platform-toolbar">
        <div className="platform-search">
          <input
            type="search"
            placeholder="Rechercher par nom, ville, ID ou email admin…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Rechercher une clinique"
          />
        </div>
        <div className="platform-filter-tabs" role="tablist" aria-label="Filtrer les cliniques">
          {CATEGORY_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              role="tab"
              aria-selected={category === f.value}
              className={`platform-filter-tab${category === f.value ? ' platform-filter-tab--active' : ''}`}
              onClick={() => setCategory(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <button type="button" className="clinical-btn" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? 'Annuler' : '+ Nouvelle clinique'}
        </button>
        <div className="platform-view-toggle" role="group" aria-label="Mode d'affichage">
          <button
            type="button"
            className={`platform-filter-tab${viewMode === 'cards' ? ' platform-filter-tab--active' : ''}`}
            onClick={() => setViewMode('cards')}
          >
            Cartes
          </button>
          <button
            type="button"
            className={`platform-filter-tab${viewMode === 'table' ? ' platform-filter-tab--active' : ''}`}
            onClick={() => setViewMode('table')}
          >
            Tableau
          </button>
        </div>
      </div>

      {showCreate && (
        <section className="clinical-card platform-create-clinic">
          <h2>Créer une clinique</h2>
          <form onSubmit={createClinic}>
            <div className="platform-form-grid">
              <div className="clinical-field">
                <label>Nom</label>
                <input
                  value={clinicForm.name}
                  onChange={(e) => setClinicForm({ ...clinicForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="clinical-field">
                <label>Ville</label>
                <input
                  value={clinicForm.city}
                  onChange={(e) => setClinicForm({ ...clinicForm, city: e.target.value })}
                />
              </div>
              <div className="clinical-field">
                <label>Téléphone</label>
                <input
                  value={clinicForm.phone}
                  onChange={(e) => setClinicForm({ ...clinicForm, phone: e.target.value })}
                />
              </div>
              <div className="clinical-field">
                <label>Adresse</label>
                <input
                  value={clinicForm.address}
                  onChange={(e) => setClinicForm({ ...clinicForm, address: e.target.value })}
                />
              </div>
            </div>
            <button type="submit" className="clinical-btn">Créer la clinique</button>
          </form>
        </section>
      )}

      <section className="clinical-card">
        <h2>
          Répertoire
          {!loading && <span className="platform-count-badge">{clinics.length}</span>}
        </h2>
        {loading ? (
          <p className="clinical-lead">Chargement…</p>
        ) : clinics.length === 0 ? (
          <p className="clinical-lead">Aucune clinique pour ce filtre.</p>
        ) : viewMode === 'table' ? (
          <div className="platform-table-wrap">
            <table className="clinical-stock-table platform-clinic-table">
              <thead>
                <tr>
                  <th>Clinique</th>
                  <th>ID</th>
                  <th>Statut</th>
                  <th>Ville</th>
                  <th>Créée le</th>
                  <th>Personnel</th>
                  <th>Patients</th>
                  <th>Consultations</th>
                  <th>Dernière activité</th>
                </tr>
              </thead>
              <tbody>
                {clinics.map((clinic) => (
                  <tr key={clinic.id}>
                    <td>
                      <Link to={`/platform/clinics/${clinic.id}`} className="platform-table-link">
                        {clinic.name}
                      </Link>
                      {clinic.admin_email && (
                        <span className="platform-table-sub">{clinic.admin_email}</span>
                      )}
                    </td>
                    <td>{clinic.id}</td>
                    <td>
                      <span className={`platform-status platform-status--${clinic.is_active ? 'active' : 'archived'}`}>
                        {clinic.status}
                      </span>
                    </td>
                    <td>{clinic.city || '—'}</td>
                    <td>{formatDate(clinic.created_at)}</td>
                    <td>{clinic.staff_count}</td>
                    <td>{clinic.patient_count}</td>
                    <td>{clinic.consultation_count}</td>
                    <td>{formatDate(clinic.last_activity_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="platform-clinic-grid">
            {clinics.map((clinic) => (
              <Link
                key={clinic.id}
                to={`/platform/clinics/${clinic.id}`}
                className="platform-clinic-card"
              >
                <div className="platform-clinic-card__header">
                  <h3>{clinic.name}</h3>
                  <span className={`platform-status platform-status--${clinic.is_active ? 'active' : 'archived'}`}>
                    {clinic.status}
                  </span>
                </div>
                <p className="platform-clinic-card__meta">
                  ID {clinic.id}
                  {clinic.city ? ` · ${clinic.city}` : ''}
                  {' · Créée '}
                  {formatDate(clinic.created_at)}
                </p>
                {clinic.admin_email && (
                  <p className="platform-clinic-card__admin">Admin : {clinic.admin_email}</p>
                )}
                <div className="platform-clinic-card__stats">
                  <span>Personnel <strong>{clinic.staff_count}</strong></span>
                  <span>Patients <strong>{clinic.patient_count}</strong></span>
                  <span>Consultations <strong>{clinic.consultation_count}</strong></span>
                </div>
                <p className="platform-clinic-card__activity">
                  Dernière activité : {formatDate(clinic.last_activity_at)}
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
