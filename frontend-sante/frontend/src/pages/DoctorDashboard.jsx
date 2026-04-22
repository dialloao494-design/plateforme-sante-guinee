import { useEffect, useState } from 'react';
import { doctorDashboardAPI } from '../services/api.js';
import './DoctorDashboard.css';

const STATUS_META = {
  pending: { label: '🟡 En attente', className: 'status-badge status-pending' },
  paid: { label: '🟢 Paye', className: 'status-badge status-paid' },
  confirmed: { label: '🟢 Confirme', className: 'status-badge status-confirmed' },
  completed: { label: '🟢 Termine', className: 'status-badge status-confirmed' },
  cancelled: { label: '🔴 Annule', className: 'status-badge status-cancelled' },
};

const getStatusMeta = (status) => {
  const normalized = String(status || '').toLowerCase().replace('é', 'e');
  return STATUS_META[normalized] || STATUS_META.pending;
};

const DoctorDashboard = () => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const { data } = await doctorDashboardAPI.getAppointments();
        setAppointments(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err?.response?.data?.detail || err?.message || 'Impossible de charger les rendez-vous.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  return (
    <div className="doctor-dashboard-page">
      <div className="doctor-dashboard-card">
        <h1>Tableau de bord medecin</h1>
        <p>Liste des rendez-vous assignes a votre profil.</p>

        {loading && <p>Chargement...</p>}
        {error && <p className="error">{error}</p>}

        {!loading && !error && appointments.length === 0 && (
          <p>Aucun rendez-vous trouve.</p>
        )}

        {!loading && !error && appointments.length > 0 && (
          <ul className="doctor-appointments-list">
            {appointments.map((item) => {
              const statusMeta = getStatusMeta(item.status);
              return (
                <li key={item.id} className="doctor-appointment-item">
                  <div>
                    <p className="line-title">{item.patient_name}</p>
                    <p>{new Date(item.date).toLocaleString()}</p>
                    <p>{item.duration_minutes} minutes</p>
                  </div>
                  <span className={statusMeta.className}>{statusMeta.label}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};

export default DoctorDashboard;
