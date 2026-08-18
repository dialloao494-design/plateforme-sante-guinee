import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import { userCanManageHospitalBeds } from '../../utils/clinicAccess.js';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import PatientSafetyStrip from '../../components/clinical/PatientSafetyStrip.jsx';
import { useClinicalPatientRoute } from '../../hooks/useClinicalPatientRoute.js';

import './clinical.css';

const STATUS_LABELS = {
  pending: 'En attente',
  admitted: 'Admis',
  in_care: 'Soins',
  transferred: 'Transféré',
  discharged: 'Sorti',
  cancelled: 'Annulé',
};

export default function HospitalizationDashboard() {
  const { user } = useAuth();
  const { patientId: routePatientId, setPatientId: setRoutePatientId } = useClinicalPatientRoute();
  const closingPatientIdRef = useRef('');
  const canManageBeds = userCanManageHospitalBeds(user?.role || user?.user_role);
  const [occupancy, setOccupancy] = useState(null);
  const [hospStats, setHospStats] = useState(null);
  const [admissions, setAdmissions] = useState([]);
  const [beds, setBeds] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [selectedAdmission, setSelectedAdmission] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [selectedBedId, setSelectedBedId] = useState('');
  const [transferReason, setTransferReason] = useState('');
  const [roomForm, setRoomForm] = useState({ ward_name: 'Médecine', room_number: '', room_type: 'general', capacity: 2 });
  const [bedForm, setBedForm] = useState({ room_id: '', bed_number: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [admitForm, setAdmitForm] = useState({ patient_id: '', diagnosis_summary: '', reason: '' });
  const [dischargeOutcome, setDischargeOutcome] = useState('cured');

  const load = useCallback(async () => {
    try {
      const [occRes, admRes, bedRes, roomRes, dashRes] = await Promise.all([
        clinicalApi.hospitalOccupancy(),
        clinicalApi.hospitalAdmissions(),
        clinicalApi.hospitalBeds(),
        clinicalApi.hospitalRooms(),
        clinicalApi.hospitalDashboard(),
      ]);
      setOccupancy(occRes.data);
      setHospStats(dashRes.data);
      setAdmissions(admRes.data || []);
      setBeds(bedRes.data || []);
      setRooms(roomRes.data || []);
      setError('');
    } catch (err) {
      setError(formatApiError(err, 'Hospitalisation indisponible'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!routePatientId) return;
    if (closingPatientIdRef.current === routePatientId || String(selectedPatient?.id || '') === routePatientId) return;
    clinicalApi.patientTimeline(routePatientId)
      .then(({ data }) => {
        const patient = data?.patient || null;
        setSelectedPatient(patient);
        setAdmitForm((current) => ({ ...current, patient_id: patient ? String(patient.id) : '' }));
      })
      .catch((err) => setError(formatApiError(err, 'Patient indisponible')));
  }, [routePatientId, selectedPatient?.id]);

  const selectPatient = (patient) => {
    closingPatientIdRef.current = '';
    setSelectedPatient(patient);
    setAdmitForm((current) => ({ ...current, patient_id: String(patient.id) }));
    setPatientMatches([]);
    setRoutePatientId(patient.id);
  };

  const closePatient = () => {
    closingPatientIdRef.current = String(selectedPatient?.id || routePatientId || '');
    setSelectedPatient(null);
    setAdmitForm((current) => ({ ...current, patient_id: '' }));
    setRoutePatientId('');
  };

  const stats = hospStats
    ? [
        { label: 'Hospitalisés actuellement', value: hospStats.current_hospitalized, variant: 'warning' },
        { label: 'Admissions ce mois', value: hospStats.admissions_this_month, variant: 'accent' },
        { label: 'Sorties ce mois', value: hospStats.discharges_this_month },
        { label: 'Durée moy. séjour (j)', value: hospStats.average_length_of_stay_days, variant: 'success' },
      ]
    : occupancy
    ? [
        { label: 'Lits totaux', value: occupancy.total_beds, hint: 'Capacité' },
        { label: 'Occupés', value: occupancy.occupied_beds, hint: `${occupancy.occupancy_rate}%`, variant: 'warning' },
        { label: 'Disponibles', value: occupancy.available_beds, hint: 'Libres', variant: 'success' },
        { label: 'Admissions actives', value: occupancy.active_admissions, hint: `${occupancy.pending_admissions} en attente` },
      ]
    : [];

  const assignBed = async () => {
    if (!selectedAdmission || !selectedBedId) return;
    try {
      await clinicalApi.assignBed(selectedAdmission.id, {
        bed_id: Number(selectedBedId),
        transfer_reason: transferReason || undefined,
      });
      setMessage('Lit assigné avec succès');
      setTransferReason('');
      setSelectedBedId('');
      setSelectedAdmission(null);
      load();
    } catch (err) {
      setError(formatApiError(err, 'Assignation impossible'));
    }
  };

  const updateStatus = async (admissionId, status) => {
    try {
      const payload = { status };
      if (status === 'discharged') {
        payload.outcome = dischargeOutcome;
      }
      await clinicalApi.updateAdmissionStatus(admissionId, payload);
      setMessage(`Statut mis à jour : ${STATUS_LABELS[status]}`);
      load();
    } catch (err) {
      setError(formatApiError(err, 'Mise à jour impossible'));
    }
  };

  const searchPatients = async () => {
    if (patientSearch.trim().length < 2) return;
    try {
      const { data } = await clinicalApi.searchPatients(patientSearch.trim());
      setPatientMatches(data || []);
    } catch (err) {
      setError(formatApiError(err, 'Recherche impossible'));
    }
  };

  const admitPatient = async (e) => {
    e.preventDefault();
    if (!admitForm.patient_id) return;
    try {
      await clinicalApi.createAdmission({
        patient_id: Number(admitForm.patient_id),
        diagnosis_summary: admitForm.diagnosis_summary || null,
        reason: admitForm.reason || null,
      });
      setMessage('Admission créée');
      setAdmitForm({ patient_id: '', diagnosis_summary: '', reason: '' });
      setSelectedPatient(null);
      setRoutePatientId('');
      setPatientMatches([]);
      load();
    } catch (err) {
      setError(formatApiError(err, 'Admission impossible'));
    }
  };

  const createRoom = async (e) => {
    e.preventDefault();
    try {
      await clinicalApi.createHospitalRoom(roomForm);
      setMessage('Chambre créée');
      setRoomForm({ ...roomForm, room_number: '' });
      load();
    } catch (err) {
      setError(formatApiError(err, 'Création chambre impossible'));
    }
  };

  const addBed = async (e) => {
    e.preventDefault();
    if (!bedForm.room_id) return;
    try {
      await clinicalApi.addHospitalBed(bedForm.room_id, { bed_number: bedForm.bed_number });
      setMessage('Lit ajouté');
      setBedForm({ ...bedForm, bed_number: '' });
      load();
    } catch (err) {
      setError(formatApiError(err, 'Ajout lit impossible'));
    }
  };

  const availableBeds = beds.filter((b) => b.status === 'available' || b.status === 'reserved');

  return (
    <div className="clinical-page" data-testid="hospitalization-dashboard">
      <header className="clinical-header">
        <h1>Hospitalisation</h1>
        <p>Admissions, lits et occupation — pilotage du service.</p>
      </header>

      {error && <div className="clinical-alert clinical-alert--error">{String(error)}</div>}
      {message && <div className="clinical-alert clinical-alert--success">{message}</div>}
      <PatientSafetyStrip patient={selectedPatient} onClose={closePatient} contextLabel="Patient actif en hospitalisation" />

      <ClinicalStatGrid stats={stats} />

      <section className="clinical-panel">
        <h2>Admettre un patient</h2>
        <form className="clinical-form-grid" onSubmit={admitPatient}>
          <label className="clinical-span-2">
            Rechercher patient
            <div className="clinical-inline-form">
              <input
                type="search"
                value={patientSearch}
                onChange={(e) => setPatientSearch(e.target.value)}
                placeholder="Nom ou téléphone"
              />
              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={searchPatients}>
                Rechercher
              </button>
            </div>
          </label>
          {patientMatches.length > 0 && (
            <ul className="clinical-list clinical-span-2" aria-label="Résultats patients">
              {patientMatches.map((patient) => (
                <li key={patient.id}>
                  <button type="button" className="clinical-link-btn" onClick={() => selectPatient(patient)}>
                    {patient.first_name} {patient.last_name} — {patient.phone || 'sans téléphone'}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <label>
            Diagnostic
            <input
              value={admitForm.diagnosis_summary}
              onChange={(e) => setAdmitForm({ ...admitForm, diagnosis_summary: e.target.value })}
            />
          </label>
          <label>
            Motif admission
            <input value={admitForm.reason} onChange={(e) => setAdmitForm({ ...admitForm, reason: e.target.value })} />
          </label>
          <button type="submit" className="clinical-btn">Créer admission</button>
        </form>
      </section>

      <div className="clinical-grid clinical-grid--2">
        <section className="clinical-panel">
          <h2>Admissions en cours</h2>
          <ul className="clinical-queue">
            {admissions.filter((a) => !['discharged', 'cancelled'].includes(a.status)).length === 0 && (
              <li>Aucune admission active.</li>
            )}
            {admissions
              .filter((a) => !['discharged', 'cancelled'].includes(a.status))
              .map((a) => (
                <li key={a.id} className={selectedAdmission?.id === a.id ? 'clinical-queue-item--active' : ''}>
                  <div>
                    <strong>{a.patient_name}</strong>
                    <span className="clinical-badge">{a.admission_number}</span>
                    <span className="clinical-badge clinical-badge--muted">{STATUS_LABELS[a.status] || a.status}</span>
                    {a.current_bed && (
                      <small>
                        {a.current_bed.ward_name} — {a.current_bed.room_number} / {a.current_bed.bed_number}
                      </small>
                    )}
                  </div>
                  <div className="clinical-actions">
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectPatient({
                      id: a.patient_id,
                      patient_number: a.patient_number,
                      full_name: a.patient_name,
                    })}>
                      Ouvrir le dossier
                    </button>
                    <button type="button" className="clinical-btn" onClick={() => setSelectedAdmission(a)}>
                      Assigner lit
                    </button>
                    {a.status !== 'in_care' && (
                      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => updateStatus(a.id, 'in_care')}>
                        Soins
                      </button>
                    )}
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => updateStatus(a.id, 'discharged')}>
                      Sortir
                    </button>
                  </div>
                  {a.diagnosis_summary && <small>Diagnostic : {a.diagnosis_summary}</small>}
                  {a.length_of_stay_days != null && <small>Durée séjour : {a.length_of_stay_days} j</small>}
                </li>
              ))}
          </ul>
        </section>

        <section className="clinical-panel">
          <h2>Assignation / transfert de lit</h2>
          <label>
            Issue à la sortie
            <select value={dischargeOutcome} onChange={(e) => setDischargeOutcome(e.target.value)}>
              <option value="cured">Guéri</option>
              <option value="improved">Amélioré</option>
              <option value="unchanged">Inchangé</option>
              <option value="transferred">Transféré</option>
              <option value="deceased">Décédé</option>
              <option value="left_against_advice">Sortie contre avis</option>
            </select>
          </label>
          {selectedAdmission ? (
            <>
              <p>
                Patient : <strong>{selectedAdmission.patient_name}</strong> ({selectedAdmission.admission_number})
              </p>
              <label>
                Lit disponible
                <select value={selectedBedId} onChange={(e) => setSelectedBedId(e.target.value)}>
                  <option value="">— Choisir —</option>
                  {availableBeds.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.ward_name} / {b.room_number} — Lit {b.bed_number}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Motif transfert (optionnel)
                <input value={transferReason} onChange={(e) => setTransferReason(e.target.value)} />
              </label>
              <button type="button" className="clinical-btn" onClick={assignBed}>
                Confirmer assignation
              </button>
            </>
          ) : (
            <p>Sélectionnez une admission pour assigner ou transférer un lit.</p>
          )}
        </section>
      </div>

      <section className="clinical-panel">
        <h2>Plan des lits</h2>
        <div className="clinical-bed-grid">
          {beds.map((b) => (
            <div key={b.id} className={`clinical-bed-card clinical-bed-card--${b.status}`}>
              <span className="clinical-bed-card__num">{b.bed_number}</span>
              <span>{b.ward_name}</span>
              <span>{b.room_number}</span>
              <span className="clinical-badge">{b.status}</span>
            </div>
          ))}
          {beds.length === 0 && <p>Aucun lit configuré — créez des chambres ci-dessous.</p>}
        </div>
      </section>

      {canManageBeds && (
      <div className="clinical-grid clinical-grid--2">
        <section className="clinical-panel">
          <h2>Nouvelle chambre (admin)</h2>
          <form onSubmit={createRoom} className="clinical-form">
            <label>
              Service
              <input value={roomForm.ward_name} onChange={(e) => setRoomForm({ ...roomForm, ward_name: e.target.value })} required />
            </label>
            <label>
              Numéro chambre
              <input value={roomForm.room_number} onChange={(e) => setRoomForm({ ...roomForm, room_number: e.target.value })} required />
            </label>
            <label>
              Type
              <select value={roomForm.room_type} onChange={(e) => setRoomForm({ ...roomForm, room_type: e.target.value })}>
                <option value="general">Général</option>
                <option value="private">Privée</option>
                <option value="icu">Réanimation</option>
                <option value="maternity">Maternité</option>
              </select>
            </label>
            <label>
              Capacité
              <input type="number" min="1" value={roomForm.capacity} onChange={(e) => setRoomForm({ ...roomForm, capacity: Number(e.target.value) })} />
            </label>
            <button type="submit" className="clinical-btn">Créer chambre</button>
          </form>
        </section>

        <section className="clinical-panel">
          <h2>Ajouter un lit (admin)</h2>
          <form onSubmit={addBed} className="clinical-form">
            <label>
              Chambre
              <select value={bedForm.room_id} onChange={(e) => setBedForm({ ...bedForm, room_id: e.target.value })} required>
                <option value="">— Choisir —</option>
                {rooms.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.ward_name} — {r.room_number}
                  </option>
                ))}
              </select>
              {rooms.length === 0 && (
                <span className="clinical-stat-hint">
                  Aucune chambre configurée — créez d&apos;abord une chambre ci-contre.
                </span>
              )}
            </label>
            <label>
              Numéro lit
              <input value={bedForm.bed_number} onChange={(e) => setBedForm({ ...bedForm, bed_number: e.target.value })} required />
            </label>
            <button type="submit" className="clinical-btn">Ajouter lit</button>
          </form>
        </section>
      </div>
      )}
    </div>
  );
}
