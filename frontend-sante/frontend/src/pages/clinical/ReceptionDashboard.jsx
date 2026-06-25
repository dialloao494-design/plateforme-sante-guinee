import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import './clinical.css';

const TABS = [
  { id: 'dashboard', label: 'Tableau de bord', shortcut: '1' },
  { id: 'register', label: 'Enregistrement', shortcut: '2' },
  { id: 'admission', label: 'Admission', shortcut: '3' },
  { id: 'billing', label: 'Facturation', shortcut: '4' },
  { id: 'refund', label: 'Remboursement', shortcut: '5' },
];

const DEPARTMENTS = [
  'Urgences',
  'Consultation externe',
  'Laboratoire',
  'Pharmacie',
  'Hospitalisation',
  'Radiologie',
];

const ADMISSION_TYPES = [
  { value: 'emergency', label: 'Urgence' },
  { value: 'outpatient', label: 'Consultation externe' },
  { value: 'hospitalization', label: 'Hospitalisation' },
];

const PAYMENT_METHODS = [
  { value: 'cash', label: 'Espèces' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'bank_transfer', label: 'Virement bancaire' },
  { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance', label: 'Assurance' },
];

const REFUND_REASONS = [
  { value: 'deceased', label: 'Décès' },
  { value: 'service_cancelled', label: 'Service annulé' },
  { value: 'overpayment', label: 'Trop-perçu' },
  { value: 'other', label: 'Autre' },
];

const REFUND_METHODS = [
  { value: 'cash', label: 'Espèces' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'bank_transfer', label: 'Virement bancaire' },
  { value: 'card', label: 'Carte' },
  { value: 'insurance_adjustment', label: 'Ajustement assurance' },
];

const EMPTY_REG = {
  first_name: '',
  last_name: '',
  gender: 'F',
  date_of_birth: '',
  phone: '',
  phone_secondary: '',
  email: '',
  address: '',
  commune: '',
  city: '',
  region: '',
  country: 'Guinée',
  place_of_birth: '',
  nationality: 'Guinéenne',
  marital_status: '',
  mother_first_name: '',
  mother_last_name: '',
  profession: '',
  preferred_language: 'Français',
  photo_url: '',
  emergency_same_address: false,
  emergency_full_name: '',
  emergency_relationship: '',
  emergency_phone: '',
  emergency_address: '',
  emergency_commune: '',
  emergency_region: '',
  emergency_country: 'Guinée',
  emergency_email: '',
  payer_type: 'patient',
  insurance_company: '',
  insurance_number: '',
  company_name: '',
};

function qrImageUrl(token) {
  if (!token) return '';
  return `https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(token)}`;
}

function statusLabel(status) {
  if (status === 'paid') return 'Payée';
  if (status === 'partially_paid') return 'Partiellement payée';
  if (status === 'unpaid') return 'Impayée';
  if (status === 'pending') return 'En attente';
  if (status === 'approved') return 'Approuvé';
  if (status === 'rejected') return 'Rejeté';
  return status;
}

export default function ReceptionDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);
  const [tab, setTab] = useState('dashboard');
  const [stats, setStats] = useState(null);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [registeredPatient, setRegisteredPatient] = useState(null);
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [doctors, setDoctors] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [regForm, setRegForm] = useState(EMPTY_REG);
  const [duplicateWarn, setDuplicateWarn] = useState(null);
  const [admissionForm, setAdmissionForm] = useState({
    admission_date: new Date().toISOString().slice(0, 10),
    admission_time: new Date().toTimeString().slice(0, 5),
    department: 'Consultation externe',
    admission_type: 'outpatient',
    attending_clinician_user_id: '',
    attending_physician_name: '',
    notes: '',
  });
  const [billingForm, setBillingForm] = useState({
    department: 'Consultation externe',
    description: '',
    total_amount_gnf: '',
  });
  const [paymentForm, setPaymentForm] = useState({
    invoice_id: '',
    amount_gnf: '',
    payment_method: 'cash',
    reference: '',
  });
  const [refundForm, setRefundForm] = useState({
    invoice_id: '',
    service_paid_for: '',
    amount_consumed_gnf: '',
    refund_amount_gnf: '',
    reason: 'service_cancelled',
    reason_notes: '',
    recipient_name: '',
    recipient_relationship: '',
    recipient_phone: '',
    refund_method: 'cash',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      const { data } = await clinicalApi.receptionHisDashboard({ forceRefresh: true });
      setStats(data);
    } catch (err) {
      setError(formatApiError(err, 'Impossible de charger le tableau de bord'));
    }
  }, []);

  const loadInvoices = useCallback(async (patientId) => {
    try {
      const { data } = await clinicalApi.receptionHisListInvoices(patientId || undefined);
      setInvoices(data || []);
    } catch {
      setInvoices([]);
    }
  }, []);

  const loadRefunds = useCallback(async () => {
    try {
      const { data } = await clinicalApi.receptionHisListRefunds();
      setRefunds(data || []);
    } catch {
      setRefunds([]);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadDashboard(), loadInvoices(selectedPatient?.id), loadRefunds()]);
  }, [loadDashboard, loadInvoices, loadRefunds, selectedPatient?.id]);

  useEffect(() => {
    clinicalApi.clinicDoctors().then((r) => setDoctors(r.data || [])).catch(() => setDoctors([]));
    refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    if (!searchQ.trim()) {
      setSearchResults([]);
      return undefined;
    }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await clinicalApi.receptionHisSearch(searchQ.trim());
        setSearchResults(data || []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [searchQ]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') {
        if (e.key === 'F3') {
          e.preventDefault();
          searchRef.current?.focus();
        }
        return;
      }
      const hit = TABS.find((t) => t.shortcut === e.key);
      if (hit) setTab(hit.id);
      if (e.key === 'F3') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const selectPatient = (p) => {
    setSelectedPatient(p);
    setSearchQ('');
    setSearchResults([]);
    loadInvoices(p.id);
    setMessage(`Patient sélectionné : ${p.first_name} ${p.last_name} (#${p.patient_number || p.id})`);
  };

  const buildRegistrationPayload = (confirmDuplicate = false) => ({
    first_name: regForm.first_name.trim(),
    last_name: regForm.last_name.trim(),
    gender: regForm.gender,
    date_of_birth: regForm.date_of_birth,
    phone: regForm.phone.trim(),
    address: regForm.address.trim(),
    phone_secondary: regForm.phone_secondary || undefined,
    email: regForm.email || undefined,
    commune: regForm.commune || undefined,
    city: regForm.city || undefined,
    region: regForm.region || undefined,
    country: regForm.country || undefined,
    place_of_birth: regForm.place_of_birth || undefined,
    nationality: regForm.nationality || undefined,
    marital_status: regForm.marital_status || undefined,
    mother_first_name: regForm.mother_first_name || undefined,
    mother_last_name: regForm.mother_last_name || undefined,
    profession: regForm.profession || undefined,
    preferred_language: regForm.preferred_language || undefined,
    photo_url: regForm.photo_url || undefined,
    emergency_contact: {
      same_address_as_patient: regForm.emergency_same_address,
      full_name: regForm.emergency_full_name.trim(),
      relationship: regForm.emergency_relationship || undefined,
      phone: regForm.emergency_phone.trim(),
      address: regForm.emergency_same_address ? undefined : regForm.emergency_address || undefined,
      commune: regForm.emergency_same_address ? undefined : regForm.emergency_commune || undefined,
      region: regForm.emergency_same_address ? undefined : regForm.emergency_region || undefined,
      country: regForm.emergency_same_address ? undefined : regForm.emergency_country || undefined,
      email: regForm.emergency_email || undefined,
    },
    payer: {
      payer_type: regForm.payer_type,
      insurance_company: regForm.payer_type === 'insurance' ? regForm.insurance_company : undefined,
      insurance_number: regForm.payer_type === 'insurance' ? regForm.insurance_number : undefined,
      company_name: regForm.payer_type === 'company' ? regForm.company_name : undefined,
    },
    confirm_duplicate: confirmDuplicate,
  });

  const handleRegister = async (e, forceDuplicate = false) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);
    try {
      const { data } = await clinicalApi.receptionHisRegister(buildRegistrationPayload(forceDuplicate));
      setRegisteredPatient(data);
      setSelectedPatient(data);
      setDuplicateWarn(null);
      setRegForm(EMPTY_REG);
      setMessage(`Patient enregistré : ${data.patient_number} — ${data.first_name} ${data.last_name}`);
      await refreshAll();
      setTab('admission');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.code === 'duplicate_patient') {
        setDuplicateWarn(detail.matches || []);
        setError(detail.message || 'Doublon détecté');
      } else {
        setError(formatApiError(err, 'Enregistrement impossible'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAdmission = async (e) => {
    e.preventDefault();
    if (!selectedPatient) {
      setError('Sélectionnez un patient (recherche F3)');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { data } = await clinicalApi.receptionHisCreateAdmission({
        patient_id: selectedPatient.id,
        admission_date: admissionForm.admission_date,
        admission_time: `${admissionForm.admission_time}:00`,
        department: admissionForm.department,
        admission_type: admissionForm.admission_type,
        attending_clinician_user_id: admissionForm.attending_clinician_user_id
          ? Number(admissionForm.attending_clinician_user_id)
          : undefined,
        attending_physician_name: admissionForm.attending_physician_name || undefined,
        notes: admissionForm.notes || undefined,
      });
      setMessage(`Admission créée : ${data.admission_number}`);
      await refreshAll();
      setTab('billing');
    } catch (err) {
      setError(formatApiError(err, 'Admission impossible'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInvoice = async (e) => {
    e.preventDefault();
    if (!selectedPatient) {
      setError('Sélectionnez un patient');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { data } = await clinicalApi.receptionHisCreateInvoice({
        patient_id: selectedPatient.id,
        department: billingForm.department,
        description: billingForm.description.trim(),
        total_amount_gnf: Number(billingForm.total_amount_gnf),
      });
      setPaymentForm((prev) => ({ ...prev, invoice_id: String(data.id), amount_gnf: String(data.remaining_balance_gnf) }));
      setMessage(`Facture ${data.invoice_number} créée`);
      await loadInvoices(selectedPatient.id);
      await loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Facturation impossible'));
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async (e) => {
    e.preventDefault();
    if (!paymentForm.invoice_id) {
      setError('Sélectionnez une facture');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { data } = await clinicalApi.receptionHisAddPayment(Number(paymentForm.invoice_id), {
        amount_gnf: Number(paymentForm.amount_gnf),
        payment_method: paymentForm.payment_method,
        reference: paymentForm.reference || undefined,
      });
      setMessage(`Paiement enregistré — reste : ${formatGNF(data.remaining_balance_gnf)}`);
      setPaymentForm((prev) => ({
        ...prev,
        amount_gnf: String(data.remaining_balance_gnf || ''),
      }));
      await loadInvoices(selectedPatient?.id);
      await loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Paiement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const openReceipt = async (invoiceId) => {
    try {
      const { data } = await clinicalApi.receptionHisInvoiceReceipt(invoiceId);
      const url = URL.createObjectURL(data);
      window.open(url, '_blank');
    } catch {
      setError('Impossible d\'imprimer le reçu');
    }
  };

  const handleRefund = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { data } = await clinicalApi.receptionHisCreateRefund({
        invoice_id: Number(refundForm.invoice_id),
        service_paid_for: refundForm.service_paid_for.trim(),
        amount_consumed_gnf: Number(refundForm.amount_consumed_gnf),
        refund_amount_gnf: Number(refundForm.refund_amount_gnf),
        reason: refundForm.reason,
        reason_notes: refundForm.reason_notes || undefined,
        recipient_name: refundForm.recipient_name.trim(),
        recipient_relationship: refundForm.recipient_relationship || undefined,
        recipient_phone: refundForm.recipient_phone.trim(),
        refund_method: refundForm.refund_method,
      });
      setMessage(`Demande de remboursement ${data.refund_number} créée`);
      await loadRefunds();
    } catch (err) {
      setError(formatApiError(err, 'Remboursement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const updateRefundStatus = async (id, status) => {
    setLoading(true);
    try {
      await clinicalApi.receptionHisUpdateRefund(id, { status });
      setMessage(`Remboursement ${statusLabel(status)}`);
      await loadRefunds();
      await loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Mise à jour impossible'));
    } finally {
      setLoading(false);
    }
  };

  const statCards = useMemo(() => {
    if (!stats) return [];
    return [
      { label: 'Patients enregistrés', value: stats.total_patients },
      { label: 'Inscriptions aujourd\'hui', value: stats.patients_registered_today },
      { label: 'Admissions du jour', value: stats.admissions_today },
      { label: 'Hospitalisés', value: stats.hospitalized_patients },
      { label: 'Recettes du jour', value: formatGNF(stats.revenue_today_gnf) },
      { label: 'Recettes mensuelles', value: formatGNF(stats.revenue_month_gnf) },
      { label: 'Factures impayées', value: stats.outstanding_invoices },
    ];
  }, [stats]);

  return (
    <div className="clinical-page reception-his">
      <header className="reception-his-header">
        <div>
          <h1>Réception — HIS</h1>
          <p className="clinical-lead">Enregistrement · Admission · Facturation · Remboursement</p>
        </div>
        <div className="reception-his-search">
          <label htmlFor="patient-search">Recherche (F3)</label>
          <input
            id="patient-search"
            ref={searchRef}
            type="search"
            placeholder="ID, QR, téléphone, nom…"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            autoComplete="off"
          />
          {searching && <span className="reception-his-search-hint">…</span>}
          {searchResults.length > 0 && (
            <ul className="reception-his-search-results">
              {searchResults.map((p) => (
                <li key={p.id}>
                  <button type="button" onClick={() => selectPatient(p)}>
                    <strong>{p.last_name} {p.first_name}</strong>
                    <span>{p.patient_number || `#${p.id}`} · {p.phone || '—'} · {p.age} ans</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      {selectedPatient && (
        <div className="reception-his-selected">
          Patient actif :
          {' '}
          <strong>{selectedPatient.last_name} {selectedPatient.first_name}</strong>
          {' '}
          ({selectedPatient.patient_number || `#${selectedPatient.id}`})
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => setSelectedPatient(null)}>
            Effacer
          </button>
        </div>
      )}

      {message && <p className="clinical-message clinical-message--ok">{message}</p>}
      {error && <p className="clinical-message clinical-message--err">{error}</p>}

      <nav className="reception-his-tabs" aria-label="Modules réception">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? 'active' : ''}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            <kbd>{t.shortcut}</kbd>
          </button>
        ))}
      </nav>

      {tab === 'dashboard' && (
        <section className="reception-his-panel">
          <div className="reception-his-stats">
            {statCards.map((c) => (
              <div key={c.label} className="reception-his-stat-card">
                <span>{c.label}</span>
                <strong>{c.value}</strong>
              </div>
            ))}
          </div>
          {stats && (
            <div className="clinical-grid">
              <div className="clinical-card">
                <h3>Répartition H/F</h3>
                <ul className="reception-his-bar-list">
                  <li><span>Hommes</span><strong>{stats.gender_distribution?.male ?? 0}</strong></li>
                  <li><span>Femmes</span><strong>{stats.gender_distribution?.female ?? 0}</strong></li>
                  <li><span>Autre</span><strong>{stats.gender_distribution?.other ?? 0}</strong></li>
                </ul>
              </div>
              <div className="clinical-card">
                <h3>Répartition par service (mois)</h3>
                <ul className="reception-his-bar-list">
                  {Object.entries(stats.department_distribution || {}).map(([d, n]) => (
                    <li key={d}><span>{d}</span><strong>{n}</strong></li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          <button type="button" className="clinical-btn" onClick={refreshAll}>Actualiser</button>
        </section>
      )}

      {tab === 'register' && (
        <section className="reception-his-panel">
          <form className="clinical-card" onSubmit={(e) => handleRegister(e, false)}>
            <h2>Enregistrement patient</h2>
            {registeredPatient && (
              <div className="reception-his-qr-block">
                <div>
                  <p><strong>ID :</strong> {registeredPatient.patient_number}</p>
                  <p><strong>QR :</strong> {registeredPatient.qr_token}</p>
                </div>
                <img src={qrImageUrl(registeredPatient.qr_token)} alt="QR patient" width={140} height={140} />
              </div>
            )}
            {duplicateWarn && (
              <div className="reception-his-duplicate-warn">
                <p>Patients similaires détectés :</p>
                <ul>
                  {duplicateWarn.map((m) => (
                    <li key={m.id}>{m.last_name} {m.first_name} — {m.phone || '—'} ({m.match_reasons?.join(', ')})</li>
                  ))}
                </ul>
                <button type="button" className="clinical-btn" onClick={(e) => handleRegister(e, true)}>
                  Créer quand même
                </button>
              </div>
            )}
            <fieldset>
              <legend>Identité</legend>
              <div className="clinical-form-row">
                <label>Prénom *<input required value={regForm.first_name} onChange={(e) => setRegForm({ ...regForm, first_name: e.target.value })} /></label>
                <label>Nom *<input required value={regForm.last_name} onChange={(e) => setRegForm({ ...regForm, last_name: e.target.value })} /></label>
                <label>Sexe *
                  <select required value={regForm.gender} onChange={(e) => setRegForm({ ...regForm, gender: e.target.value })}>
                    <option value="F">Féminin</option>
                    <option value="M">Masculin</option>
                  </select>
                </label>
                <label>Date naissance *
                  <input required type="date" value={regForm.date_of_birth} onChange={(e) => setRegForm({ ...regForm, date_of_birth: e.target.value })} />
                </label>
                <label>Lieu naissance<input value={regForm.place_of_birth} onChange={(e) => setRegForm({ ...regForm, place_of_birth: e.target.value })} /></label>
                <label>Nationalité<input value={regForm.nationality} onChange={(e) => setRegForm({ ...regForm, nationality: e.target.value })} /></label>
                <label>État civil<input value={regForm.marital_status} onChange={(e) => setRegForm({ ...regForm, marital_status: e.target.value })} /></label>
                <label>Prénom mère<input value={regForm.mother_first_name} onChange={(e) => setRegForm({ ...regForm, mother_first_name: e.target.value })} /></label>
                <label>Nom mère<input value={regForm.mother_last_name} onChange={(e) => setRegForm({ ...regForm, mother_last_name: e.target.value })} /></label>
                <label>Profession<input value={regForm.profession} onChange={(e) => setRegForm({ ...regForm, profession: e.target.value })} /></label>
                <label>Langue<input value={regForm.preferred_language} onChange={(e) => setRegForm({ ...regForm, preferred_language: e.target.value })} /></label>
                <label>Email<input type="email" value={regForm.email} onChange={(e) => setRegForm({ ...regForm, email: e.target.value })} /></label>
                <label>Photo (URL)<input value={regForm.photo_url} onChange={(e) => setRegForm({ ...regForm, photo_url: e.target.value })} /></label>
              </div>
            </fieldset>
            <fieldset>
              <legend>Contact</legend>
              <div className="clinical-form-row">
                <label>Tél. principal *<input required value={regForm.phone} onChange={(e) => setRegForm({ ...regForm, phone: e.target.value })} /></label>
                <label>Tél. secondaire<input value={regForm.phone_secondary} onChange={(e) => setRegForm({ ...regForm, phone_secondary: e.target.value })} /></label>
                <label>Adresse *<input required value={regForm.address} onChange={(e) => setRegForm({ ...regForm, address: e.target.value })} /></label>
                <label>Quartier<input value={regForm.commune} onChange={(e) => setRegForm({ ...regForm, commune: e.target.value })} /></label>
                <label>Ville<input value={regForm.city} onChange={(e) => setRegForm({ ...regForm, city: e.target.value })} /></label>
                <label>Région<input value={regForm.region} onChange={(e) => setRegForm({ ...regForm, region: e.target.value })} /></label>
                <label>Pays<input value={regForm.country} onChange={(e) => setRegForm({ ...regForm, country: e.target.value })} /></label>
              </div>
            </fieldset>
            <fieldset>
              <legend>Personne à contacter</legend>
              <label className="reception-his-check">
                <input type="checkbox" checked={regForm.emergency_same_address} onChange={(e) => setRegForm({ ...regForm, emergency_same_address: e.target.checked })} />
                Adresse identique au patient
              </label>
              <div className="clinical-form-row">
                <label>Nom complet *<input required value={regForm.emergency_full_name} onChange={(e) => setRegForm({ ...regForm, emergency_full_name: e.target.value })} /></label>
                <label>Lien<input value={regForm.emergency_relationship} onChange={(e) => setRegForm({ ...regForm, emergency_relationship: e.target.value })} /></label>
                <label>Téléphone *<input required value={regForm.emergency_phone} onChange={(e) => setRegForm({ ...regForm, emergency_phone: e.target.value })} /></label>
                {!regForm.emergency_same_address && (
                  <>
                    <label>Adresse<input value={regForm.emergency_address} onChange={(e) => setRegForm({ ...regForm, emergency_address: e.target.value })} /></label>
                    <label>Commune<input value={regForm.emergency_commune} onChange={(e) => setRegForm({ ...regForm, emergency_commune: e.target.value })} /></label>
                  </>
                )}
              </div>
            </fieldset>
            <fieldset>
              <legend>Payeur</legend>
              <div className="clinical-form-row">
                <label>Type
                  <select value={regForm.payer_type} onChange={(e) => setRegForm({ ...regForm, payer_type: e.target.value })}>
                    <option value="patient">Patient</option>
                    <option value="insurance">Assurance</option>
                    <option value="company">Entreprise</option>
                  </select>
                </label>
                {regForm.payer_type === 'insurance' && (
                  <>
                    <label>Compagnie<input value={regForm.insurance_company} onChange={(e) => setRegForm({ ...regForm, insurance_company: e.target.value })} /></label>
                    <label>N° assurance<input value={regForm.insurance_number} onChange={(e) => setRegForm({ ...regForm, insurance_number: e.target.value })} /></label>
                  </>
                )}
                {regForm.payer_type === 'company' && (
                  <label>Entreprise<input value={regForm.company_name} onChange={(e) => setRegForm({ ...regForm, company_name: e.target.value })} /></label>
                )}
              </div>
            </fieldset>
            <button type="submit" className="clinical-btn" disabled={loading}>Enregistrer le patient</button>
          </form>
        </section>
      )}

      {tab === 'admission' && (
        <section className="reception-his-panel">
          <form className="clinical-card" onSubmit={handleAdmission}>
            <h2>Admission</h2>
            {!selectedPatient && <p className="clinical-hint">Recherchez et sélectionnez un patient (F3).</p>}
            <div className="clinical-form-row">
              <label>Date<input type="date" required value={admissionForm.admission_date} onChange={(e) => setAdmissionForm({ ...admissionForm, admission_date: e.target.value })} /></label>
              <label>Heure<input type="time" required value={admissionForm.admission_time} onChange={(e) => setAdmissionForm({ ...admissionForm, admission_time: e.target.value })} /></label>
              <label>Service *
                <select required value={admissionForm.department} onChange={(e) => setAdmissionForm({ ...admissionForm, department: e.target.value })}>
                  {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
              <label>Type *
                <select required value={admissionForm.admission_type} onChange={(e) => setAdmissionForm({ ...admissionForm, admission_type: e.target.value })}>
                  {ADMISSION_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </label>
              <label>Médecin traitant
                <select value={admissionForm.attending_clinician_user_id} onChange={(e) => setAdmissionForm({ ...admissionForm, attending_clinician_user_id: e.target.value })}>
                  <option value="">—</option>
                  {doctors.map((d) => <option key={d.id} value={d.id}>{d.full_name || d.email}</option>)}
                </select>
              </label>
              <label>Nom médecin (libre)<input value={admissionForm.attending_physician_name} onChange={(e) => setAdmissionForm({ ...admissionForm, attending_physician_name: e.target.value })} /></label>
              <label>Notes<textarea value={admissionForm.notes} onChange={(e) => setAdmissionForm({ ...admissionForm, notes: e.target.value })} rows={2} /></label>
            </div>
            <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>Créer l&apos;admission</button>
          </form>
        </section>
      )}

      {tab === 'billing' && (
        <section className="reception-his-panel clinical-grid">
          <form className="clinical-card" onSubmit={handleCreateInvoice}>
            <h2>Nouvelle facture</h2>
            <div className="clinical-form-row">
              <label>Service
                <select value={billingForm.department} onChange={(e) => setBillingForm({ ...billingForm, department: e.target.value })}>
                  {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
              <label>Description<input required value={billingForm.description} onChange={(e) => setBillingForm({ ...billingForm, description: e.target.value })} /></label>
              <label>Montant total (GNF)<input required type="number" min="0" value={billingForm.total_amount_gnf} onChange={(e) => setBillingForm({ ...billingForm, total_amount_gnf: e.target.value })} /></label>
            </div>
            <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>Créer facture</button>
          </form>

          <form className="clinical-card" onSubmit={handlePayment}>
            <h2>Paiement</h2>
            <div className="clinical-form-row">
              <label>Facture
                <select value={paymentForm.invoice_id} onChange={(e) => {
                  const inv = invoices.find((i) => String(i.id) === e.target.value);
                  setPaymentForm({
                    ...paymentForm,
                    invoice_id: e.target.value,
                    amount_gnf: inv ? String(inv.remaining_balance_gnf) : '',
                  });
                }}>
                  <option value="">—</option>
                  {invoices.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.invoice_number} — {formatGNF(i.remaining_balance_gnf)} restant
                    </option>
                  ))}
                </select>
              </label>
              <label>Montant<input required type="number" min="1" value={paymentForm.amount_gnf} onChange={(e) => setPaymentForm({ ...paymentForm, amount_gnf: e.target.value })} /></label>
              <label>Mode
                <select value={paymentForm.payment_method} onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })}>
                  {PAYMENT_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </label>
              <label>Référence<input value={paymentForm.reference} onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })} /></label>
            </div>
            <button type="submit" className="clinical-btn" disabled={loading}>Enregistrer paiement</button>
          </form>

          <div className="clinical-card reception-his-invoices">
            <h2>Factures & historique</h2>
            {invoices.length === 0 && <p>Aucune facture.</p>}
            {invoices.map((inv) => (
              <div key={inv.id} className="reception-his-invoice-row">
                <div>
                  <strong>{inv.invoice_number}</strong>
                  {' '}
                  — {statusLabel(inv.status)} — {formatGNF(inv.paid_amount_gnf)} / {formatGNF(inv.total_amount_gnf)}
                </div>
                <ul>
                  {(inv.payments || []).map((p) => (
                    <li key={p.id}>{new Date(p.paid_at).toLocaleString('fr-FR')} — {formatGNF(p.amount_gnf)} ({p.payment_method})</li>
                  ))}
                </ul>
                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openReceipt(inv.id)}>Imprimer reçu</button>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'refund' && (
        <section className="reception-his-panel clinical-grid">
          <form className="clinical-card" onSubmit={handleRefund}>
            <h2>Demande de remboursement</h2>
            <div className="clinical-form-row">
              <label>Facture
                <select required value={refundForm.invoice_id} onChange={(e) => setRefundForm({ ...refundForm, invoice_id: e.target.value })}>
                  <option value="">—</option>
                  {invoices.filter((i) => i.paid_amount_gnf > 0).map((i) => (
                    <option key={i.id} value={i.id}>{i.invoice_number} — payé {formatGNF(i.paid_amount_gnf)}</option>
                  ))}
                </select>
              </label>
              <label>Service payé<input required value={refundForm.service_paid_for} onChange={(e) => setRefundForm({ ...refundForm, service_paid_for: e.target.value })} /></label>
              <label>Montant consommé<input required type="number" min="0" value={refundForm.amount_consumed_gnf} onChange={(e) => setRefundForm({ ...refundForm, amount_consumed_gnf: e.target.value })} /></label>
              <label>Montant remboursement<input required type="number" min="1" value={refundForm.refund_amount_gnf} onChange={(e) => setRefundForm({ ...refundForm, refund_amount_gnf: e.target.value })} /></label>
              <label>Motif
                <select value={refundForm.reason} onChange={(e) => setRefundForm({ ...refundForm, reason: e.target.value })}>
                  {REFUND_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </label>
              <label>Bénéficiaire<input required value={refundForm.recipient_name} onChange={(e) => setRefundForm({ ...refundForm, recipient_name: e.target.value })} /></label>
              <label>Lien<input value={refundForm.recipient_relationship} onChange={(e) => setRefundForm({ ...refundForm, recipient_relationship: e.target.value })} /></label>
              <label>Tél. bénéficiaire<input required value={refundForm.recipient_phone} onChange={(e) => setRefundForm({ ...refundForm, recipient_phone: e.target.value })} /></label>
              <label>Mode remboursement
                <select value={refundForm.refund_method} onChange={(e) => setRefundForm({ ...refundForm, refund_method: e.target.value })}>
                  {REFUND_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </label>
            </div>
            <button type="submit" className="clinical-btn" disabled={loading}>Soumettre remboursement</button>
          </form>

          <div className="clinical-card">
            <h2>Suivi remboursements</h2>
            {refunds.length === 0 && <p>Aucun remboursement.</p>}
            {refunds.map((r) => (
              <div key={r.id} className="reception-his-invoice-row">
                <div>
                  <strong>{r.refund_number}</strong> — {r.patient_name} — {formatGNF(r.refund_amount_gnf)} — {statusLabel(r.status)}
                </div>
                <p>Facture {r.invoice_number} · {r.reason}</p>
                {r.status === 'pending' && (
                  <div className="reception-his-refund-actions">
                    <button type="button" className="clinical-btn" onClick={() => updateRefundStatus(r.id, 'approved')}>Approuver</button>
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => updateRefundStatus(r.id, 'rejected')}>Rejeter</button>
                  </div>
                )}
                {r.status === 'approved' && (
                  <button type="button" className="clinical-btn" onClick={() => updateRefundStatus(r.id, 'paid')}>Marquer payé</button>
                )}
                {r.status === 'paid' && (
                  <button type="button" className="clinical-btn clinical-btn--secondary" onClick={async () => {
                    try {
                      const { data } = await clinicalApi.receptionHisRefundReceipt(r.id);
                      window.open(URL.createObjectURL(data), '_blank');
                    } catch {
                      setError('Reçu indisponible');
                    }
                  }}>Imprimer reçu</button>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
