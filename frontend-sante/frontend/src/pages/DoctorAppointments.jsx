import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { appointmentsAPI } from '../services/api.js';
import AppointmentActions from '../components/AppointmentActions.jsx';
import {
  formatGNF,
  getAppointmentState,
  getAppointmentActions,
} from '../utils/appointmentPresentation.js';
import './DoctorAppointments.css';

const DoctorAppointments = () => {
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('');
  const [actionBusyId, setActionBusyId] = useState(null);

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    return err?.message || fallback;
  };

  const loadAppointments = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await appointmentsAPI.getAll();
      setAppointments(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de charger les rendez-vous.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAppointments();
  }, []);

  const filteredAppointments = useMemo(() => {
    return appointments
      .filter((appointment) => {
        if (statusFilter !== 'all') {
          const appointmentState = getAppointmentState(appointment).state;
          if (statusFilter === 'pending' && appointmentState !== 'pending') {
            return false;
          }
          if ((statusFilter === 'confirmed' || statusFilter === 'paid') && appointmentState !== 'confirmed') {
            return false;
          }
          if (statusFilter === 'cancelled' && appointmentState !== 'cancelled') {
            return false;
          }
        }

        if (dateFilter) {
          const appointmentDay = new Date(appointment.date).toISOString().slice(0, 10);
          if (appointmentDay !== dateFilter) {
            return false;
          }
        }

        return true;
      })
      .sort((a, b) => new Date(a.date) - new Date(b.date));
  }, [appointments, statusFilter, dateFilter]);

  const isToday = (appointmentDate) => {
    const d = new Date(appointmentDate);
    const today = new Date();
    return d.toDateString() === today.toDateString();
  };

  const handleConfirm = async (appointmentId) => {
    setActionBusyId(appointmentId);
    try {
      await appointmentsAPI.updateStatus(appointmentId, 'confirmed');
      await loadAppointments();
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de confirmer le rendez-vous.'));
    } finally {
      setActionBusyId(null);
    }
  };

  const handleCancel = async (appointmentId) => {
    if (!window.confirm('Confirmer l’annulation de ce rendez-vous ?')) {
      return;
    }

    setActionBusyId(appointmentId);
    try {
      await appointmentsAPI.cancel(appointmentId);
      await loadAppointments();
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible d’annuler le rendez-vous.'));
    } finally {
      setActionBusyId(null);
    }
  };

  return (
    <div className="doctor-appointments-page">
      <header className="doctor-appointments-header">
        <div>
          <h1>Rendez-vous médecin</h1>
          <p>Gérez vos rendez-vous, confirmez-les et contactez vos patients.</p>
        </div>
        <Link to="/doctor/dashboard" className="button-secondary">Retour au tableau de bord</Link>
      </header>

      <div className="doctor-appointments-filters">
        <label>
          Date
          <input type="date" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} />
        </label>
        <label>
          Statut
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">Tous</option>
            <option value="pending">En attente</option>
            <option value="paid">Payé</option>
            <option value="confirmed">Confirmé</option>
            <option value="cancelled">Annulé</option>
          </select>
        </label>
      </div>

      {loading && <p>Chargement...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && filteredAppointments.length === 0 && (
        <p className="doctor-appointments-empty">Aucun rendez-vous trouvé.</p>
      )}

      <ul className="doctor-appointments-list">
        {filteredAppointments.map((appointment) => {
          const presentation = getAppointmentState(appointment);
          const actions = getAppointmentActions(appointment);
          const busy = actionBusyId === appointment.id;
          return (
            <li key={appointment.id} className={`doctor-appointment-card ${isToday(appointment.date) ? 'urgent' : ''}`}>
              <div className="doctor-appointment-main">
                <p className="patient-name">
                  {appointment?.patient?.first_name || 'Patient'} {appointment?.patient?.last_name || ''}
                </p>
                <p><strong>Date:</strong> {new Date(appointment.date).toLocaleString('fr-FR')}</p>
                <p><strong>Durée:</strong> {appointment.duration_minutes} minutes</p>
                <p><strong>Prix:</strong> {formatGNF(appointment.price)}</p>
                <p><strong>Paiement:</strong> {presentation.paymentLabel}</p>
                <p>
                  <strong>Statut:</strong> <span className={presentation.statusColor}>{presentation.displayStatus}</span>
                </p>
              </div>

              <AppointmentActions
                actions={actions}
                appointment={appointment}
                onPay={() => handleConfirm(appointment.id)}
                onCancel={() => handleCancel(appointment.id)}
                onOpenMessages={() => navigate(`/messages/${appointment.id}`)}
                onJoinConsultation={() => window.open(appointment.meeting_link, '_blank', 'noopener,noreferrer')}
                isPaying={busy}
                isCancelling={busy}
              />
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default DoctorAppointments;
