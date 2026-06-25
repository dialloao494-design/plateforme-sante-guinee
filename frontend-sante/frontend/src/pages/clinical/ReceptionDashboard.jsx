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

const DEPARTMENTS = ['Urgences', 'Consultation externe', 'Laboratoire', 'Pharmacie', 'Hospitalisation', 'Radiologie'];
const ADMISSION_TYPES = [
  { value: 'emergency', label: 'Urgence' },
  { value: 'outpatient', label: 'Consultation externe' },
  { value: 'hospitalization', label: 'Hospitalisation' },
];
const ADMISSION_CONFIRMATIONS = [
  { value: 'confirmed', label: 'Confirmée' },
  { value: 'pending', label: 'En attente' },
];
const PAYMENT_METHODS = [
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'cash', label: 'Espèces' },
  { value: 'bank_transfer', label: 'Virement bancaire' },
  { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance', label: 'Assurance' },
];
const REFUND_METHODS = [
  { value: 'cash', label: 'Espèces' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'bank_transfer', label: 'Virement' },
  { value: 'card', label: 'Carte' },
  { value: 'insurance_adjustment', label: 'Assurance' },
];
const REFUND_REASONS = [
  { value: 'deceased', label: 'Décès' },
  { value: 'service_cancelled', label: 'Service annulé' },
  { value: 'overpayment', label: 'Trop-perçu' },
  { value: 'other', label: 'Autre' },
];

const todayStr = new Date().toISOString().slice(0, 10);

const EMPTY_REG = {
  is_newborn: false,
  registration_date: todayStr,
  first_name: '',
  last_name: '',
  date_of_birth: '',
  gender: 'F',
  marital_status: '',
  nationality: 'Guinéenne',
  mother_last_name: '',
  mother_first_name: '',
  profession: '',
  preferred_language: 'Français',
  email: '',
  photo_url: '',
  address: '',
  phone: '',
  phone_secondary: '',
  commune: '',
  city: '',
  region: '',
  country: 'Guinée',
  emergency_same_address: false,
  emergency_full_name: '',
  emergency_relationship: '',
  emergency_phone: '',
  emergency_address: '',
  emergency_commune: '',
  emergency_region: '',
  emergency_country: 'Guinée',
  payer_type: 'patient',
  insurance_company: '',
  insurance_number: '',
  company_name: '',
  payer_notes: '',
};

const EMPTY_ADMISSION = {
  admission_date: todayStr,
  admission_time: new Date().toTimeString().slice(0, 5),
  department: 'Consultation externe',
  admission_type: 'outpatient',
  attending_clinician_user_id: '',
  attending_physician_name: '',
  confirmation_status: 'confirmed',
  notes: '',
};

const EMPTY_BILLING = { department: 'Consultation externe', description: '', total_amount_gnf: '' };
const EMPTY_PAYMENT = { amount_gnf: '', payment_method: 'orange_money', reference: '' };
const EMPTY_REFUND = {
  invoice_id: '',
  service_paid_for: '',
  amount_consumed_gnf: '',
  refund_amount_gnf: '',
  recipient_name: '',
  recipient_phone: '',
  recipient_relationship: '',
  refund_method: 'orange_money',
  reason: 'service_cancelled',
  reason_notes: '',
};

const calcAge = (dob) => {
  if (!dob) return '';
  const b = new Date(dob);
  if (Number.isNaN(b.getTime())) return '';
  const n = new Date();
  let age = n.getFullYear() - b.getFullYear();
  const m = n.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && n.getDate() < b.getDate())) age -= 1;
  return age >= 0 ? age : '';
};

const qrImageUrl = (token) =>
  token ? `https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(token)}` : '';

const refundStatusLabel = (status) => {
  if (status === 'pending') return 'Demandé';
  if (status === 'approved') return 'Approuvé';
  if (status === 'paid') return 'Payé';
  if (status === 'rejected') return 'Rejeté';
  return status || '—';
};

const invoiceStatusLabel = (status) => {
  if (status === 'paid') return 'Payée';
  if (status === 'partially_paid') return 'Partiellement payée';
  if (status === 'unpaid') return 'Impayée';
  return status || '—';
};

const methodLabel = (methods, value) => methods.find((m) => m.value === value)?.label || value || '—';

const genderLabel = (gender) => {
  if (gender === 'F') return 'Féminin';
  if (gender === 'M') return 'Masculin';
  if (gender === 'Autre') return 'Autre';
  return gender || '';
};

const patientAge = (patient) => {
  if (!patient) return '';
  if (patient.date_of_birth) return calcAge(patient.date_of_birth);
  if (patient.age != null && patient.age !== '') return String(patient.age);
  return '';
};

const patientFullName = (patient) => {
  if (!patient) return '';
  return `${patient.last_name || ''} ${patient.first_name || ''}`.trim();
};

const PatientField = ({ value, filled = false }) => (
  <input
    readOnly
    tabIndex={-1}
    value={value || ''}
    className={filled && value ? 'reception-his-auto-filled' : 'reception-his-auto-empty'}
  />
);

const PaymentMethodRadios = ({ name, value, onChange, methods }) => (
  <div className="reception-his-payment-methods" role="radiogroup" aria-label="Mode de paiement">
    {methods.map((m) => (
      <label key={m.value} className="reception-his-payment-option">
        <input
          type="radio"
          name={name}
          value={m.value}
          checked={value === m.value}
          onChange={() => onChange(m.value)}
        />
        {m.label}
      </label>
    ))}
  </div>
);

