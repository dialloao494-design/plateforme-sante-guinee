import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import AppointmentCard from '../components/AppointmentCard.jsx';
import PaymentConfirmationModal from '../components/PaymentConfirmationModal.jsx';
import { doctorsAPI, paymentsAPI } from '../services/api.js';
import { canPayAppointment, formatGNF, getPaymentLabel, getStatusMeta, isPendingAppointment } from '../utils/appointmentPresentation.js';
import { loadSimulatedPayments } from '../utils/simulatedPaymentsStorage.js';
import './Appointments.css';

const Appointments = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isPatient = user?.role === 'patient';
  const isDoctor = user?.role === 'doctor';
  const isAdmin = user?.role === 'admin';
  const { appointments, loading, error, addAppointment, deleteAppointment, fetchAppointments } = useAppointmentContext();
  const [doctors, setDoctors] = useState([]);
  const [loadingDoctors, setLoadingDoctors] = useState(false);
  const [doctorsError, setDoctorsError] = useState('');
  const [formData, setFormData] = useState({ doctorId: '', date: '', duration: 30 });
  const [selectedDoctorFilter, setSelectedDoctorFilter] = useState('');
  const [success, setSuccess] = useState('');
  const [actionError, setActionError] = useState('');
  const [lastAppointment, setLastAppointment] = useState(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isPaying, setIsPaying] = useState(false);
  const [paymentAttemptStarted, setPaymentAttemptStarted] = useState(false);
  const [paymentError, setPaymentError] = useState('');
  const [isCreatingAppointment, setIsCreatingAppointment] = useState(false);
  const [payingAppointmentId, setPayingAppointmentId] = useState(null);
  const [cancellingAppointmentId, setCancellingAppointmentId] = useState(null);
  const [paymentModalAppointment, setPaymentModalAppointment] = useState(null);
  const [searchParams] = useSearchParams();
  const [simulatedPayments, setSimulatedPayments] = useState(() => loadSimulatedPayments());

  const getApiErrorMessage = (err, fallback) => {
    if (!err?.response && /network|failed to fetch/i.test(String(err?.message || ''))) {
      return 'Erreur de connexion. Veuillez réessayer.';
    }

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
    setLoadingDoctors(true);
    setDoctorsError('');
    try {
      const { data } = await doctorsAPI.getAll();
      const fromDoctorsEndpoint = (Array.isArray(data) ? data : [])
        .map(normalizeDoctor)
        .filter(Boolean);
      setDoctors(fromDoctorsEndpoint);
    } catch (err) {
      setDoctorsError(getApiErrorMessage(err, 'Impossible de charger les médecins.'));
      setDoctors([]);
    } finally {
      setLoadingDoctors(false);
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
      const appointment = await addAppointment(payload);
      await fetchAppointments();
      setLastAppointment(appointment);
      setShowConfirmation(true);
      setSuccess('Rendez-vous créé avec succès');
      toast.success('Rendez-vous créé avec succès');
      setFormData({ doctorId: '', date: '', duration: 30 });
    } catch (err) {
      const message = getApiErrorMessage(err, 'Impossible de créer le rendez-vous.');
      setActionError(message);
      toast.error(message);
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
    setCancellingAppointmentId(id);
    try {
      await deleteAppointment(id);
      setSuccess('Rendez-vous annulé');
      toast.success('Rendez-vous annulé');
      if (lastAppointment?.id === id) {
        setLastAppointment(null);
        setShowConfirmation(false);
      }
    } catch (err) {
      const message = getApiErrorMessage(err, 'Impossible d’annuler le rendez-vous.');
      setActionError(message);
      toast.error(message);
    } finally {
      setCancellingAppointmentId(null);
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

  const withSimulatedPayment = (appointment) => {
    if (!appointment || !simulatedPayments[appointment.id]) {
      return appointment;
    }

    return {
      ...appointment,
      payment_status: 'paid',
      status: appointment.status === 'cancelled' ? 'cancelled' : 'paid',
    };
  };

  const displayedAppointments = useMemo(
    () => filteredAppointments.map(withSimulatedPayment),
    [filteredAppointments, simulatedPayments]
  );

  const displayedLastAppointment = lastAppointment ? withSimulatedPayment(lastAppointment) : null;

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

  const canCancel = (appointment) => {
    if (!user) return false;
    if (!isPendingAppointment(appointment)) return false;
    if (isAdmin) return true;
    if (isDoctor) return true;
    if (isPatient) {
      return new Date(appointment.date) > new Date();
    }
    return false;
  };

  const openPaymentModal = (appointment = lastAppointment) => {
    setPaymentError('');
    setPaymentModalAppointment(appointment);
  };

  const handleConfirmPayment = async (appointment) => {
    if (!appointment?.id) {
      setPaymentError('Rendez-vous introuvable pour le paiement.');
      return;
    }

    setIsPaying(true);
    setPayingAppointmentId(appointment.id);
    setPaymentAttemptStarted(true);

    try {
      // Call backend to mark appointment as paid
      const response = await paymentsAPI.confirmPayment(appointment.id);
      
      // Refresh appointments to get updated status from server
      await fetchAppointments();
      
      setSuccess('Paiement effectué avec succès. Le médecin confirmera le rendez-vous.');
      toast.success('Paiement validé');
      setPaymentModalAppointment(null);
      
      // Update last appointment display with response from server
      if (lastAppointment?.id === appointment.id && response?.data) {
        setLastAppointment(response.data);
      }
    } catch (err) {
      const message = getApiErrorMessage(err, 'Erreur lors de la confirmation du paiement.');
      setPaymentError(message);
      toast.error(message);
      setPaymentAttemptStarted(false);
    } finally {
      setIsPaying(false);
      setPayingAppointmentId(null);
    }
  };

  const handleNewBooking = () => {
    setShowConfirmation(false);
    setLastAppointment(null);
    setPaymentError('');
    setPaymentAttemptStarted(false);
  };

  return (
    <div className="appointments-page">
      <header className="appointments-header">
        <div>
          <h1>Rendez-vous</h1>
          <p>Planifiez vos consultations et payez via Mobile Money en toute simplicité.</p>
        </div>
      </header>

      {isPatient && showConfirmation && displayedLastAppointment && (
        <div className="confirmation-card">
          <div className="confirmation-top">
            <div>
              <p className="tag">Rendez-vous enregistré</p>
              <h2>Résumé du rendez-vous</h2>
            </div>
            <button className="button-secondary" onClick={handleNewBooking}>
              Réserver un autre
            </button>
          </div>
          <div className="confirmation-details">
            <div>
              <p className="detail-label">Médecin</p>
              <p>{getDoctorName(displayedLastAppointment)}</p>
            </div>
            <div>
              <p className="detail-label">Date et heure</p>
              <p>{new Date(displayedLastAppointment.date).toLocaleString('fr-FR')}</p>
            </div>
            <div>
              <p className="detail-label">Durée</p>
              <p>{displayedLastAppointment.duration_minutes} minutes</p>
            </div>
            <div>
              <p className="detail-label">Paiement</p>
              <p>{getPaymentLabel(displayedLastAppointment.payment_status)}</p>
            </div>
            <div>
              <p className="detail-label">Prix</p>
              <p>{formatGNF(displayedLastAppointment.price)}</p>
            </div>
            <div>
              <p className="detail-label">Statut</p>
              <span className={getStatusMeta(displayedLastAppointment.status).className}>
                {getStatusMeta(displayedLastAppointment.status).label}
              </span>
            </div>
          </div>
          <div className="confirmation-actions">
            {['paid', 'confirmed', 'completed'].includes(String(displayedLastAppointment.status || '').toLowerCase()) && (
              <button type="button" className="button-secondary" onClick={() => setShowConfirmation(false)}>
                Voir mes rendez-vous
              </button>
            )}
            {isPendingAppointment(displayedLastAppointment) && (
              <button
                type="button"
                className="button-pay"
                onClick={() => openPaymentModal(displayedLastAppointment)}
                disabled={isPaying || paymentAttemptStarted || payingAppointmentId === displayedLastAppointment.id}
              >
                {isPaying ? 'Traitement...' : 'Payer via Mobile Money'}
              </button>
            )}
            {isPendingAppointment(displayedLastAppointment) && (
              <small className="payment-helper-text">Simulation de paiement</small>
            )}
            {paymentError && <p className="error">{paymentError}</p>}
          </div>
        </div>
      )}

      {isPatient && (
      <form onSubmit={handleSubmit} className="appointment-form">
        <h2>Ajouter un rendez-vous</h2>

        <div className="form-group">
          <label>Médecin</label>
          {doctorsError && <p className="error" style={{marginBottom: '6px'}}>{doctorsError}</p>}
          <select
            value={formData.doctorId}
            onChange={(e) => setFormData((prev) => ({ ...prev, doctorId: e.target.value }))}
            required
            disabled={loadingDoctors}
          >
            <option value="">
              {loadingDoctors ? 'Chargement des médecins...' : 'Sélectionnez un médecin'}
            </option>
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

        <button type="submit" disabled={isCreatingAppointment || loadingDoctors}>
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

          {displayedAppointments.length > 0 && (
            <ul className="appointments-cards">
              {displayedAppointments.map((appointment) => (
                <AppointmentCard
                  key={appointment.id}
                  appointment={appointment}
                  title={getDoctorName(appointment)}
                  onPay={openPaymentModal}
                  onCancel={(item) => handleDelete(item.id)}
                  onOpenMessages={(item) => navigate(`/messages/${item.id}`)}
                  canPay={canPayAppointment(appointment)}
                  canCancel={canCancel(appointment)}
                  canMessage={Boolean(appointment?.id) && (isPatient || isDoctor)}
                  isPaying={isPaying && payingAppointmentId === appointment.id}
                  isCancelling={cancellingAppointmentId === appointment.id}
                />
              ))}
            </ul>
          )}
        </div>
      </div>

      <PaymentConfirmationModal
        isOpen={Boolean(paymentModalAppointment)}
        appointment={paymentModalAppointment}
        onConfirm={handleConfirmPayment}
        onClose={() => setPaymentModalAppointment(null)}
        isProcessing={isPaying}
      />
    </div>
  );
};

export default Appointments;