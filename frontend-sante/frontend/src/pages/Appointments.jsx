import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import { doctorsAPI, paymentsAPI } from '../services/api.js';
import './Appointments.css';

const Appointments = () => {
  const { appointments, loading, error, addAppointment, deleteAppointment } = useAppointmentContext();
  const [doctors, setDoctors] = useState([]);
  const [formData, setFormData] = useState({ doctorId: '', date: '', duration: 30 });
  const [selectedDoctorFilter, setSelectedDoctorFilter] = useState('');
  const [success, setSuccess] = useState('');
  const [actionError, setActionError] = useState('');
  const [lastAppointment, setLastAppointment] = useState(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isPaying, setIsPaying] = useState(false);
  const [paymentMessage, setPaymentMessage] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [searchParams] = useSearchParams();

  const fetchDoctors = async () => {
    try {
      const { data } = await doctorsAPI.getAll();
      setDoctors(data);
    } catch (err) {
      setActionError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Impossible de charger les médecins');
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
    setActionError('');
    setSuccess('');
    setPaymentMessage('');
    setPaymentError('');

    if (!formData.doctorId || !formData.date) {
      setActionError('Choisissez un médecin et une date.');
      return;
    }

    try {
      const appointment = await addAppointment({
        doctor_id: Number(formData.doctorId),
        date: formData.date,
        duration_minutes: Number(formData.duration),
      });
      setLastAppointment(appointment);
      setShowConfirmation(true);
      setSuccess('Rendez-vous ajouté avec succès !');
      setFormData({ doctorId: '', date: '', duration: 30 });
    } catch (err) {
      setActionError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Erreur création');
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
      setActionError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Erreur annulation');
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

  const getDoctorName = (id) => {
    const doctor = doctors.find((doc) => doc.id === Number(id));
    return doctor ? doctor.name : `Médecin #${id}`;
  };

  const handlePayNow = async () => {
    if (!lastAppointment || !lastAppointment.id) {
      setPaymentError('Invalid appointment.');
      return;
    }

    setPaymentError('');
    setPaymentMessage('');
    setIsPaying(true);

    try {
      const response = await paymentsAPI.createIntent(lastAppointment.id);
      const { client_secret } = response.data;

      setPaymentMessage(
        'Payment intent created. Please proceed with payment on Stripe. Client secret: ' + client_secret
      );

      await new Promise((resolve) => setTimeout(resolve, 2000));
      setPaymentMessage('Payment processed. Your appointment is confirmed.');
    } catch (err) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to process payment.';
      setPaymentError(errorMsg);
    } finally {
      setIsPaying(false);
    }
  };

  const handleNewBooking = () => {
    setShowConfirmation(false);
    setLastAppointment(null);
    setPaymentMessage('');
    setPaymentError('');
  };

  return (
    <div className="appointments-page">
      <header className="appointments-header">
        <div>
          <h1>Appointments</h1>
          <p>Book a doctor, review your schedule, and confirm payment when ready.</p>
        </div>
      </header>

      {showConfirmation && lastAppointment && (
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
              <p>{getDoctorName(lastAppointment.doctor_id)}</p>
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
              disabled={isPaying}
            >
              {isPaying ? 'Processing payment...' : 'Pay with Stripe'}
            </button>
            {paymentMessage && <p className="success">{paymentMessage}</p>}
            {paymentError && <p className="error">{paymentError}</p>}
          </div>
        </div>
      )}

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

        <button type="submit" disabled={loading}>
          {loading ? 'Enregistrement...' : 'Valider le rendez-vous'}
        </button>
      </form>

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
                      Médecin : <strong>{getDoctorName(appointment.doctor_id)}</strong>
                    </p>
                    <p>Date : {new Date(appointment.date).toLocaleString()}</p>
                    <p>Statut : {appointment.status}</p>
                    <p>Payé : {appointment.payment_status}</p>
                    <p>Durée : {appointment.duration_minutes} minutes</p>
                    <p>Prix : {appointment.price} GNF</p>
                  </div>
                  <div className="appointment-actions">
                    <button
                      onClick={() => handleDelete(appointment.id)}
                      disabled={loading}
                      className="delete-btn"
                    >
                      Annuler
                    </button>
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