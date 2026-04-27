import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { doctorsAPI } from '../services/api.js';
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
      <div className="doctors-page">
        <div className="page-state">
          <p>Chargement des médecins...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doctors-page">
        <div className="page-error">
          <p>Erreur: {error}</p>
        </div>
      </div>
    );
  }

  if (!doctors || doctors.length === 0) {
    return (
      <div className="doctors-page">
        <div className="no-doctors">
          <p>No doctors available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="doctors-page">
      <header className="doctors-header">
        <h1>Nos Médecins</h1>
        <p>Trouvez un spécialiste et prenez rendez-vous</p>
      </header>

      <div className="doctors-container">
        <div className="doctors-grid">
          {doctors.map((doctor) => (
            <article key={doctor.id} className="doctor-list-card">
              <h3 className="doctor-list-name">{doctor.first_name} {doctor.last_name}</h3>
              <p className="doctor-list-specialty">
                <span>Spécialité</span>
                <strong>{doctor.specialty || 'Généraliste'}</strong>
              </p>
              <button
                type="button"
                className="doctor-list-book"
                onClick={() => navigate('/appointments', { state: { doctorId: doctor.id } })}
              >
                Book appointment
              </button>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Doctors;