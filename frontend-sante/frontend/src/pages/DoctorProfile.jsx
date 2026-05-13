import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { doctorsAPI } from '../services/api.js';
import { formatSpecialtyLabel } from '../utils/specialtyLabels.js';
import { formatGNF } from '../utils/appointmentPresentation.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './DoctorProfile.css';

export default function DoctorProfile() {
  const { doctorId } = useParams();
  const navigate = useNavigate();
  const [doctor, setDoctor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await doctorsAPI.getById(doctorId);
      setDoctor(data);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Médecin introuvable.');
      setDoctor(null);
    } finally {
      setLoading(false);
    }
  }, [doctorId]);

  useEffect(() => {
    void load();
  }, [load]);

  const book = () => {
    navigate('/appointments', { state: { doctorId: Number(doctorId) } });
  };

  const displayName = useMemo(() => {
    if (!doctor) return '';
    return doctor.name || `Dr #${doctor.id}`;
  }, [doctor]);

  return (
    <div className="doctor-profile-page ds-page">
      <header className="doctor-profile-header">
        <div>
          <p className="doctor-profile-eyebrow">Fiche publique</p>
          <h1>{displayName || 'Chargement…'}</h1>
          {doctor && (
            <p className="doctor-profile-meta">
              {formatSpecialtyLabel(doctor.specialty)} · {doctor.location || 'Guinée'}
            </p>
          )}
        </div>
        <div className="doctor-profile-header-actions">
          <Link to="/doctors" className="btn btn-secondary">
            Annuaire
          </Link>
          <button type="button" className="btn btn-primary" disabled={!doctor} onClick={book}>
            Prendre rendez-vous
          </button>
        </div>
      </header>

      {loading && (
        <div className="doctor-profile-loading">
          <PageSkeleton lines={4} />
        </div>
      )}

      {error && !loading && (
        <div className="doctor-profile-error" role="alert">
          {error}
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/doctors')}>
            Retour à l’annuaire
          </button>
        </div>
      )}

      {!loading && doctor && (
        <div className="doctor-profile-grid">
          <section className="doctor-profile-card doctor-profile-card--hero">
            <div className="doctor-profile-avatar-wrap">
              {doctor.photo_url ? (
                <img src={doctor.photo_url} alt="" className="doctor-profile-photo" />
              ) : (
                <div className="doctor-profile-photo-fallback" aria-hidden>
                  {String(doctor.name || 'Dr')
                    .replace(/^Dr\s*/i, '')
                    .slice(0, 2)
                    .toUpperCase()}
                </div>
              )}
            </div>
            <div>
              <h2>Présentation</h2>
              <p className="doctor-profile-lead">
                Praticien référencé sur la plateforme. Réservez un créneau pour une consultation au cabinet ou en
                téléconsultation sécurisée selon les disponibilités affichées lors de la réservation.
              </p>
              <dl className="doctor-profile-facts">
                <div>
                  <dt>Tarif indicatif</dt>
                  <dd>{formatGNF(doctor.consultation_fee)}</dd>
                </div>
                <div>
                  <dt>Zone d’exercice</dt>
                  <dd>{doctor.location || '—'}</dd>
                </div>
              </dl>
            </div>
          </section>

          <section className="doctor-profile-card">
            <h2>Carte & proximité</h2>
            <p className="doctor-profile-muted">
              La géolocalisation patient → cabinet sera affichée ici (carte interactive) une fois le fournisseur cartes
              choisi (MapLibre / Google). Les coordonnées régionales sont déjà utilisées côté annuaire pour le tri
              « à proximité ».
            </p>
            <div className="doctor-profile-map-placeholder" role="img" aria-label="Emplacement approximatif">
              <span>Carte — intégration à venir</span>
              <small>Conakry &amp; régions · Guinée</small>
            </div>
          </section>

          <section className="doctor-profile-card doctor-profile-card--cta">
            <h2>Gagner du temps</h2>
            <p>
              Réservez en ligne, recevez les confirmations sur votre espace et échangez avec le cabinet avant la
              consultation via la messagerie sécurisée.
            </p>
            <button type="button" className="btn btn-primary doctor-profile-cta" onClick={book}>
              Choisir un créneau
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
