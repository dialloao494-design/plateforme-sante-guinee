import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import { userCanManageHospitalBeds } from '../../utils/clinicAccess.js';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import PatientSafetyStrip from '../../components/clinical/PatientSafetyStrip.jsx';
import ClinicalFeedback from '../../components/clinical/ClinicalFeedback.jsx';
import { useClinicalPatientRoute } from '../../hooks/useClinicalPatientRoute.js';
import WardCensusBoard from './hospitalization/WardCensusBoard.jsx';
import WardConfiguration from './hospitalization/WardConfiguration.jsx';

import './clinical.css';
import './hospitalization/hospitalization.css';

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
  const [board, setBoard] = useState(null);
  const [wards, setWards] = useState([]);
  const [activeView, setActiveView] = useState('census');
  const [hospStats, setHospStats] = useState(null);
  const [admissions, setAdmissions] = useState([]);
  const [beds, setBeds] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [selectedAdmission, setSelectedAdmission] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [selectedBedId, setSelectedBedId] = useState('');
  const [transferReason, setTransferReason] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [admitForm, setAdmitForm] = useState({ patient_id: '', diagnosis_summary: '', reason: '', expected_discharge_at: '', placement_age_group: 'adult', requires_isolation: false, requires_accessible: false });
  const [dischargeOutcome, setDischargeOutcome] = useState('cured');

  const load = useCallback(async () => {
    const results = await Promise.allSettled([
        clinicalApi.hospitalOccupancy(),
        clinicalApi.hospitalAdmissions(),
        clinicalApi.hospitalBeds(),
        clinicalApi.hospitalRooms(),
        clinicalApi.hospitalDashboard(),
        clinicalApi.hospitalWardBoard(),
        clinicalApi.hospitalWards(),
      ]);
    const value = (index) => results[index].status === 'fulfilled' ? results[index].value.data : undefined;
    if (value(0)) setOccupancy(value(0));
    if (value(1)) setAdmissions(value(1) || []);
    if (value(2)) setBeds(value(2) || []);
    if (value(3)) setRooms(value(3) || []);
    if (value(4)) setHospStats(value(4));
    if (value(5)) setBoard(value(5));
    if (value(6)) setWards(value(6) || []);
    if (results.some((result) => result.status === 'fulfilled')) {
      setError('');
    } else {
      setError(formatApiError(results[0].reason, 'Hospitalisation indisponible hors ligne. Connectez-vous une fois pour préparer ce poste.'));
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
      const response = await clinicalApi.assignBed(selectedAdmission.id, {
        bed_id: Number(selectedBedId),
        expected_bed_version: beds.find((bed) => bed.id === Number(selectedBedId))?.version,
        transfer_reason: transferReason || undefined,
      });
      setMessage(response.data?._offline_queued
        ? 'Placement enregistré hors ligne. Il sera vérifié à la synchronisation avant de devenir définitif.'
        : 'Lit assigné avec succès');
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
        expected_discharge_at: admitForm.expected_discharge_at || null,
        placement_age_group: admitForm.placement_age_group,
        requires_isolation: admitForm.requires_isolation,
        requires_accessible: admitForm.requires_accessible,
      });
      setMessage('Admission créée');
      setAdmitForm({ patient_id: '', diagnosis_summary: '', reason: '', expected_discharge_at: '', placement_age_group: 'adult', requires_isolation: false, requires_accessible: false });
      setSelectedPatient(null);
      setRoutePatientId('');
      setPatientMatches([]);
      load();
    } catch (err) {
      setError(formatApiError(err, 'Admission impossible'));
    }
  };

  const createWardConfig = async (payload) => {
    try { await clinicalApi.createHospitalWard(payload); setMessage('Service créé'); await load(); }
    catch (err) { setError(formatApiError(err, 'Création du service impossible')); throw err; }
  };

  const createRoomConfig = async (payload) => {
    try { await clinicalApi.createHospitalRoom({ ...payload, ward_id: Number(payload.ward_id) }); setMessage('Chambre créée'); await load(); }
    catch (err) { setError(formatApiError(err, 'Création de la chambre impossible')); throw err; }
  };

  const addBedConfig = async (payload) => {
    try {
      const { room_id, ...data } = payload;
      await clinicalApi.addHospitalBed(Number(room_id), data);
      setMessage(payload.accommodation_type === 'cradle' ? 'Berceau ajouté' : 'Lit ajouté');
      await load();
    } catch (err) { setError(formatApiError(err, 'Ajout du couchage impossible')); throw err; }
  };

  const markBedReady = async (bed) => {
    try {
      await clinicalApi.updateHospitalBed(bed.id, { status: 'available', reason: 'Nettoyage terminé', expected_version: bed.version });
      setMessage(`${bed.accommodation_type === 'cradle' ? 'Berceau' : 'Lit'} ${bed.bed_number} disponible`);
      await load();
    } catch (err) { setError(formatApiError(err, 'Mise à disposition impossible')); }
  };

  const focusAdmission = (admissionId) => {
    const admission = admissions.find((item) => item.id === admissionId);
    if (admission) { setSelectedAdmission(admission); setActiveView('workflow'); }
  };

  const availableBeds = beds.filter((bed) => {
    if (!['available', 'reserved'].includes(bed.status)) return false;
    if (!selectedAdmission) return true;
    if (selectedAdmission.placement_age_group === 'newborn' && !bed.newborn_suitable) return false;
    if (selectedAdmission.placement_age_group === 'pediatric' && !bed.pediatric_suitable) return false;
    if (selectedAdmission.requires_isolation && !bed.isolation_suitable) return false;
    if (selectedAdmission.requires_accessible && !bed.accessible) return false;
    return true;
  });

  return (
    <div className="clinical-page hospitalization-page" data-testid="hospitalization-dashboard">
      <header className="clinical-header">
        <h1>Hospitalisation</h1>
        <p>Admissions, lits et occupation — pilotage du service.</p>
      </header>

      <ClinicalFeedback error={error} message={message} />
      <nav className="hospitalization-toolbar" aria-label="Sections hospitalisation">
        <div className="hospitalization-toolbar__tabs" role="tablist">
          <button type="button" role="tab" aria-selected={activeView === 'census'} onClick={() => setActiveView('census')}>Plan des lits</button>
          <button type="button" role="tab" aria-selected={activeView === 'workflow'} onClick={() => setActiveView('workflow')}>Admissions et transferts</button>
          {canManageBeds && <button type="button" role="tab" aria-selected={activeView === 'configuration'} onClick={() => setActiveView('configuration')}>Configuration</button>}
        </div>
        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={load}>Actualiser le census</button>
      </nav>
      <PatientSafetyStrip patient={selectedPatient} onClose={closePatient} contextLabel="Patient actif en hospitalisation" />

      <ClinicalStatGrid stats={stats} />

      {activeView === 'census' && <WardCensusBoard board={board} canManageBeds={canManageBeds} onSelectAdmission={focusAdmission} onMarkReady={markBedReady} />}

      {activeView === 'workflow' && <>
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
          <label>
            Sortie prévue
            <input type="datetime-local" value={admitForm.expected_discharge_at} onChange={(e) => setAdmitForm({ ...admitForm, expected_discharge_at: e.target.value })} />
          </label>
          <label>
            Groupe de placement
            <select value={admitForm.placement_age_group} onChange={(e) => setAdmitForm({ ...admitForm, placement_age_group: e.target.value })}>
              <option value="adult">Adulte</option><option value="pediatric">Enfant</option><option value="newborn">Nouveau-né</option>
            </select>
          </label>
          <div className="clinical-span-2 clinical-actions">
            <label><input type="checkbox" checked={admitForm.requires_isolation} onChange={(e) => setAdmitForm({ ...admitForm, requires_isolation: e.target.checked })} /> Isolement requis</label>
            <label><input type="checkbox" checked={admitForm.requires_accessible} onChange={(e) => setAdmitForm({ ...admitForm, requires_accessible: e.target.checked })} /> Accès adapté requis</label>
          </div>
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
                      {b.accommodation_type === 'cradle' ? ' · Berceau' : ''}
                    </option>
                  ))}
                </select>
                {availableBeds.length === 0 && <span className="clinical-stat-hint">Aucun couchage disponible ne répond aux exigences de placement. Vérifiez le plan ou contactez un responsable clinique.</span>}
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
      </>}

      {activeView === 'configuration' && canManageBeds && <WardConfiguration wards={wards} rooms={rooms} onCreateWard={createWardConfig} onCreateRoom={createRoomConfig} onAddBed={addBedConfig} />}
    </div>
  );
}
