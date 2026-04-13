import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import api, { doctorsAPI, paymentsAPI } from '../services/api.js';
import './Appointments.css';

const Appointments = () => {
  const { user } = useAuth();
  const isPatient = user?.role === 'patient';
  const isDoctor = user?.role === 'doctor';
  const isAdmin = user?.role === 'admin';
  const { appointments, loading, error, addAppointment, deleteAppointment, fetchAppointments } = useAppointmentContext();
  const [doctors, setDoctors] = useState([]);
  const [formData, setFormData] = useState({ doctorId: '', date: '', duration: 30 });
  const [selectedDoctorFilter, setSelectedDoctorFilter] = useState('');
  const [success, setSuccess] = useState('');
  const [actionError, setActionError] = useState('');
  const [lastAppointment, setLastAppointment] = useState(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isPaying, setIsPaying] = useState(false);
  const [paymentAttemptStarted, setPaymentAttemptStarted] = useState(false);
  const [paymentMessage, setPaymentMessage] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [isCreatingAppointment, setIsCreatingAppointment] = useState(false);
  const [searchParams] = useSearchParams();

  const getApiErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => (typeof item === 'string' ? item : item?.msg || JSON.stringify(item)))
        .join(' | ');
    }
    const message = err?.response?.data?.message;
    if (typeof message === 'string' && message.trim()) {
      return message;
    }
    return err?.message || fallback;
  };

  const normalizeDoctor = (item) => {
    const id = Number(item?.id);
    if (!id) return null;

    const role = String(item?.role || item?.user_role || '').toLowerCase();
    if (role && role !== 'doctor') return null;

    const fullName =
      item?.name || `${item?.first_name || ''} ${item?.last_name || ''}`.trim() || item?.email || `Docteur #${id}`;

    return {
      id,
      name: fullName,
    };
  };

  const fetchDoctors = async () => {
    try {
      const { data } = await doctorsAPI.getAll();
      const fromDoctorsEndpoint = (Array.isArray(data) ? data : [])
        .map(normalizeDoctor)
        .filter(Boolean);

      if (fromDoctorsEndpoint.length > 0) {
        setDoctors(fromDoctorsEndpoint);
        return;
      }

      // Fallback: if /doctors returns empty, try /users and keep only doctor-role users.
      const usersResponse = await api.get('/users');
      const fromUsersEndpoint = (Array.isArray(usersResponse.data) ? usersResponse.data : [])
        .filter((userItem) => String(userItem?.role || userItem?.user_role || '').toLowerCase() === 'doctor')
        .map(normalizeDoctor)
        .filter(Boolean);

      setDoctors(fromUsersEndpoint);
    } catch (err) {
      console.error('Failed to load doctors:', err);
      setActionError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Impossible de charger les médecins');
      setDoctors([]);
    }
  };

  useEffect(() => {
    fetchDoctors();
    const doctorId = searchParams.get('doctor_id');
    if (doctorId) {
      setFormData(prev => ({ ...prev, doctorId }));
    }
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsCreatingAppointment(true);
    setActionError('');
    setSuccess('');
    setPaymentMessage('');
    setPaymentError('');

    if (!formData.doctorId || !formData.date) {
      setActionError('Choisissez un médecin et une date.');
      setIsCreatingAppointment(false);
      return;
    }

    try {
      const payload = {
        doctor_id: Number(formData.doctorId),
        date: formData.date,
        duration_minutes: Number(formData.duration),
      };
      console.log('Submitting appointment:', payload);
      const appointment = await addAppointment(payload);
      console.log('Appointment created:', appointment);
      await fetchAppointments();
      setLastAppointment(appointment);
      setShowConfirmation(true);
      setSuccess('Rendez-vous créé avec succès. Vous pouvez maintenant procéder au paiement.');
      setFormData({ doctorId: '', date: '', duration: 30 });
    } catch (err) {
      setActionError(getApiErrorMessage(err, 'Erreur lors de la création du rendez-vous.'));
    } finally {
      setIsCreatingAppointment(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Êtes-vous sûr de vouloir annuler ce rendez-vous ?')) {
      return;
    }

    setActionError('');
    setSuccess('');
    try {
      await deleteAppointment(id);
      setSuccess('Rendez-vous annulé avec succès !');
      if (lastAppointment?.id === id) {
        setLastAppointment(null);
        setShowConfirmation(false);
      }
    } catch (err) {
      setActionError(getApiErrorMessage(err, 'Erreur lors de l’annulation du rendez-vous.'));
    }
  };

  const doctorOptions = doctors.map((doctor) => ({
    id: doctor.id,
    name: doctor.name,
  }));

  const filteredAppointments = useMemo(() => {
    return selectedDoctorFilter
      ? appointments.filter((appointment) => String(appointment.doctor_id) === selectedDoctorFilter)
      : appointments;
  }, [appointments, selectedDoctorFilter]);

  const getDoctorName = (appointmentOrId) => {
    if (typeof appointmentOrId === 'object' && appointmentOrId !== null) {
      const appointmentDoctor = appointmentOrId.doctor;
      if (appointmentDoctor?.name) {
        return appointmentDoctor.name;
      }
      const composed = `${appointmentDoctor?.first_name || ''} ${appointmentDoctor?.last_name || ''}`.trim();
      if (composed) {
        return `Dr ${composed}`;
      }
    }

    const id = typeof appointmentOrId === 'object' && appointmentOrId !== null
      ? appointmentOrId.doctor_id
      : appointmentOrId;

    const doctor = doctors.find((doc) => doc.id === Number(id));
    if (!doctor) {
      return `Dr #${id}`;
    }
    return doctor.name;
  };

  const getStatusClassName = (statusValue) => {
    const normalized = String(statusValue || '').toLowerCase();
    if (normalized === 'confirmed' || normalized === 'confirmé') return 'status-pill status-confirmed';
    if (normalized === 'cancelled') return 'status-pill status-cancelled';
    return 'status-pill status-pending';
  };

  const canCancel = (appointment) => {
    if (!user) return false;
    if (isAdmin) return true;
    if (isDoctor) return appointment.status !== 'cancelled';
    if (isPatient) {
      return appointment.status !== 'cancelled' && new Date(appointment.date) > new Date();
    }
    return false;
  };

  const handlePayNow = async () => {
    if (!lastAppointment || !lastAppointment.id) {
      setPaymentError('Invalid appointment.');
      return;
    }

    setPaymentError('');
    setPaymentMessage('');
    setIsPaying(true);
    setPaymentAttemptStarted(true);

    try {
      const response = await paymentsAPI.createIntent(lastAppointment.id);
      const { checkout_url } = response.data;

      if (!checkout_url) {
        throw new Error('Checkout URL missing from backend response.');
      }

      window.location.href = checkout_url;
    } catch (err) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to process payment.';
      setPaymentError(errorMsg);
      setPaymentAttemptStarted(false);
    } finally {
      setIsPaying(false);
    }
  };

  const handleNewBooking = () => {
    setShowConfirmation(false);
    setLastAppointment(null);
    setPaymentMessage('');
    setPaymentError('');
    setPaymentAttemptStarted(false);
  };

  return (
    <div className="appointments-page">
      <header className="appointments-header">
        <div>
          <h1>Appointments</h1>
          <p>Book a doctor, review your schedule, and confirm payment when ready.</p>
        </div>
      </header>

      {isPatient && showConfirmation && lastAppointment && (
        <div className="confirmation-card">
          <div className="confirmation-top">
            <div>
              <p className="tag">Booking confirmed</p>
              <h2>Appointment summary</h2>
            </div>
            <button className="button-secondary" onClick={handleNewBooking}>
              Book another
            </button>
          </div>
          <div className="confirmation-details">
            <div>
              <p className="detail-label">Doctor</p>
              <p>{getDoctorName(lastAppointment)}</p>
            </div>
            <div>
              <p className="detail-label">Date & Time</p>
              <p>{new Date(lastAppointment.date).toLocaleString()}</p>
            </div>
            <div>
              <p className="detail-label">Duration</p>
              <p>{lastAppointment.duration_minutes} minutes</p>
            </div>
            <div>
              <p className="detail-label">Status</p>
              <p>{lastAppointment.status || 'pending'}</p>
            </div>
          </div>
          <div className="confirmation-actions">
            <button
              type="button"
              className="button-pay"
              onClick={handlePayNow}
              disabled={
                isPaying ||
                paymentAttemptStarted ||
                lastAppointment.status !== 'pending' ||
                lastAppointment.payment_status === 'paid'
              }
            >
              {isPaying ? 'Processing payment...' : 'Pay with Stripe'}
            </button>
            {paymentMessage && <p className="success">{paymentMessage}</p>}
            {paymentError && <p className="error">{paymentError}</p>}
          </div>
        </div>
      )}

      {isPatient && (
      <form onSubmit={handleSubmit} className="appointment-form">
        <h2>Ajouter un rendez-vous</h2>

        <div className="form-group">
          <label>Médecin</label>
          <select
            value={formData.doctorId}
            onChange={(e) => setFormData((prev) => ({ ...prev, doctorId: e.target.value }))}
            required
          >
            <option value="">Sélectionnez un médecin</option>
            {doctorOptions.map((doctor) => (
              <option key={doctor.id} value={doctor.id}>
                {doctor.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Date</label>
          <input
            type="datetime-local"
            value={formData.date}
            onChange={(e) => setFormData((prev) => ({ ...prev, date: e.target.value }))}
            required
          />
        </div>

        <div className="form-group">
          <label>Durée (minutes)</label>
          <select
            value={formData.duration}
            onChange={(e) => setFormData((prev) => ({ ...prev, duration: e.target.value }))}
            required
          >
            {[30, 60, 90, 120].map((duration) => (
              <option key={duration} value={duration}>
                {duration} minutes
              </option>
            ))}
          </select>
        </div>

        <button type="submit" disabled={isCreatingAppointment}>
          {isCreatingAppointment ? 'Création en cours...' : 'Valider le rendez-vous'}
        </button>
      </form>
      )}

      {(actionError || error) && <p className="error">{actionError || error}</p>}
      {success && <p className="success">{success}</p>}

      <div className="appointments-list">
        <div className="appointments-panel">
          <div className="appointments-panel-header">
            <h2>Liste des rendez-vous</h2>
            <div className="appointments-filter">
              <label>Filtrer par médecin :</label>
              <select value={selectedDoctorFilter} onChange={(e) => setSelectedDoctorFilter(e.target.value)}>
                <option value="">Tous les médecins</option>
                {doctorOptions.map((doctor) => (
                  <option key={doctor.id} value={doctor.id}>
                    {doctor.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {loading && <p>Chargement...</p>}

          {!loading && appointments.length === 0 && <p>Aucun rendez-vous trouvé.</p>}

          {filteredAppointments.length > 0 && (
            <ul>
              {filteredAppointments.map((appointment) => (
                <li key={appointment.id} className="appointment-item">
                  <div className="appointment-info">
                    <p>
                      Médecin : <strong>{getDoctorName(appointment)}</strong>
                    </p>
                    <p>Date : {new Date(appointment.date).toLocaleString()}</p>
                    <p>
                      Statut : <span className={getStatusClassName(appointment.status)}>{appointment.status}</span>
                    </p>
                    <p>Payé : {appointment.payment_status}</p>
                    <p>Durée : {appointment.duration_minutes} minutes</p>
                    <p>Prix : {appointment.price} GNF</p>
                  </div>
                  <div className="appointment-actions">
                    {canCancel(appointment) && (
                      <button
                        onClick={() => handleDelete(appointment.id)}
                        disabled={loading || !canCancel(appointment)}
                        className="delete-btn"
                      >
                        Annuler
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default Appointments;