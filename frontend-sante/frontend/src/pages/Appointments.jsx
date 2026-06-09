import { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import AppointmentCard from '../components/AppointmentCard.jsx';
import AppointmentActions from '../components/AppointmentActions.jsx';
import PaymentConfirmationModal from '../components/PaymentConfirmationModal.jsx';
import { doctorsAPI, paymentsAPI } from '../services/api.js';
import { createCheckoutForAppointment } from '../services/paymentFlow.js';
import {
  formatGNF,
  getAppointmentState,
  getAppointmentActions,
} from '../utils/appointmentPresentation.js';
import { loadSimulatedPayments } from '../utils/simulatedPaymentsStorage.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import './Appointments.css';

function normalizeDoctor(item) {
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
}

const Appointments = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const isPatient = user?.role === 'patient';
  const { appointments, loading, error, addAppointment, deleteAppointment, fetchAppointments } = useAppointmentContext();
  const [doctors, setDoctors] = useState([]);
  const [loadingDoctors, setLoadingDoctors] = useState(false);
  const [doctorsError, setDoctorsError] = useState('');
  const [formData, setFormData] = useState({ doctorId: '', date: '', duration: 30, consultationType: 'physical' });
  const [selectedDoctorFilter, setSelectedDoctorFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
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
  const SIM_ENABLED = import.meta.env.VITE_ENABLE_PAYMENT_SIMULATION === 'true';
  const PAYMENT_STUB_TOKEN = import.meta.env.VITE_PAYMENT_STUB_TOKEN || '';
  const [simulatedPayments] = useState(() => (SIM_ENABLED ? loadSimulatedPayments() : {}));
  const [paymentRows, setPaymentRows] = useState([]);
  const [loadingPaymentHistory, setLoadingPaymentHistory] = useState(false);

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

  const fetchDoctors = useCallback(async () => {
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
  }, []);

  const fetchPaymentHistory = useCallback(async () => {
    if (!isPatient) return;
    setLoadingPaymentHistory(true);
    try {
      const { data } = await paymentsAPI.list();
      setPaymentRows(Array.isArray(data) ? data : []);
    } catch {
      setPaymentRows([]);
    } finally {
      setLoadingPaymentHistory(false);
    }
  }, [isPatient]);

  useEffect(() => {
    void fetchDoctors();
  }, [fetchDoctors]);

  useEffect(() => {
    void fetchPaymentHistory();
  }, [fetchPaymentHistory]);

  useEffect(() => {
    const fromQuery = searchParams.get('doctor_id');
    const fromState = location.state?.doctorId;
    const raw = fromQuery || (fromState != null ? String(fromState) : '');
    if (raw) {
      setFormData((prev) => ({ ...prev, doctorId: String(raw) }));
    }
  }, [searchParams, location.state]);

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
        consultation_type: formData.consultationType,
      };
      const appointment = await addAppointment(payload);
      await fetchAppointments();
      setLastAppointment(appointment);
      setShowConfirmation(true);
      setSuccess('Rendez-vous créé avec succès');
      toast.success('Rendez-vous créé avec succès');
      setFormData({ doctorId: '', date: '', duration: 30, consultationType: 'physical' });
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
      await fetchPaymentHistory();
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

  const getDoctorName = useCallback(
    (appointmentOrId) => {
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

      const id =
        typeof appointmentOrId === 'object' && appointmentOrId !== null
          ? appointmentOrId.doctor_id
          : appointmentOrId;

      const doctor = doctors.find((doc) => doc.id === Number(id));
      if (!doctor) {
        return `Dr #${id}`;
      }
      return doctor.name;
    },
    [doctors]
  );

  const filteredAppointments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return appointments.filter((appointment) => {
      if (selectedDoctorFilter && String(appointment.doctor_id) !== selectedDoctorFilter) {
        return false;
      }
      if (!q) return true;
      const doctorLabel = getDoctorName(appointment).toLowerCase();
      const dateStr = new Date(appointment.date).toLocaleString('fr-FR').toLowerCase();
      return doctorLabel.includes(q) || dateStr.includes(q) || String(appointment.id).includes(q);
    });
  }, [appointments, selectedDoctorFilter, searchQuery, getDoctorName]);

  const withSimulatedPayment = useCallback(
    (appointment) => {
      if (!appointment || !simulatedPayments[appointment.id]) {
        return appointment;
      }

      return {
        ...appointment,
        payment_status: 'paid',
        status: 'confirmed',
      };
    },
    [simulatedPayments]
  );

  const displayedAppointments = useMemo(
    () => filteredAppointments.map(withSimulatedPayment),
    [filteredAppointments, withSimulatedPayment]
  );

  const resolveForUser = (appointment) => getAppointmentState(appointment);

  const displayedLastAppointment = lastAppointment ? withSimulatedPayment(lastAppointment) : null;
  const displayedLastPresentation = displayedLastAppointment ? resolveForUser(displayedLastAppointment) : null;
  const displayedLastActions = displayedLastAppointment ? getAppointmentActions(displayedLastAppointment) : [];

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
      if (SIM_ENABLED) {
        if (!PAYMENT_STUB_TOKEN) {
          throw new Error(
            'Simulation de paiement : définissez VITE_PAYMENT_STUB_TOKEN (aligné sur PAYMENT_STUB_TOKEN backend).'
          );
        }
        const response = await paymentsAPI.confirmPayment(appointment.id, PAYMENT_STUB_TOKEN);
        await fetchAppointments();
        await fetchPaymentHistory();
        setSuccess('Paiement simulé validé côté serveur.');
        toast.success('Paiement validé (mode démo)');
        setPaymentModalAppointment(null);
        if (lastAppointment?.id === appointment.id && response?.data) {
          setLastAppointment(response.data);
        }
        return;
      }

      const checkoutUrl = await createCheckoutForAppointment(appointment);
      window.location.assign(checkoutUrl);
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
              <p>{displayedLastPresentation?.paymentLabel}</p>
            </div>
            <div>
              <p className="detail-label">Prix</p>
              <p>{formatGNF(displayedLastAppointment.price)}</p>
            </div>
            <div>
              <p className="detail-label">Statut</p>
              <span className={displayedLastPresentation?.statusColor}>
                {displayedLastPresentation?.displayStatus}
              </span>
            </div>
          </div>
          <AppointmentActions
            actions={displayedLastActions}
            appointment={displayedLastAppointment}
            onPay={openPaymentModal}
            onCancel={handleDelete}
            onOpenMessages={(item) => navigate(`/messages/${item.id}`)}
            onJoinConsultation={(item) => navigate(`/consultation/${item.id}`)}
            isPaying={isPaying || paymentAttemptStarted || payingAppointmentId === displayedLastAppointment.id}
            isCancelling={false}
          />
          {paymentError && <p className="error">{paymentError}</p>}
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

        <div className="form-group">
          <label>Type de consultation</label>
          <select
            value={formData.consultationType}
            onChange={(e) => setFormData((prev) => ({ ...prev, consultationType: e.target.value }))}
            required
          >
            <option value="physical">Consultation physique</option>
            <option value="teleconsultation">Téléconsultation</option>
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
            <div className="appointments-filters-row">
              <div className="appointments-search">
                <label htmlFor="appt-search" className="visually-hidden">
                  Rechercher
                </label>
                <input
                  id="appt-search"
                  type="search"
                  placeholder="Rechercher (médecin, date, n°)…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoComplete="off"
                />
              </div>
              <div className="appointments-filter">
                <label htmlFor="appt-doctor-filter">Médecin</label>
                <select
                  id="appt-doctor-filter"
                  value={selectedDoctorFilter}
                  onChange={(e) => setSelectedDoctorFilter(e.target.value)}
                >
                  <option value="">Tous</option>
                  {doctorOptions.map((doctor) => (
                    <option key={doctor.id} value={doctor.id}>
                      {doctor.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {loading && <PageSkeleton lines={6} />}

          {!loading && appointments.length === 0 && (
            <EmptyState
              preset="calendar"
              title="Aucun rendez-vous"
              description="Vos consultations passées et à venir s’affichent ici. Prenez rendez-vous avec un médecin partenaire en quelques clics."
              actionLabel="Réserver une consultation"
              onAction={() => navigate('/doctors')}
            />
          )}

          {!loading && appointments.length > 0 && displayedAppointments.length === 0 && (
            <EmptyState
              preset="clipboard"
              title="Aucun résultat"
              description="Ajustez la recherche ou le filtre médecin pour afficher d’autres rendez-vous."
            />
          )}

          {displayedAppointments.length > 0 && (
            <ul className="appointments-cards">
              {displayedAppointments.map((appointment) => {
                const presentation = resolveForUser(appointment);
                const actions = getAppointmentActions(appointment);
                return (
                  <AppointmentCard
                    key={appointment.id}
                    appointment={appointment}
                    title={getDoctorName(appointment)}
                    onPay={openPaymentModal}
                    onCancel={(item) => handleDelete(item.id)}
                    onOpenMessages={(item) => navigate(`/messages/${item.id}`)}
                    onJoinConsultation={(item) => navigate(`/consultation/${item.id}`)}
                    presentation={presentation}
                    actions={actions}
                    isPaying={isPaying && payingAppointmentId === appointment.id}
                    isCancelling={cancellingAppointmentId === appointment.id}
                  />
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {isPatient && (
        <section className="appointments-payment-history" aria-labelledby="payment-history-title">
          <h2 id="payment-history-title">Historique paiements &amp; rendez-vous</h2>
          <p className="appointments-payment-history-lead">
            Liste renvoyée par l’API (même périmètre que vos rendez-vous) — utile pour contrôler statut de paiement et
            suivi cabinet.
          </p>
          {loadingPaymentHistory && <PageSkeleton lines={4} />}
          {!loadingPaymentHistory && paymentRows.length === 0 && (
            <p className="appointments-muted">Aucun enregistrement pour le moment.</p>
          )}
          {!loadingPaymentHistory && paymentRows.length > 0 && (
            <div className="appointments-payment-table-wrap">
              <table className="appointments-payment-table">
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Médecin</th>
                    <th scope="col">Montant</th>
                    <th scope="col">Paiement</th>
                    <th scope="col">Statut RDV</th>
                  </tr>
                </thead>
                <tbody>
                  {paymentRows.map((row) => (
                    <tr key={row.id}>
                      <td>{new Date(row.date).toLocaleString('fr-FR')}</td>
                      <td>{getDoctorName(row)}</td>
                      <td>{formatGNF(row.price)}</td>
                      <td>{String(row.payment_status || '—')}</td>
                      <td>{String(row.status || '—')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

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