export default function ReceptionDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);

  const [tab, setTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [stats, setStats] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const [selectedPatient, setSelectedPatient] = useState(null);
  const [registeredPatient, setRegisteredPatient] = useState(null);
  const [lastAdmission, setLastAdmission] = useState(null);
  const [lastRefund, setLastRefund] = useState(null);

  const [invoices, setInvoices] = useState([]);
  const [activeInvoice, setActiveInvoice] = useState(null);
  const [refunds, setRefunds] = useState([]);

  const [regForm, setRegForm] = useState(EMPTY_REG);
  const [admissionForm, setAdmissionForm] = useState(EMPTY_ADMISSION);
  const [billingForm, setBillingForm] = useState(EMPTY_BILLING);
  const [paymentForm, setPaymentForm] = useState(EMPTY_PAYMENT);
  const [refundForm, setRefundForm] = useState(EMPTY_REFUND);

  const [invoiceSearchQ, setInvoiceSearchQ] = useState('');
  const [invoiceSearchHits, setInvoiceSearchHits] = useState([]);

  const updateReg = (v) => setRegForm((p) => ({ ...p, ...v }));
  const updateAdmission = (v) => setAdmissionForm((p) => ({ ...p, ...v }));
  const updateBilling = (v) => setBillingForm((p) => ({ ...p, ...v }));
  const updatePayment = (v) => setPaymentForm((p) => ({ ...p, ...v }));
  const updateRefund = (v) => setRefundForm((p) => ({ ...p, ...v }));

  const loadDashboard = useCallback(async () => {
    try {
      const { data } = await clinicalApi.receptionHisDashboard({ forceRefresh: true });
      setStats(data || null);
    } catch (e) {
      setError(formatApiError(e, 'Impossible de charger le tableau de bord'));
    }
  }, []);

  const loadInvoices = useCallback(async (patientId) => {
    if (!patientId) {
      setInvoices([]);
      return;
    }
    try {
      const { data } = await clinicalApi.receptionHisListInvoices(patientId);
      setInvoices(data || []);
    } catch {
      setInvoices([]);
    }
  }, []);

  const loadRefunds = useCallback(async (patientId) => {
    try {
      const { data } = await clinicalApi.receptionHisListRefunds(patientId);
      setRefunds(data || []);
    } catch {
      setRefunds([]);
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([loadDashboard(), loadInvoices(selectedPatient?.id), loadRefunds(selectedPatient?.id)]);
  }, [loadDashboard, loadInvoices, loadRefunds, selectedPatient?.id]);

  useEffect(() => {
    loadDashboard();
    clinicalApi.clinicDoctors().then((r) => setDoctors(r.data || [])).catch(() => setDoctors([]));
  }, [loadDashboard]);

  const runPatientSearch = useCallback(async (query) => {
    const q = (query ?? searchQ).trim();
    if (!q) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const { data } = await clinicalApi.receptionHisSearch(q);
      setSearchResults(data || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, [searchQ]);

  useEffect(() => {
    if (!searchQ.trim()) return void setSearchResults([]);
    const t = setTimeout(() => runPatientSearch(searchQ), 250);
    return () => clearTimeout(t);
  }, [searchQ, runPatientSearch]);

  useEffect(() => {
    if (!selectedPatient?.id || !invoiceSearchQ.trim()) return void setInvoiceSearchHits([]);
    const t = setTimeout(async () => {
      try {
        const { data } = await clinicalApi.receptionHisSearchInvoice(invoiceSearchQ.trim(), selectedPatient.id);
        setInvoiceSearchHits(data ? [data] : []);
      } catch {
        setInvoiceSearchHits([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [invoiceSearchQ, selectedPatient?.id]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === 'F3') {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
      const hit = TABS.find((t) => t.shortcut === e.key);
      if (hit) setTab(hit.id);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const selectPatient = async (p) => {
    if (!p?.id) return;
    let patient = p;
    try {
      const { data } = await clinicalApi.receptionHisGetPatient(p.id);
      if (data?.id) patient = data;
    } catch {
      try {
        const { data } = await clinicalApi.receptionHisSearch(String(p.patient_number || p.id));
        const hit = (data || []).find((row) => row.id === p.id) || data?.[0];
        if (hit?.id) patient = hit;
      } catch {
        /* keep partial payload */
      }
    }
    setSelectedPatient(patient);
    setSearchQ('');
    setSearchResults([]);
    setActiveInvoice(null);
    setInvoiceSearchQ('');
    setInvoiceSearchHits([]);
    setRefundForm((prev) => ({
      ...prev,
      invoice_id: '',
      recipient_name: prev.recipient_name || patientFullName(patient),
      recipient_phone: prev.recipient_phone || patient.phone || '',
    }));
    await Promise.all([loadInvoices(patient.id), loadRefunds(patient.id)]);
    setMessage(`Patient sélectionné : ${patientFullName(patient)} · N° dossier ${patient.patient_number || '—'}`);
  };

  const clearPatient = () => {
    setSelectedPatient(null);
    setInvoices([]);
    setRefunds([]);
    setActiveInvoice(null);
    setRefundForm((prev) => ({ ...prev, invoice_id: '' }));
  };

  const onPhotoFile = (file) => {
    if (!file) return updateReg({ photo_url: '' });
    if (file.size > 400 * 1024) return setError('La photo doit faire moins de 400 KB.');
    const reader = new FileReader();
    reader.onload = () => {
      updateReg({ photo_url: String(reader.result || '') });
      setError('');
    };
    reader.onerror = () => setError('Lecture de la photo impossible.');
    reader.readAsDataURL(file);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        first_name: regForm.first_name.trim(),
        last_name: regForm.last_name.trim(),
        date_of_birth: regForm.date_of_birth,
        gender: regForm.gender,
        is_newborn: regForm.is_newborn,
        registration_date: regForm.registration_date || undefined,
        marital_status: regForm.marital_status || undefined,
        nationality: regForm.nationality || undefined,
        mother_last_name: regForm.mother_last_name || undefined,
        mother_first_name: regForm.mother_first_name || undefined,
        profession: regForm.profession || undefined,
        preferred_language: regForm.preferred_language || undefined,
        email: regForm.email || undefined,
        photo_url: regForm.photo_url || undefined,
        address: regForm.address.trim(),
        phone: regForm.phone.trim(),
        phone_secondary: regForm.phone_secondary || undefined,
        commune: regForm.commune || undefined,
        city: regForm.city || undefined,
        region: regForm.region || undefined,
        country: regForm.country || undefined,
        emergency_contact: {
          same_address_as_patient: regForm.emergency_same_address,
          full_name: regForm.emergency_full_name.trim(),
          relationship: regForm.emergency_relationship || undefined,
          phone: regForm.emergency_phone.trim(),
          address: regForm.emergency_same_address ? regForm.address : regForm.emergency_address || undefined,
          commune: regForm.emergency_same_address ? regForm.commune : regForm.emergency_commune || undefined,
          region: regForm.emergency_same_address ? regForm.region : regForm.emergency_region || undefined,
          country: regForm.emergency_same_address ? regForm.country : regForm.emergency_country || undefined,
        },
        payer: {
          payer_type: regForm.payer_type,
          insurance_company: regForm.payer_type === 'insurance' ? regForm.insurance_company || undefined : undefined,
          insurance_number: regForm.payer_type === 'insurance' ? regForm.insurance_number || undefined : undefined,
          company_name: regForm.payer_type === 'company' ? regForm.company_name || undefined : undefined,
          notes: regForm.payer_notes || undefined,
        },
      };
      const { data } = await clinicalApi.receptionHisRegister(payload);
      setRegisteredPatient(data || null);
      setRegForm({ ...EMPTY_REG, registration_date: todayStr });
      setMessage(`Patient enregistré · N° dossier patient ${data?.patient_number || '—'}`);
      if (data?.id) await selectPatient(data);
      await loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement du patient impossible'));
    } finally {
      setLoading(false);
    }
  };

  const handleAdmission = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Recherchez et sélectionnez un patient avant de créer l’admission.');
    setLoading(true);
    setError('');
    setMessage('');
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
        confirmation_status: admissionForm.confirmation_status,
        notes: admissionForm.notes || undefined,
      });
      setLastAdmission(data || null);
      setMessage(`Admission créée · N° admission ${data?.admission_number || '—'}`);
      await loadDashboard();
      setTab('billing');
    } catch (err) {
      setError(formatApiError(err, 'Création de l’admission impossible'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInvoice = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Recherchez et sélectionnez un patient avant de créer l’admission.');
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.receptionHisCreateInvoice({
        patient_id: selectedPatient.id,
        department: billingForm.department,
        description: billingForm.description.trim(),
        total_amount_gnf: Number(billingForm.total_amount_gnf || 0),
      });
      setActiveInvoice(data || null);
      setPaymentForm((prev) => ({ ...prev, amount_gnf: String(data?.remaining_balance_gnf ?? data?.total_amount_gnf ?? '') }));
      setMessage(`Facture créée · N° facture ${data?.invoice_number || '—'}`);
      await Promise.all([loadInvoices(selectedPatient.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Création de facture impossible'));
    } finally {
      setLoading(false);
    }
  };

  const selectInvoice = (id) => {
    const inv = invoices.find((item) => String(item.id) === String(id));
    setActiveInvoice(inv || null);
    updatePayment({ amount_gnf: String(inv?.remaining_balance_gnf ?? '') });
    updateRefund({
      invoice_id: inv ? String(inv.id) : '',
      service_paid_for: inv?.department || '',
      refund_amount_gnf: String(inv?.paid_amount_gnf ?? ''),
    });
  };

  const handlePayment = async (e) => {
    e.preventDefault();
    if (!activeInvoice?.id) return setError('Sélectionnez une facture du patient.');
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.receptionHisAddPayment(activeInvoice.id, {
        amount_gnf: Number(paymentForm.amount_gnf || 0),
        payment_method: paymentForm.payment_method,
        reference: paymentForm.reference || undefined,
      });
      setMessage(`Paiement enregistré · reste ${formatGNF(data?.remaining_balance_gnf || 0)}`);
      updatePayment({ amount_gnf: String(data?.remaining_balance_gnf ?? '') });
      setActiveInvoice(data || null);
      await Promise.all([loadInvoices(selectedPatient?.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement du paiement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const handleRefund = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Recherchez et sélectionnez un patient avant de créer l’admission.');
    if (!refundForm.invoice_id) return setError('Sélectionnez une facture du patient.');
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.receptionHisCreateRefund({
        invoice_id: Number(refundForm.invoice_id),
        service_paid_for: refundForm.service_paid_for || undefined,
        amount_consumed_gnf: Number(refundForm.amount_consumed_gnf || 0),
        refund_amount_gnf: Number(refundForm.refund_amount_gnf || 0),
        recipient_name: refundForm.recipient_name.trim(),
        recipient_phone: refundForm.recipient_phone.trim(),
        recipient_relationship: refundForm.recipient_relationship || undefined,
        refund_method: refundForm.refund_method,
        reason: refundForm.reason,
        reason_notes: refundForm.reason_notes || undefined,
      });
      setMessage(`Demande enregistrée · N° remboursement ${data?.refund_number || '—'}`);
      setLastRefund(data || null);
      setRefundForm((prev) => ({ ...EMPTY_REFUND, invoice_id: prev.invoice_id }));
      await Promise.all([loadRefunds(selectedPatient.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Création du remboursement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const updateRefundStatus = async (id, status) => {
    setLoading(true);
    setError('');
    try {
      await clinicalApi.receptionHisUpdateRefund(id, { status });
      setMessage(`Remboursement mis à jour : ${refundStatusLabel(status)}`);
      await Promise.all([loadRefunds(selectedPatient?.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Mise à jour du remboursement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const printInvoiceReceipt = async (invoiceId) => {
    try {
      const { data } = await clinicalApi.receptionHisInvoiceReceipt(invoiceId);
      window.open(URL.createObjectURL(data), '_blank');
    } catch {
      setError('Impossible d’imprimer le reçu.');
    }
  };

  const printRefundReceipt = async (refundId) => {
    try {
      const { data } = await clinicalApi.receptionHisRefundReceipt(refundId);
      window.open(URL.createObjectURL(data), '_blank');
    } catch {
      setError('Impossible d’imprimer le reçu de remboursement.');
    }
  };

  const statCards = useMemo(() => {
    if (!stats) return [];
    return [
      { label: 'Patients total', value: stats.total_patients ?? 0 },
      { label: 'Patients inscrits aujourd’hui', value: stats.patients_registered_today ?? 0 },
      { label: 'Admissions aujourd’hui', value: stats.admissions_today ?? 0 },
      { label: 'Patients hospitalisés', value: stats.hospitalized_patients ?? 0 },
      { label: 'Factures payées', value: stats.paid_invoices ?? 0 },
      { label: 'Factures impayées', value: stats.unpaid_invoices ?? 0 },
      { label: 'Recette du jour', value: formatGNF(stats.revenue_today_gnf ?? 0) },
      { label: 'Recette du mois', value: formatGNF(stats.revenue_month_gnf ?? 0) },
      { label: 'Total remboursements', value: formatGNF(stats.refunds_total_gnf ?? 0) },
    ];
  }, [stats]);

  const filteredRefunds = useMemo(() => {
    if (!selectedPatient?.id) return [];
    return refunds.filter((r) => Number(r.patient_id) === Number(selectedPatient.id));
  }, [refunds, selectedPatient?.id]);

  const refundInvoices = useMemo(() => {
    if (!invoiceSearchQ.trim()) return invoices;
    const q = invoiceSearchQ.trim().toLowerCase();
    const ids = new Set((invoiceSearchHits || []).map((x) => Number(x.id)));
    return invoices.filter((i) => String(i.invoice_number || '').toLowerCase().includes(q) || ids.has(Number(i.id)));
  }, [invoiceSearchQ, invoiceSearchHits, invoices]);

  const activeMeta = activeInvoice
    ? {
        total: Number(activeInvoice.total_amount_gnf || 0),
        paid: Number(activeInvoice.paid_amount_gnf || 0),
        remaining: Number(activeInvoice.remaining_balance_gnf || 0),
      }
    : null;

  const patientDisplayName = patientFullName(selectedPatient);

  const PatientContextPanel = () => (
    <div className={`clinical-card reception-his-patient-context${selectedPatient ? ' reception-his-patient-context--active' : ''}`}>
      <h3>Patient sélectionné</h3>
      <div className="reception-his-patient-context-grid">
        <div><strong>N° dossier</strong><span className={selectedPatient?.patient_number ? 'reception-his-value-filled' : ''}>{selectedPatient?.patient_number || ''}</span></div>
        <div><strong>Nom</strong><span className={selectedPatient?.last_name ? 'reception-his-value-filled' : ''}>{selectedPatient?.last_name || ''}</span></div>
        <div><strong>Prénom</strong><span className={selectedPatient?.first_name ? 'reception-his-value-filled' : ''}>{selectedPatient?.first_name || ''}</span></div>
        <div><strong>Téléphone</strong><span className={selectedPatient?.phone ? 'reception-his-value-filled' : ''}>{selectedPatient?.phone || ''}</span></div>
        <div><strong>Âge</strong><span className={patientAge(selectedPatient) ? 'reception-his-value-filled' : ''}>{patientAge(selectedPatient)}</span></div>
        <div><strong>Sexe</strong><span className={selectedPatient?.gender ? 'reception-his-value-filled' : ''}>{genderLabel(selectedPatient?.gender)}</span></div>
      </div>
      {!selectedPatient && (
        <p className="clinical-hint reception-his-patient-hint">
          Utilisez la recherche en haut de page pour sélectionner un patient.
        </p>
      )}
    </div>
  );

  return (
    <div className="clinical-page reception-his">
      <header className="reception-his-header">
        <div>
          <h1>Tableau de bord — Réception</h1>
          <p className="clinical-lead">Enregistrement patient · Admission · Facturation · Remboursement</p>
          <p className="reception-his-session">Session : {user?.full_name || user?.email || 'Utilisateur'}</p>
        </div>
        <div className="reception-his-search">
          <label htmlFor="patient-search">Recherche patient</label>
          <div className="reception-his-search-inline">
            <input
              id="patient-search"
              ref={searchRef}
              type="search"
              placeholder="N° dossier, nom, téléphone, QR…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  runPatientSearch();
                }
              }}
              autoComplete="off"
            />
            <button
              type="button"
              className="clinical-btn"
              onClick={() => runPatientSearch()}
              disabled={searching || !searchQ.trim()}
            >
              {searching ? '…' : 'Rechercher'}
            </button>
          </div>
          {searching && <span className="reception-his-search-hint">Recherche…</span>}
          {searchResults.length > 0 && (
            <ul className="reception-his-search-results">
              {searchResults.map((p) => (
                <li key={p.id}>
                  <button type="button" onClick={() => selectPatient(p)}>
                    <strong>{p.last_name} {p.first_name}</strong>
                    <span>ID patient {p.patient_number || '—'} · {p.phone || '—'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      {selectedPatient && (
        <div className="reception-his-selected">
          Patient actif : <strong>{selectedPatient.last_name} {selectedPatient.first_name}</strong> · ID patient{' '}
          <strong>{selectedPatient.patient_number || '—'}</strong>
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={clearPatient}>Effacer</button>
        </div>
      )}

      {message && <p className="clinical-message clinical-message--ok">{message}</p>}
      {error && <p className="clinical-message clinical-message--err">{error}</p>}

      <nav className="reception-his-tabs">
        {TABS.map((t) => (
          <button key={t.id} type="button" className={tab === t.id ? 'active' : ''} onClick={() => setTab(t.id)}>
            {t.label}<kbd>{t.shortcut}</kbd>
          </button>
        ))}
      </nav>

      {tab === 'dashboard' && (
        <section className="reception-his-panel">
          <div className="reception-his-stats">
            {statCards.map((s) => (
              <article key={s.label} className="reception-his-stat-card"><span>{s.label}</span><strong>{s.value}</strong></article>
            ))}
          </div>
          <div className="clinical-grid">
            <article className="clinical-card">
              <h3>Répartition H/F/Autre</h3>
              <ul className="reception-his-list">
                <li>H : {stats?.gender_distribution?.male ?? 0}</li>
                <li>F : {stats?.gender_distribution?.female ?? 0}</li>
                <li>Autre : {stats?.gender_distribution?.other ?? 0}</li>
              </ul>
            </article>
            <article className="clinical-card">
              <h3>Répartition par service</h3>
              <ul className="reception-his-list">
                {Object.entries(stats?.department_distribution || {}).map(([k, v]) => <li key={k}>{k} : {v}</li>)}
              </ul>
            </article>
          </div>
          <div className="clinical-grid">
            <article className="clinical-card">
              <h3>Inscriptions récentes</h3>
              <ul className="reception-his-list">
                {(stats?.recent_registrations || []).map((r, idx) => (
                  <li key={`${r.patient_id}-${idx}`}>{r.patient_name} · ID patient {r.patient_id}</li>
                ))}
              </ul>
            </article>
            <article className="clinical-card">
              <h3>Admissions récentes</h3>
              <ul className="reception-his-list">
                {(stats?.recent_admissions || []).map((r, idx) => (
                  <li key={`${r.admission_number}-${idx}`}>N° admission {r.admission_number} · {r.patient_id} · {r.department || '—'}</li>
                ))}
              </ul>
            </article>
          </div>
          <div className="clinical-grid">
            <article className="clinical-card">
              <h3>Paiements récents</h3>
              <ul className="reception-his-list">
                {(stats?.recent_payments || []).map((r, idx) => (
                  <li key={`${r.invoice_number}-${idx}`}>N° facture {r.invoice_number} · {formatGNF(r.amount_gnf || 0)} · {r.payment_method}</li>
                ))}
              </ul>
            </article>
            <article className="clinical-card">
              <h3>Remboursements récents</h3>
              <ul className="reception-his-list">
                {(stats?.recent_refunds || []).map((r, idx) => (
                  <li key={`${r.refund_number}-${idx}`}>{r.refund_number} · {r.patient_id} · {formatGNF(r.refund_amount_gnf || 0)} · {refundStatusLabel(r.status)}</li>
                ))}
              </ul>
            </article>
          </div>
          <button type="button" className="clinical-btn" onClick={refresh} disabled={loading}>Actualiser</button>
        </section>
      )}

      {tab === 'register' && (
        <section className="reception-his-panel">
          <form className="clinical-card" onSubmit={handleRegister}>
            <h2>Enregistrement patient</h2>
            {registeredPatient && (
              <div className="reception-his-qr-block">
                <div>
                  <p><strong>N° dossier patient :</strong> {registeredPatient.patient_number || '—'}</p>
                  <p><strong>QR :</strong> {registeredPatient.qr_token || '—'}</p>
                </div>
                {registeredPatient.qr_token && <img src={qrImageUrl(registeredPatient.qr_token)} alt="QR patient" width={140} height={140} />}
              </div>
            )}
            <fieldset><legend>Identité</legend><div className="clinical-form-row">
              <label>N° dossier patient<PatientField value={registeredPatient?.patient_number || ''} filled={Boolean(registeredPatient?.patient_number)} /></label>
              <label>Date inscription<input required type="date" value={registeredPatient?.registration_date ? String(registeredPatient.registration_date).slice(0, 10) : regForm.registration_date} onChange={(e) => updateReg({ registration_date: e.target.value })} readOnly={Boolean(registeredPatient)} /></label>
              <label className="reception-his-check"><input type="checkbox" checked={regForm.is_newborn} onChange={(e) => updateReg({ is_newborn: e.target.checked })} />Nouveau-né</label>
              <label>Nom *<input required value={regForm.last_name} onChange={(e) => updateReg({ last_name: e.target.value })} /></label>
              <label>Prénom *<input required value={regForm.first_name} onChange={(e) => updateReg({ first_name: e.target.value })} /></label>
              <label>Date naissance *<input required type="date" value={regForm.date_of_birth} onChange={(e) => updateReg({ date_of_birth: e.target.value })} /></label>
              <label>Âge<input readOnly value={calcAge(regForm.date_of_birth)} /></label>
              <label>Sexe *<select required value={regForm.gender} onChange={(e) => updateReg({ gender: e.target.value })}><option value="F">Féminin</option><option value="M">Masculin</option><option value="Autre">Autre</option></select></label>
              <label>État civil<input value={regForm.marital_status} onChange={(e) => updateReg({ marital_status: e.target.value })} /></label>
              <label>Nationalité<input value={regForm.nationality} onChange={(e) => updateReg({ nationality: e.target.value })} /></label>
              <label>Nom mère<input value={regForm.mother_last_name} onChange={(e) => updateReg({ mother_last_name: e.target.value })} /></label>
              <label>Prénom mère<input value={regForm.mother_first_name} onChange={(e) => updateReg({ mother_first_name: e.target.value })} /></label>
              <label>Profession du patient<input value={regForm.profession} onChange={(e) => updateReg({ profession: e.target.value })} /></label>
              <label>Langue<input value={regForm.preferred_language} onChange={(e) => updateReg({ preferred_language: e.target.value })} /></label>
              <label>Email<input type="email" value={regForm.email} onChange={(e) => updateReg({ email: e.target.value })} /></label>
            </div></fieldset>
            <fieldset><legend>Photo</legend><div className="clinical-form-row">
              <label>Photo (optionnelle)<input type="file" accept="image/*" onChange={(e) => onPhotoFile(e.target.files?.[0])} /></label>
              {regForm.photo_url && <div className="reception-his-photo-preview"><img src={regForm.photo_url} alt="Aperçu" /></div>}
            </div></fieldset>
            <fieldset><legend>Adresse</legend><div className="clinical-form-row">
              <label>Adresse *<input required value={regForm.address} onChange={(e) => updateReg({ address: e.target.value })} /></label>
              <label>Tél. principal *<input required value={regForm.phone} onChange={(e) => updateReg({ phone: e.target.value })} /></label>
              <label>Tél. secondaire<input value={regForm.phone_secondary} onChange={(e) => updateReg({ phone_secondary: e.target.value })} /></label>
              <label>Commune / ville<input value={regForm.commune} onChange={(e) => updateReg({ commune: e.target.value })} /></label>
              <label>Région<input value={regForm.region} onChange={(e) => updateReg({ region: e.target.value })} /></label>
              <label>Pays<input value={regForm.country} onChange={(e) => updateReg({ country: e.target.value })} /></label>
            </div></fieldset>
            <fieldset><legend>Personne à contacter</legend>
              <label className="reception-his-check"><input type="checkbox" checked={regForm.emergency_same_address} onChange={(e) => updateReg({ emergency_same_address: e.target.checked })} />Adresse identique à celle du patient</label>
              <div className="clinical-form-row">
                <label>Nom du contact *<input required value={regForm.emergency_full_name} onChange={(e) => updateReg({ emergency_full_name: e.target.value })} /></label>
                <label>Relation<input value={regForm.emergency_relationship} onChange={(e) => updateReg({ emergency_relationship: e.target.value })} /></label>
                <label>Téléphone *<input required value={regForm.emergency_phone} onChange={(e) => updateReg({ emergency_phone: e.target.value })} /></label>
                {!regForm.emergency_same_address && (
                  <>
                    <label>Adresse contact<input value={regForm.emergency_address} onChange={(e) => updateReg({ emergency_address: e.target.value })} /></label>
                    <label>Commune / ville contact<input value={regForm.emergency_commune} onChange={(e) => updateReg({ emergency_commune: e.target.value })} /></label>
                    <label>Région contact<input value={regForm.emergency_region} onChange={(e) => updateReg({ emergency_region: e.target.value })} /></label>
                    <label>Pays contact<input value={regForm.emergency_country} onChange={(e) => updateReg({ emergency_country: e.target.value })} /></label>
                  </>
                )}
              </div>
            </fieldset>
            <fieldset><legend>Payeur</legend><div className="clinical-form-row">
              <label>Type de payeur<select value={regForm.payer_type} onChange={(e) => updateReg({ payer_type: e.target.value })}><option value="patient">Patient</option><option value="insurance">Assurance</option><option value="company">Entreprise</option></select></label>
              {regForm.payer_type === 'insurance' && (<><label>Compagnie d’assurance<input value={regForm.insurance_company} onChange={(e) => updateReg({ insurance_company: e.target.value })} /></label><label>Numéro d’assurance<input value={regForm.insurance_number} onChange={(e) => updateReg({ insurance_number: e.target.value })} /></label></>)}
              {regForm.payer_type === 'company' && <label>Nom de l’entreprise<input value={regForm.company_name} onChange={(e) => updateReg({ company_name: e.target.value })} /></label>}
              <label>Notes<textarea rows={2} value={regForm.payer_notes} onChange={(e) => updateReg({ payer_notes: e.target.value })} /></label>
            </div></fieldset>
            <button type="submit" className="clinical-btn" disabled={loading}>Enregistrer le patient</button>
          </form>
        </section>
      )}

      {tab === 'admission' && (
        <section className="reception-his-panel">
          <PatientContextPanel />
          <form className="clinical-card reception-his-form-sheet" onSubmit={handleAdmission}>
            <h2>Admission</h2>
            <fieldset>
              <legend>Admission</legend>
              <div className="reception-his-form-row reception-his-form-row--4">
                <label>
                  N° d&apos;admission
                  <PatientField value={lastAdmission?.admission_number || ''} filled={Boolean(lastAdmission?.admission_number)} />
                </label>
                <label>
                  N° dossier patient
                  <PatientField value={selectedPatient?.patient_number || ''} filled={Boolean(selectedPatient)} />
                </label>
                <label>
                  Nom et prénom
                  <PatientField value={patientDisplayName} filled={Boolean(selectedPatient)} />
                </label>
                <label>
                  Service *
                  <select required value={admissionForm.department} onChange={(e) => updateAdmission({ department: e.target.value })}>
                    {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </label>
              </div>
              <div className="reception-his-form-row">
                <label>
                  Date et heure d&apos;admission
                  <div className="reception-his-datetime-pair">
                    <input
                      required
                      type="date"
                      value={admissionForm.admission_date}
                      onChange={(e) => updateAdmission({ admission_date: e.target.value })}
                    />
                    <input
                      required
                      type="time"
                      value={admissionForm.admission_time}
                      onChange={(e) => updateAdmission({ admission_time: e.target.value })}
                    />
                  </div>
                </label>
                <label>
                  Médecin traitant
                  <select value={admissionForm.attending_clinician_user_id} onChange={(e) => updateAdmission({ attending_clinician_user_id: e.target.value })}>
                    <option value="">— Sélectionner —</option>
                    {doctors.map((d) => <option key={d.id} value={d.id}>{d.full_name || d.email}</option>)}
                  </select>
                  <input
                    type="text"
                    placeholder="Ou saisir le nom du médecin"
                    value={admissionForm.attending_physician_name}
                    onChange={(e) => updateAdmission({ attending_physician_name: e.target.value })}
                  />
                </label>
                <label>
                  Type d&apos;admission
                  <select value={admissionForm.admission_type} onChange={(e) => updateAdmission({ admission_type: e.target.value })}>
                    {ADMISSION_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                  <span className="reception-his-field-hint">Urgence · Consultation externe · Hospitalisation</span>
                </label>
              </div>
              <div className="reception-his-form-row reception-his-form-row--2">
                <label>
                  Confirmation / rendez-vous
                  <select value={admissionForm.confirmation_status} onChange={(e) => updateAdmission({ confirmation_status: e.target.value })}>
                    {ADMISSION_CONFIRMATIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </label>
                <label className="reception-his-notes-field">
                  Notes
                  <textarea rows={2} value={admissionForm.notes} onChange={(e) => updateAdmission({ notes: e.target.value })} />
                </label>
              </div>
            </fieldset>
            <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>Créer l&apos;admission</button>
          </form>
        </section>
      )}

      {tab === 'billing' && (
        <section className="reception-his-panel">
          <PatientContextPanel />
          <div className="clinical-card reception-his-form-sheet">
            <h2>Facturation</h2>

            {selectedPatient && invoices.length > 0 && (
              <label className="reception-his-invoice-select">
                Facture du patient
                <select value={activeInvoice?.id || ''} onChange={(e) => selectInvoice(e.target.value)}>
                  <option value="">— Nouvelle facture —</option>
                  {invoices.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.invoice_number} · {invoiceStatusLabel(i.status)}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <fieldset>
              <legend>Facture</legend>
              <div className="reception-his-form-row reception-his-form-row--4">
                <label>
                  N° facture
                  <PatientField value={activeInvoice?.invoice_number || ''} filled={Boolean(activeInvoice)} />
                </label>
                <label>
                  N° dossier patient
                  <PatientField value={selectedPatient?.patient_number || ''} filled={Boolean(selectedPatient)} />
                </label>
                <label>
                  Nom et prénom
                  <PatientField value={patientDisplayName} filled={Boolean(selectedPatient)} />
                </label>
                <label>
                  Date de facturation
                  <PatientField value={(activeInvoice?.created_at || '').slice(0, 10)} filled={Boolean(activeInvoice)} />
                </label>
              </div>
              <div className="reception-his-form-row">
                <label>
                  Service concerné
                  {activeInvoice ? (
                    <PatientField value={activeInvoice.department || ''} filled />
                  ) : (
                    <select value={billingForm.department} onChange={(e) => updateBilling({ department: e.target.value })}>
                      {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  )}
                </label>
              </div>
              {!activeInvoice && (
                <form className="reception-his-inline-create" onSubmit={handleCreateInvoice}>
                  <div className="reception-his-form-row reception-his-form-row--2">
                    <label>
                      Description *
                      <input required value={billingForm.description} onChange={(e) => updateBilling({ description: e.target.value })} />
                    </label>
                    <label>
                      Montant total *
                      <input required type="number" min="0" value={billingForm.total_amount_gnf} onChange={(e) => updateBilling({ total_amount_gnf: e.target.value })} />
                    </label>
                  </div>
                  <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>Créer facture</button>
                </form>
              )}
            </fieldset>

            <fieldset>
              <legend>Paiement</legend>
              <div className="reception-his-form-row reception-his-form-row--4">
                <label>
                  Montant total
                  <input
                    readOnly
                    disabled
                    value={activeMeta ? formatGNF(activeMeta.total) : (billingForm.total_amount_gnf ? formatGNF(Number(billingForm.total_amount_gnf)) : '')}
                  />
                </label>
                <label>
                  À payer par le patient
                  <input readOnly disabled value={activeMeta ? formatGNF(activeMeta.total) : ''} />
                </label>
                <label>
                  Montant reçu
                  <input readOnly disabled value={activeMeta ? formatGNF(activeMeta.paid) : ''} />
                </label>
                <label>
                  Reste à payer
                  <input readOnly disabled value={activeMeta ? formatGNF(activeMeta.remaining) : ''} />
                </label>
              </div>
              <form onSubmit={handlePayment}>
                <div className="reception-his-form-row reception-his-form-row--2">
                  <label>
                    Montant à encaisser *
                    <input
                      required
                      type="number"
                      min="0"
                      value={paymentForm.amount_gnf}
                      onChange={(e) => updatePayment({ amount_gnf: e.target.value })}
                      disabled={!activeInvoice}
                    />
                  </label>
                  <label>
                    Référence
                    <input
                      value={paymentForm.reference}
                      onChange={(e) => updatePayment({ reference: e.target.value })}
                      placeholder="N° transaction, reçu…"
                      disabled={!activeInvoice}
                    />
                  </label>
                </div>
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Mode de paiement</legend>
                  <PaymentMethodRadios
                    name="payment_method"
                    value={paymentForm.payment_method}
                    onChange={(v) => updatePayment({ payment_method: v })}
                    methods={PAYMENT_METHODS}
                  />
                </fieldset>
                <button type="submit" className="clinical-btn" disabled={loading || !activeInvoice || !selectedPatient}>
                  Enregistrer paiement
                </button>
              </form>
            </fieldset>

            <fieldset className="reception-his-payment-history">
              <legend>Historique des paiements</legend>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Montant</th>
                    <th>Mode</th>
                    <th>Référence</th>
                  </tr>
                </thead>
                <tbody>
                  {(activeInvoice?.payments || []).length === 0 ? (
                    <tr>
                      <td colSpan={4} className="reception-his-empty-row">Aucun paiement enregistré.</td>
                    </tr>
                  ) : (
                    (activeInvoice.payments || []).map((p) => (
                      <tr key={p.id}>
                        <td>{new Date(p.paid_at).toLocaleString('fr-FR')}</td>
                        <td>{formatGNF(p.amount_gnf || 0)}</td>
                        <td>{methodLabel(PAYMENT_METHODS, p.payment_method)}</td>
                        <td>{p.reference || '—'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              {activeInvoice && (
                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => printInvoiceReceipt(activeInvoice.id)}>
                  Imprimer reçu
                </button>
              )}
            </fieldset>
          </div>
        </section>
      )}

      {tab === 'refund' && (
        <section className="reception-his-panel">
          <PatientContextPanel />
          <div className="clinical-card reception-his-form-sheet">
            <h2>Remboursement</h2>

            <form onSubmit={handleRefund}>
              <fieldset>
                <legend>Demande de remboursement</legend>
                <div className="reception-his-form-row reception-his-form-row--4">
                  <label>
                    N° remboursement
                    <input readOnly disabled value={lastRefund?.refund_number || ''} />
                  </label>
                  <label>
                    N° dossier patient
                    <PatientField value={selectedPatient?.patient_number || ''} filled={Boolean(selectedPatient)} />
                  </label>
                  <label>
                    Nom et prénom
                    <PatientField value={patientDisplayName} filled={Boolean(selectedPatient)} />
                  </label>
                  <label>
                    Service payé
                    <input value={refundForm.service_paid_for} onChange={(e) => updateRefund({ service_paid_for: e.target.value })} />
                  </label>
                </div>
                <div className="reception-his-form-row reception-his-form-row--2">
                  <label>
                    Facture originale *
                    <input
                      type="search"
                      placeholder="Rechercher N° facture…"
                      value={invoiceSearchQ}
                      onChange={(e) => setInvoiceSearchQ(e.target.value)}
                      disabled={!selectedPatient}
                    />
                    <select
                      required
                      value={refundForm.invoice_id}
                      onChange={(e) => { updateRefund({ invoice_id: e.target.value }); selectInvoice(e.target.value); }}
                      disabled={!selectedPatient}
                    >
                      <option value="">— Sélectionner —</option>
                      {refundInvoices.map((i) => (
                        <option key={i.id} value={i.id}>
                          {i.invoice_number} · payé {formatGNF(i.paid_amount_gnf || 0)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Motif
                    <select value={refundForm.reason} onChange={(e) => updateRefund({ reason: e.target.value })}>
                      {REFUND_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                  </label>
                </div>
                <div className="reception-his-form-row reception-his-form-row--3">
                  <label>
                    Total payé
                    <input readOnly disabled value={formatGNF(activeInvoice?.paid_amount_gnf || 0)} />
                  </label>
                  <label>
                    Montant consommé *
                    <input required type="number" min="0" value={refundForm.amount_consumed_gnf} onChange={(e) => updateRefund({ amount_consumed_gnf: e.target.value })} />
                  </label>
                  <label>
                    Montant à rembourser *
                    <input required type="number" min="0" value={refundForm.refund_amount_gnf} onChange={(e) => updateRefund({ refund_amount_gnf: e.target.value })} />
                  </label>
                </div>
                <div className="reception-his-form-row reception-his-form-row--3">
                  <label>
                    Bénéficiaire *
                    <input required value={refundForm.recipient_name} onChange={(e) => updateRefund({ recipient_name: e.target.value })} />
                  </label>
                  <label>
                    Tél. bénéficiaire *
                    <input required value={refundForm.recipient_phone} onChange={(e) => updateRefund({ recipient_phone: e.target.value })} />
                  </label>
                  <label>
                    Lien avec le patient
                    <input value={refundForm.recipient_relationship} onChange={(e) => updateRefund({ recipient_relationship: e.target.value })} />
                  </label>
                </div>
                <label className="reception-his-notes-field">
                  Notes
                  <textarea rows={2} value={refundForm.reason_notes} onChange={(e) => updateRefund({ reason_notes: e.target.value })} />
                </label>
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Mode de remboursement</legend>
                  <p className="clinical-hint">Indiquez comment le remboursement sera effectué (espèces, Orange Money, virement, etc.)</p>
                  <PaymentMethodRadios
                    name="refund_method"
                    value={refundForm.refund_method}
                    onChange={(v) => updateRefund({ refund_method: v })}
                    methods={REFUND_METHODS}
                  />
                </fieldset>
              </fieldset>
              <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>Soumettre remboursement</button>
            </form>

            <fieldset className="reception-his-payment-history">
              <legend>Historique des remboursements</legend>
              <table>
                <thead>
                  <tr>
                    <th>N° remboursement</th>
                    <th>Facture</th>
                    <th>Montant</th>
                    <th>Mode</th>
                    <th>Statut</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRefunds.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="reception-his-empty-row">Aucun remboursement enregistré.</td>
                    </tr>
                  ) : (
                    filteredRefunds.map((r) => (
                      <tr key={r.id}>
                        <td>{r.refund_number}</td>
                        <td>{r.invoice_number || '—'}</td>
                        <td>{formatGNF(r.refund_amount_gnf || 0)}</td>
                        <td>{methodLabel(REFUND_METHODS, r.refund_method)}</td>
                        <td>{refundStatusLabel(r.status)}</td>
                        <td>
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
                            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => printRefundReceipt(r.id)}>Imprimer reçu</button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </fieldset>
          </div>
        </section>
      )}
    </div>
  );
}
