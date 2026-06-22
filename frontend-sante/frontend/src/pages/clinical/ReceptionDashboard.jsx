import { useCallback, useEffect, useMemo, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { getVisitWorkflowOptions, clinicHasExtendedModules } from '../../utils/clinicModuleConfig.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

const METHOD_LABELS = {
  cash: 'Espèces',
  orange_money: 'Orange Money',
  unknown: 'Autre',
};

function chargeTypeLabel(type) {
  if (type === 'consultation') return 'Consultation';
  if (type === 'laboratory') return 'Laboratoire';
  if (type === 'pharmacy') return 'Pharmacie';
  return type;
}

export default function ReceptionDashboard() {
  const { user } = useAuth();
  const clinicId = user?.clinic_id;
  const visitOptions = useMemo(() => getVisitWorkflowOptions(clinicId), [clinicId]);
  const [queue, setQueue] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [pendingCharges, setPendingCharges] = useState([]);
  const [revenueDate, setRevenueDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [revenue, setRevenue] = useState(null);
  const [followUps, setFollowUps] = useState({ due_today: [], overdue: [], upcoming: [] });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [patientForm, setPatientForm] = useState({
    first_name: '',
    last_name: '',
    age: 30,
    gender: 'other',
    phone: '',
    address: '',
    quartier: '',
    profession: '',
    mother_name: '',
    visit_destination: '',
    date_of_birth: '',
  });
  const [apptForm, setApptForm] = useState({
    patient_id: '',
    doctor_id: '',
    date: '',
    duration_minutes: 30,
  });
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [visitForm, setVisitForm] = useState({ patient_id: '', workflow_type: '' });

  const load = useCallback(async () => {
    try {
      const [q, d, charges, rev, fu] = await Promise.all([
        clinicalApi.receptionQueue(),
        clinicalApi.clinicDoctors(),
        clinicalApi.pendingCharges(),
        clinicalApi.dailyRevenue(revenueDate).catch(() => ({ data: null })),
        clinicalApi.receptionFollowUps().catch(() => ({ data: { due_today: [], overdue: [], upcoming: [] } })),
      ]);
      setQueue(q.data || []);
      setDoctors(d.data || []);
      setPendingCharges(charges.data || []);
      setRevenue(rev.data || null);
      setFollowUps(fu.data || { due_today: [], overdue: [], upcoming: [] });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Impossible de charger la réception');
    }
  }, [revenueDate]);

  useEffect(() => {
    load();
  }, [load]);

  const registerPatient = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.intakePatient({
        ...patientForm,
        date_of_birth: patientForm.date_of_birth || undefined,
        address: patientForm.address || undefined,
        quartier: patientForm.quartier || undefined,
        profession: patientForm.profession || undefined,
      });
      setMessage(`Patient enregistré : ${data.first_name} ${data.last_name} (#${data.id})`);
      setApptForm((prev) => ({ ...prev, patient_id: String(data.id) }));
      setVisitForm((prev) => ({ ...prev, patient_id: String(data.id) }));
      setPatientForm({
        first_name: '',
        last_name: '',
        age: 30,
        gender: 'other',
        phone: '',
        address: '',
        quartier: '',
        profession: '',
        mother_name: '',
        visit_destination: '',
        date_of_birth: '',
      });
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Enregistrement impossible');
    }
  };

  const bookAppointment = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.createAppointment({
        ...apptForm,
        patient_id: Number(apptForm.patient_id),
        doctor_id: Number(apptForm.doctor_id),
        duration_minutes: Number(apptForm.duration_minutes),
        consultation_type: 'physical',
      });
      setMessage(`Rendez-vous #${data.id} créé pour ${data.patient_name}`);
      load();
    } catch (err) {
      setError(typeof err?.response?.data?.detail === 'string' ? err.response.data.detail : 'Création impossible');
    }
  };

  const handleCheckIn = async (id) => {
    setError('');
    try {
      await clinicalApi.checkIn(id);
      setMessage(`Patient enregistré en salle d'attente (#${id})`);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Check-in impossible');
    }
  };

  const handlePay = async (chargeId, method = 'cash') => {
    setError('');
    setMessage('');
    try {
      await clinicalApi.payCharge(chargeId, method);
      setMessage(`Paiement enregistré (#${chargeId})`);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Paiement impossible');
    }
  };

  const searchPatients = async () => {
    if (patientSearch.trim().length < 2) return;
    try {
      const { data } = await clinicalApi.searchPatients(patientSearch.trim());
      setPatientMatches(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Recherche impossible');
    }
  };

  const waitingCount = queue.filter((i) => i.clinical_status === 'waiting' || i.clinical_status === 'checked_in').length;
  const scheduledCount = queue.filter((i) => i.clinical_status === 'scheduled').length;

  const startVisit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    if (!visitForm.patient_id) {
      setError('Sélectionnez ou enregistrez un patient avant de démarrer la visite.');
      return;
    }
    try {
      const payload = {
        patient_id: Number(visitForm.patient_id),
        workflow_type: visitForm.workflow_type || undefined,
      };
      const { data } = await clinicalApi.startVisit(payload);
      setMessage(
        `Visite démarrée pour le patient #${data.patient_id} — parcours ${data.workflow_type} (étape : ${data.current_department})`
      );
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Impossible de démarrer la visite');
    }
  };

  const stats = [
    { label: "File d'attente", value: waitingCount, hint: `${scheduledCount} à enregistrer`, variant: 'accent' },
    { label: 'Factures en attente', value: pendingCharges.length, hint: 'À encaisser', variant: 'warning' },
    {
      label: 'Encaissé aujourd\'hui',
      value: revenue ? formatGNF(revenue.total_collected_gnf) : '—',
      hint: revenue?.date || revenueDate,
      variant: 'success',
    },
    { label: 'Médecins actifs', value: doctors.length },
  ];

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Réception</h1>
      <p className="clinical-lead">
        Accueil, rendez-vous, check-in et encaissement — poste unique réception &amp; caisse.
      </p>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <DepartmentQueuePanel department="reception" title="File de visite — Réception" />

      <nav className="clinical-section-nav" aria-label="Sections réception">
        <a href="#reception-visit">Démarrer visite</a>
        <a href="#reception-patient">Enregistrement</a>
        <a href="#reception-rdv">Rendez-vous</a>
        <a href="#reception-caisse">Encaissement</a>
        <a href="#reception-followups">Suivis</a>
        <a href="#reception-file">File d&apos;attente</a>
      </nav>

      <div className="clinical-grid">
        <section id="reception-visit" className="clinical-card">
          <h2>Démarrer une visite</h2>
          <p className="clinical-stat-hint">
            {clinicHasExtendedModules(clinicId)
              ? 'Enfant (<18 ans) : Réception → Nutrition → PEV → Médecin. Adulte : choisissez le parcours.'
              : 'Adulte : consultation, laboratoire ou pharmacie. Sélectionnez le service de destination.'}
          </p>
          <form onSubmit={startVisit}>
            <div className="clinical-field">
              <label>ID patient</label>
              <input
                value={visitForm.patient_id}
                onChange={(e) => setVisitForm({ ...visitForm, patient_id: e.target.value })}
                placeholder="ID ou via enregistrement ci-dessous"
                required
              />
            </div>
            <div className="clinical-field">
              <label>Parcours (laisser vide = auto selon l&apos;âge)</label>
              <select
                value={visitForm.workflow_type}
                onChange={(e) => setVisitForm({ ...visitForm, workflow_type: e.target.value })}
              >
                {visitOptions.map((opt) => (
                  <option key={opt.value || 'auto'} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <button type="submit" className="clinical-btn">Démarrer la visite</button>
          </form>
        </section>

        <section id="reception-patient" className="clinical-card">
          <h2>Enregistrement patient</h2>
          <form onSubmit={registerPatient}>
            <div className="clinical-field">
              <label>Prénom</label>
              <input value={patientForm.first_name} onChange={(e) => setPatientForm({ ...patientForm, first_name: e.target.value })} required />
            </div>
            <div className="clinical-field">
              <label>Nom</label>
              <input value={patientForm.last_name} onChange={(e) => setPatientForm({ ...patientForm, last_name: e.target.value })} required />
            </div>
            <div className="clinical-field">
              <label>Âge</label>
              <input type="number" value={patientForm.age} onChange={(e) => setPatientForm({ ...patientForm, age: Number(e.target.value) })} required />
            </div>
            <div className="clinical-field">
              <label>Sexe</label>
              <select value={patientForm.gender} onChange={(e) => setPatientForm({ ...patientForm, gender: e.target.value })}>
                <option value="F">Féminin</option>
                <option value="M">Masculin</option>
                <option value="other">Autre</option>
              </select>
            </div>
            <div className="clinical-field">
              <label>Téléphone</label>
              <input value={patientForm.phone} onChange={(e) => setPatientForm({ ...patientForm, phone: e.target.value })} required />
            </div>
            <div className="clinical-field">
              <label>Date de naissance</label>
              <input type="date" value={patientForm.date_of_birth} onChange={(e) => setPatientForm({ ...patientForm, date_of_birth: e.target.value })} />
            </div>
            <div className="clinical-field">
              <label>Quartier / résidence</label>
              <input value={patientForm.quartier} onChange={(e) => setPatientForm({ ...patientForm, quartier: e.target.value })} required />
            </div>
            <div className="clinical-field">
              <label>Adresse complète</label>
              <input value={patientForm.address} onChange={(e) => setPatientForm({ ...patientForm, address: e.target.value })} />
            </div>
            <div className="clinical-field">
              <label>Profession</label>
              <input value={patientForm.profession} onChange={(e) => setPatientForm({ ...patientForm, profession: e.target.value })} required />
            </div>
            <div className="clinical-field">
              <label>Nom de la mère</label>
              <input value={patientForm.mother_name} onChange={(e) => setPatientForm({ ...patientForm, mother_name: e.target.value })} required />
            </div>
            <div className="clinical-field">
              <label>Motif de visite / service</label>
              <select
                value={patientForm.visit_destination}
                onChange={(e) => setPatientForm({ ...patientForm, visit_destination: e.target.value })}
                required
              >
                <option value="">Choisir le service</option>
                <option value="Consultation médicale">Consultation médicale</option>
                <option value="Laboratoire">Laboratoire</option>
                <option value="Pharmacie">Pharmacie</option>
                <option value="Autre">Autre</option>
              </select>
            </div>
            <button type="submit" className="clinical-btn">Enregistrer</button>
          </form>
        </section>

        <section id="reception-rdv" className="clinical-card">
          <h2>Rendez-vous</h2>
          <div className="clinical-field">
            <label>Rechercher patient (nom / téléphone)</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input value={patientSearch} onChange={(e) => setPatientSearch(e.target.value)} placeholder="Min. 2 caractères" />
              <button type="button" className="clinical-btn secondary" onClick={searchPatients}>Rechercher</button>
            </div>
            {patientMatches.length > 0 && (
              <ul className="clinical-list">
                {patientMatches.map((p) => (
                  <li key={p.id}>
                    <button type="button" className="clinical-btn secondary" onClick={() => setApptForm((prev) => ({ ...prev, patient_id: String(p.id) }))}>
                      {p.first_name} {p.last_name} #{p.id} {p.phone ? `· ${p.phone}` : ''}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <form onSubmit={bookAppointment}>
            <div className="clinical-field">
              <label>ID patient</label>
              <input value={apptForm.patient_id} onChange={(e) => setApptForm({ ...apptForm, patient_id: e.target.value })} required />
            </div>
            <div className="clinical-field">
              <label>Médecin</label>
              <select value={apptForm.doctor_id} onChange={(e) => setApptForm({ ...apptForm, doctor_id: e.target.value })} required>
                <option value="">Choisir</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>{d.name} — {d.specialty}</option>
                ))}
              </select>
            </div>
            <div className="clinical-field">
              <label>Date et heure</label>
              <input type="datetime-local" value={apptForm.date} onChange={(e) => setApptForm({ ...apptForm, date: e.target.value })} required />
            </div>
            <button type="submit" className="clinical-btn">Créer le rendez-vous</button>
          </form>
        </section>
      </div>

      <section id="reception-caisse" className="clinical-card" style={{ marginTop: '1.25rem' }}>
        <div className="clinical-revenue-header">
          <h2>Encaissement</h2>
          <label className="clinical-revenue-date">
            Date comptable
            <input type="date" value={revenueDate} onChange={(e) => setRevenueDate(e.target.value)} />
          </label>
        </div>
        <ul className="clinical-list">
          {pendingCharges.length === 0 && <li>Aucune facture en attente.</li>}
          {pendingCharges.map((charge) => (
            <li key={charge.id}>
              <strong>{charge.patient_name || `Patient #${charge.patient_id}`}</strong>
              {' — '}
              {chargeTypeLabel(charge.charge_type)} · {formatGNF(charge.amount_gnf)}
              <br />
              <span className="clinical-badge">{charge.description}</span>
              <div className="clinical-actions">
                <button type="button" className="clinical-btn" onClick={() => handlePay(charge.id, 'cash')}>
                  Encaisser (espèces)
                </button>
                <button
                  type="button"
                  className="clinical-btn clinical-btn--secondary"
                  onClick={() => handlePay(charge.id, 'orange_money')}
                >
                  Orange Money
                </button>
              </div>
            </li>
          ))}
        </ul>
        {revenue && Object.keys(revenue.by_payment_method || {}).length > 0 && (
          <ul className="clinical-revenue-breakdown" style={{ marginTop: '1rem' }}>
            {Object.entries(revenue.by_payment_method).map(([key, amount]) => (
              <li key={key}>
                <span>{METHOD_LABELS[key] || key}</span>
                <strong>{formatGNF(amount)}</strong>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section id="reception-followups" className="clinical-card" style={{ marginTop: '1.25rem' }}>
        <h2>Suivis patients</h2>
        <div className="clinical-grid">
          <div>
            <h3>À faire aujourd&apos;hui ({followUps.due_today?.length || 0})</h3>
            <ul className="clinical-list">
              {(followUps.due_today || []).map((f) => (
                <li key={f.id}>
                  <strong>{f.patient_name}</strong> — {f.doctor_name}
                  <br />
                  {f.reason || 'Suivi'} · <span className="clinical-badge">{f.visit_type}</span>
                </li>
              ))}
              {(followUps.due_today || []).length === 0 && <li>Aucun suivi prévu aujourd&apos;hui.</li>}
            </ul>
          </div>
          <div>
            <h3>En retard ({followUps.overdue?.length || 0})</h3>
            <ul className="clinical-list">
              {(followUps.overdue || []).map((f) => (
                <li key={f.id}>
                  <strong>{f.patient_name}</strong> — {new Date(f.scheduled_date).toLocaleDateString('fr-FR')}
                  <span className="clinical-badge">overdue</span>
                </li>
              ))}
              {(followUps.overdue || []).length === 0 && <li>Aucun suivi en retard.</li>}
            </ul>
          </div>
          <div>
            <h3>À venir ({followUps.upcoming?.length || 0})</h3>
            <ul className="clinical-list">
              {(followUps.upcoming || []).map((f) => (
                <li key={f.id}>
                  <strong>{f.patient_name}</strong> — {new Date(f.scheduled_date).toLocaleDateString('fr-FR')}
                </li>
              ))}
              {(followUps.upcoming || []).length === 0 && <li>Aucun suivi à venir (30 j).</li>}
            </ul>
          </div>
        </div>
      </section>

      <section id="reception-file" className="clinical-card" style={{ marginTop: '1.25rem' }}>
        <h2>File d&apos;attente</h2>
        <ul className="clinical-list">
          {queue.length === 0 && <li>Aucun patient en attente.</li>}
          {queue.map((item) => (
            <li key={item.id}>
              <strong>{item.patient_name}</strong> — {item.doctor_name}
              <br />
              {new Date(item.date).toLocaleString('fr-FR')} · <span className="clinical-badge">{item.clinical_status}</span>
              <div className="clinical-actions">
                {item.clinical_status === 'scheduled' && (
                  <button type="button" className="clinical-btn" onClick={() => handleCheckIn(item.id)}>Check-in</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
