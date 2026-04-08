import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { doctorsAPI } from '../services/api.js';
import './Doctors.css';

const Doctors = () => {
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        const response = await doctorsAPI.getAll();
        setDoctors(response.data);
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'Failed to load doctors');
      } finally {
        setLoading(false);
      }
    };
    fetchDoctors();
  }, []);

  const handleBookAppointment = (doctorId) => {
    navigate(`/appointments?doctor_id=${doctorId}`);
  };

  return (
    <div className="doctors-page">
      <header className="doctors-header">
        <div>
          <h1>Meet our doctors</h1>
          <p>Choose a specialist and book a convenient appointment in seconds.</p>
        </div>
      </header>

      {loading && <div className="page-state">Chargement des médecins...</div>}
      {error && <div className="page-error">Erreur : {error}</div>}

      {!loading && !error && (
        <div className="doctors-grid">
          {doctors.map((doctor) => (
            <div key={doctor.id} className="doctor-card">
              <div className="doctor-card-header">
                <div className="doctor-avatar">{doctor.name?.slice(0, 1)}</div>
                <h3>{doctor.name}</h3>
              </div>
              <p className="doctor-specialty">{doctor.specialty}</p>
              <button className="button-primary" onClick={() => handleBookAppointment(doctor.id)}>
                Book appointment
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Doctors;