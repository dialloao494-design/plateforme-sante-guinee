import { useEffect, useMemo, useState, useCallback } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import AppointmentCard from '../components/AppointmentCard.jsx';
import AppointmentActions from '../components/AppointmentActions.jsx';
import { doctorsAPI } from '../services/api.js';
import {
  formatGNF,
  getAppointmentState,
  getAppointmentActions,
} from '../utils/appointmentPresentation.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import { useConfirm } from '../contexts/ConfirmContext.jsx';
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
  const confirm = useConfirm();
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
  const [isCreatingAppointment, setIsCreatingAppointment] = useState(false);
  const [cancellingAppointmentId, setCancellingAppointmentId] = useState(null);
  const [searchParams] = useSearchParams();

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

  useEffect(() => {
    void fetchDoctors();
  }, [fetchDoctors]);

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
    const accepted = await confirm({
      title: 'Annuler ce rendez-vous ?',
      message: 'Le rendez-vous sera marqué comme annulé et retiré de la file active.',
      confirmLabel: 'Annuler le rendez-vous',
    });
    if (!accepted) return;

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

  const resolveForUser = (appointment) => getAppointmentState(appointment);
  const displayedLastPresentation = lastAppointment ? resolveForUser(lastAppointment) : null;
  const displayedLastActions = lastAppointment ? getAppointmentActions(lastAppointment) : [];

  const handleNewBooking = () => {
    setShowConfirmation(false);
    setLastAppointment(null);
  };

  return (
    <div className="appointments-page">
      <header className="appointments-header">
        <div>
          <h1>Rendez-vous</h1>
          <p>Planifiez vos consultations — le paiement se fait à la caisse de la clinique.</p>
        </div>
      </header>

      {isPatient && showConfirmation && lastAppointment && (
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
              <p>{getDoctorName(lastAppointment)}</p>
            </div>
            <div>
              <p className="detail-label">Date et heure</p>
              <p>{new Date(lastAppointment.date).toLocaleString('fr-FR')}</p>
            </div>
            <div>
              <p className="detail-label">Durée</p>
              <p>{lastAppointment.duration_minutes} minutes</p>
            </div>
            <div>
              <p className="detail-label">Prix indicatif</p>
              <p>{formatGNF(lastAppointment.price)}</p>
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
            appointment={lastAppointment}
            onCancel={handleDelete}
            onOpenMessages={(item) => navigate(`/messages/${item.id}`)}
            onJoinConsultation={(item) => navigate(`/consultation/${item.id}`)}
            isCancelling={false}
          />
        </div>
      )}

      {isPatient && (
      <form onSubmit={handleSubmit} className="appointment-form">
        <h2>Ajouter un rendez-vous</h2>

        <div className="form-group">
          <label htmlFor="appointment-doctor">Médecin</label>
          {doctorsError && <p className="error" style={{marginBottom: '6px'}}>{doctorsError}</p>}
          <select
            id="appointment-doctor"
            name="doctor_id"
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
          <label htmlFor="appointment-date">Date et heure</label>
          <input
            id="appointment-date"
            name="appointment_date"
            type="datetime-local"
            value={formData.date}
            onChange={(e) => setFormData((prev) => ({ ...prev, date: e.target.value }))}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="appointment-duration">Durée (minutes)</label>
          <select
            id="appointment-duration"
            name="duration_minutes"
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
          <label htmlFor="appointment-type">Type de consultation</label>
          <select
            id="appointment-type"
            name="consultation_type"
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

          {!loading && appointments.length > 0 && filteredAppointments.length === 0 && (
            <EmptyState
              preset="clipboard"
              title="Aucun résultat"
              description="Ajustez la recherche ou le filtre médecin pour afficher d’autres rendez-vous."
            />
          )}

          {filteredAppointments.length > 0 && (
            <ul className="appointments-cards">
              {filteredAppointments.map((appointment) => {
                const presentation = resolveForUser(appointment);
                const actions = getAppointmentActions(appointment);
                return (
                  <AppointmentCard
                    key={appointment.id}
                    appointment={appointment}
                    title={getDoctorName(appointment)}
                    onCancel={(item) => handleDelete(item.id)}
                    onOpenMessages={(item) => navigate(`/messages/${item.id}`)}
                    onJoinConsultation={(item) => navigate(`/consultation/${item.id}`)}
                    presentation={presentation}
                    actions={actions}
                    isCancelling={cancellingAppointmentId === appointment.id}
                  />
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default Appointments;
