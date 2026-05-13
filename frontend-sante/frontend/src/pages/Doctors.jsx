import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { doctorsAPI } from '../services/api.js';
import { formatSpecialtyLabel } from '../utils/specialtyLabels.js';
import {
  GUINEA_REGION_OPTIONS,
  SPECIALTY_FILTER_OPTIONS,
  sortDoctorsByProximity,
} from '../utils/guineaLocations.js';
import EmptyState from '../components/ui/EmptyState.jsx';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './Doctors.css';

const Doctors = () => {
  const navigate = useNavigate();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [region, setRegion] = useState('');
  const [geoStatus, setGeoStatus] = useState('idle');
  const [userPos, setUserPos] = useState(null);

  useEffect(() => {
    const t = window.setTimeout(() => setSearch(searchInput.trim()), 350);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const fetchList = useCallback(async () => {
    try {
      setLoading(true);
      const response = await doctorsAPI.getAll({
        specialty: specialty || undefined,
        location: region || undefined,
        search: search || undefined,
      });
      let list = Array.isArray(response.data) ? response.data : [];
      if (userPos) {
        list = sortDoctorsByProximity(list, userPos.lat, userPos.lon);
      }
      setDoctors(list);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Impossible de charger les médecins.');
      setDoctors([]);
    } finally {
      setLoading(false);
    }
  }, [specialty, region, search, userPos]);

  useEffect(() => {
    void fetchList();
  }, [fetchList]);

  const requestNearby = () => {
    if (!navigator.geolocation) {
      setGeoStatus('unsupported');
      return;
    }
    setGeoStatus('loading');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserPos({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setGeoStatus('ok');
      },
      () => {
        setGeoStatus('denied');
        setUserPos(null);
      },
      { enableHighAccuracy: false, timeout: 12_000, maximumAge: 60_000 }
    );
  };

  const clearNearby = () => {
    setUserPos(null);
    setGeoStatus('idle');
  };

  const filterSummary = useMemo(() => {
    const bits = [];
    if (search) bits.push(`« ${search} »`);
    if (specialty) bits.push(formatSpecialtyLabel(specialty));
    if (region) bits.push(region);
    return bits.length ? bits.join(' · ') : 'Tous les praticiens référencés';
  }, [search, specialty, region]);

  if (loading && doctors.length === 0) {
    return (
      <div className="doctors-page ds-page">
        <header className="doctors-header">
          <h1>Nos médecins</h1>
          <p>Annuaire des praticiens disponibles pour la prise de rendez-vous.</p>
        </header>
        <PageSkeleton lines={6} />
      </div>
    );
  }

  if (error && doctors.length === 0 && !loading) {
    return (
      <div className="doctors-page ds-page">
        <header className="doctors-header">
          <h1>Nos médecins</h1>
        </header>
        <div className="doctors-page-error" role="alert">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="doctors-page ds-page">
      <header className="doctors-header">
        <h1>Annuaire des médecins</h1>
        <p>Trouvez un spécialiste à Conakry, Kindia ou en téléconsultation — filtres par zone et spécialité.</p>
      </header>

      <section className="doctors-discovery" aria-label="Recherche et filtres">
        <div className="doctors-discovery-row">
          <label className="doctors-field">
            <span>Recherche</span>
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Nom, spécialité, quartier…"
              autoComplete="off"
            />
          </label>
          <label className="doctors-field">
            <span>Spécialité</span>
            <select value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
              {SPECIALTY_FILTER_OPTIONS.map((o) => (
                <option key={o.value || 'all'} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="doctors-field">
            <span>Zone</span>
            <select value={region} onChange={(e) => setRegion(e.target.value)}>
              {GUINEA_REGION_OPTIONS.map((o) => (
                <option key={o.value || 'all'} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="doctors-discovery-actions">
          <button type="button" className="btn btn-secondary" onClick={requestNearby} disabled={geoStatus === 'loading'}>
            {geoStatus === 'loading' ? 'Localisation…' : 'Trier par proximité'}
          </button>
          {userPos && (
            <button type="button" className="btn btn-ghost" onClick={clearNearby}>
              Réinitialiser le tri
            </button>
          )}
          <span className="doctors-filter-summary">{filterSummary}</span>
        </div>
        {geoStatus === 'denied' && (
          <p className="doctors-geo-hint">Localisation refusée — tri par proximité désactivé.</p>
        )}
        {geoStatus === 'unsupported' && (
          <p className="doctors-geo-hint">La géolocalisation n’est pas disponible sur ce navigateur.</p>
        )}
        {geoStatus === 'ok' && <p className="doctors-geo-hint">Tri approximatif selon la zone d’exercice et votre position.</p>}
      </section>

      {loading && doctors.length > 0 && <div className="doctors-inline-loading" aria-busy="true"><PageSkeleton lines={2} /></div>}

      {!loading && doctors.length === 0 && (
        <EmptyState
          preset="people"
          title="Aucun médecin ne correspond à ces critères"
          description="Élargissez la zone, changez la spécialité ou effacez la recherche pour voir plus de praticiens."
          actionLabel="Réinitialiser les filtres"
          onAction={() => {
            setSearchInput('');
            setSearch('');
            setSpecialty('');
            setRegion('');
            clearNearby();
          }}
        />
      )}

      {!loading && doctors.length > 0 && (
        <div className="doctors-container">
          <p className="doctors-count-line">{doctors.length} praticien(s)</p>
          <div className="doctors-grid">
            {doctors.map((doctor) => (
              <article key={doctor.id} className="doctor-list-card">
                <h3 className="doctor-list-name">{doctor.name || `Dr ${doctor.first_name} ${doctor.last_name}`}</h3>
                <p className="doctor-list-specialty">
                  <span>Spécialité</span>
                  <strong>{formatSpecialtyLabel(doctor.specialty)}</strong>
                </p>
                {doctor.location && (
                  <p className="doctor-list-city">
                    <span>Localisation</span>
                    <strong>{doctor.location}</strong>
                  </p>
                )}
                <p className="doctor-list-fee">
                  <span>À partir de</span>
                  <strong>
                    {new Intl.NumberFormat('fr-FR').format(Number(doctor.consultation_fee || 0))} GNF
                  </strong>
                </p>
                <div className="doctor-list-actions">
                  <Link to={`/doctors/${doctor.id}`} className="btn btn-secondary doctor-list-link">
                    Voir la fiche
                  </Link>
                  <button
                    type="button"
                    className="btn btn-primary doctor-list-book"
                    onClick={() => navigate('/appointments', { state: { doctorId: doctor.id } })}
                  >
                    Prendre rendez-vous
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Doctors;
