import { useState, useEffect } from 'react';
import { doctorsAPI } from '../services/api.js';
import './Doctors.css';

const Doctors = () => {
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        console.log('🔍 Fetching doctors from API...');
        setLoading(true);
        const response = await doctorsAPI.getAll();
        console.log('✅ Doctors fetched successfully:', response.data);
        setDoctors(response.data);
        setError(null);
      } catch (err) {
        console.error('❌ Error fetching doctors:', err);
        setError(err?.response?.data?.detail || err.message || 'Erreur lors du chargement des médecins');
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
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <p>Chargement des médecins...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doctors-page">
        <div style={{ padding: '40px', textAlign: 'center', color: 'red' }}>
          <p>Erreur: {error}</p>
        </div>
      </div>
    );
  }

  if (!doctors || doctors.length === 0) {
    return (
      <div className="doctors-page">
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <p>Aucun médecin trouvé</p>
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

      <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: '20px'
        }}>
          {doctors.map((doctor) => (
            <div
              key={doctor.id}
              style={{
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '20px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              <h3>{doctor.first_name} {doctor.last_name}</h3>
              <p><strong>Spécialité:</strong> {doctor.specialty}</p>
              <p><strong>Lieu:</strong> {doctor.location}</p>
              <p><strong>Téléphone:</strong> {doctor.phone}</p>
              {doctor.consultation_fee && (
                <p><strong>Tarif:</strong> {doctor.consultation_fee} GNF</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Doctors;