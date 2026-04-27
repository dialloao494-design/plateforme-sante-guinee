import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import AppointmentCard from '../components/AppointmentCard.jsx';
import './Dashboard.css';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { appointments } = useAppointmentContext();
  const role = user?.role;
  const previewAppointments = appointments.slice(0, 2);

  const getPreviewTitle = (appointment) => {
    if (role === 'doctor' || role === 'admin') {
      return appointment?.patient?.first_name || 'Patient';
    }
    if (appointment?.doctor?.name) {
      return appointment.doctor.name;
    }
    return `Dr #${appointment?.doctor_id || '-'}`;
  };

  return (
    <div className="dashboard">
      <h1>Tableau de bord</h1>
      <div className="user-info">
        <h2>Bienvenue, {user?.email || 'Utilisateur'}</h2>
        {role && <p className="user-role">Rôle: {role.charAt(0).toUpperCase() + role.slice(1)}</p>}
      </div>
      <div className="dashboard-actions">
        <button type="button" className="action-button" onClick={() => navigate('/doctor/dashboard')}>
          Switch to Doctor Mode
        </button>
        {role === 'patient' && (
          <>
            <Link to="/appointments" className="action-button">Mes rendez-vous</Link>
            <button type="button" className="action-button" onClick={() => navigate('/doctors')}>
              Trouver un médecin
            </button>
          </>
        )}
        {role === 'doctor' && (
          <>
            <Link to="/doctors" className="action-button">Mon profil</Link>
            <Link to="/doctor/dashboard" className="action-button">Mon agenda</Link>
          </>
        )}
        {role === 'admin' && (
          <>
            <Link to="/users" className="action-button">Gérer les utilisateurs</Link>
            <Link to="/appointments" className="action-button">Tous les rendez-vous</Link>
            <Link to="/doctors" className="action-button">Gérer les médecins</Link>
          </>
        )}
        {!role && (
          <>
            <Link to="/doctors" className="action-button">Voir les médecins</Link>
            <Link to="/appointments" className="action-button">Mes rendez-vous</Link>
          </>
        )}
      </div>

      {previewAppointments.length > 0 && (
        <section className="dashboard-preview">
          <h3>Prochains rendez-vous</h3>
          <ul className="dashboard-preview-list">
            {previewAppointments.map((appointment) => (
              <AppointmentCard
                key={appointment.id}
                appointment={appointment}
                title={getPreviewTitle(appointment)}
                onPay={() => {}}
                onCancel={() => {}}
                onOpenMessages={() => {}}
                canPay={false}
                canCancel={false}
                canMessage={false}
                isPaying={false}
                isCancelling={false}
              />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
};

export default Dashboard;