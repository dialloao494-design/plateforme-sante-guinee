import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { doctorsAPI } from '../services/api.js';
import { formatSpecialtyLabel } from '../utils/specialtyLabels.js';
import EmptyState from '../components/ui/EmptyState.jsx';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './Doctors.css';

const Doctors = () => {
  const navigate = useNavigate();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        setLoading(true);
        const response = await doctorsAPI.getAll();
        setDoctors(response.data);
        setError(null);
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'Impossible de charger les médecins.');
        setDoctors([]);
      } finally {
        setLoading(false);
      }
    };

    fetchDoctors();
  }, []);

  if (loading) {
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

  if (error) {
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

  if (!doctors || doctors.length === 0) {
    return (
      <div className="doctors-page ds-page">
        <header className="doctors-header">
          <h1>Nos médecins</h1>
          <p>Aucun praticien n’est publié pour le moment.</p>
        </header>
        <EmptyState
          preset="people"
          title="Annuaire en cours de configuration"
          description="Les cabinets partenaires de Conakry, Kindia et la téléconsultation apparaîtront ici dès que les profils seront validés."
          actionLabel="Retour au tableau de bord"
          onAction={() => navigate('/dashboard')}
        />
      </div>
    );
  }

  return (
    <div className="doctors-page ds-page">
      <header className="doctors-header">
        <h1>Nos médecins</h1>
        <p>Spécialistes et médecine générale — réservez un créneau au cabinet ou en visio sécurisée.</p>
      </header>

      <div className="doctors-container">
        <div className="doctors-grid">
          {doctors.map((doctor) => (
            <article key={doctor.id} className="doctor-list-card">
              <h3 className="doctor-list-name">
                Dr {doctor.first_name} {doctor.last_name}
              </h3>
              <p className="doctor-list-specialty">
                <span>Spécialité</span>
                <strong>{formatSpecialtyLabel(doctor.specialty)}</strong>
              </p>
              {doctor.city && (
                <p className="doctor-list-city">
                  <span>Localisation</span>
                  <strong>{doctor.city}</strong>
                </p>
              )}
              <button
                type="button"
                className="doctor-list-book"
                onClick={() => navigate('/appointments', { state: { doctorId: doctor.id } })}
              >
                Prendre rendez-vous
              </button>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Doctors;
