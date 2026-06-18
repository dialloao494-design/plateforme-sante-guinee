import { useCallback, useEffect, useState } from 'react';

import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import { userCanManageHospitalBeds } from '../../utils/clinicAccess.js';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';

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
  const canManageBeds = userCanManageHospitalBeds(user?.role || user?.user_role);
  const [occupancy, setOccupancy] = useState(null);
  const [admissions, setAdmissions] = useState([]);
  const [beds, setBeds] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [selectedAdmission, setSelectedAdmission] = useState(null);
  const [selectedBedId, setSelectedBedId] = useState('');
  const [transferReason, setTransferReason] = useState('');
  const [roomForm, setRoomForm] = useState({ ward_name: 'Médecine', room_number: '', room_type: 'general', capacity: 2 });
  const [bedForm, setBedForm] = useState({ room_id: '', bed_number: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [occRes, admRes, bedRes, roomRes] = await Promise.all([
        clinicalApi.hospitalOccupancy(),
        clinicalApi.hospitalAdmissions(),
        clinicalApi.hospitalBeds(),
        clinicalApi.hospitalRooms(),
      ]);
      setOccupancy(occRes.data);
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

  const stats = occupancy
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
      await clinicalApi.updateAdmissionStatus(admissionId, { status });
      setMessage(`Statut mis à jour : ${STATUS_LABELS[status]}`);
      load();
    } catch (err) {
      setError(formatApiError(err, 'Mise à jour impossible'));
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
    <div className="clinical-page">
      <header className="clinical-header">
        <h1>Hospitalisation</h1>
        <p>Admissions, lits et occupation — pilotage du service.</p>
      </header>

      {error && <div className="clinical-alert clinical-alert--error">{String(error)}</div>}
      {message && <div className="clinical-alert clinical-alert--success">{message}</div>}

      <ClinicalStatGrid stats={stats} />

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
                    <button type="button" className="clinical-btn" onClick={() => setSelectedAdmission(a)}>
                      Assigner lit
                    </button>
                    {a.status !== 'in_care' && (
                      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => updateStatus(a.id, 'in_care')}>
                        Soins
                      </button>
                    )}
                  </div>
                </li>
              ))}
          </ul>
        </section>

        <section className="clinical-panel">
          <h2>Assignation / transfert de lit</h2>
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
