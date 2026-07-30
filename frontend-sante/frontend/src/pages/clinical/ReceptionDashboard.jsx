import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import PatientRegistrationPrint from '../../components/print/PatientRegistrationPrint.jsx';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import { SPECIALTY_OTHER_CODE, PAYER_TYPE_OPTIONS, payerTypeLabel } from '../../constants/clinicBranding.js';
import './clinical.css';

const TABS = [
  { id: 'dashboard', label: 'Tableau de bord', shortcut: '1' },
  { id: 'register', label: 'Enregistrement', shortcut: '2' },
  { id: 'admission', label: 'Admission', shortcut: '3' },
  { id: 'billing', label: 'Facturation', shortcut: '4' },
  { id: 'refund', label: 'Remboursement', shortcut: '5' },
  { id: 'service_requests', label: 'Demandes de service', shortcut: '6' },
];

const DEFAULT_ADMISSION_SERVICES = [
  'Consultation urgences',
  'Consultation spécialisée',
  'Consultation externe',
  'Laboratoire',
  'Pharmacie',
  'Hospitalisation',
  'Imagerie médicale',
];
const DEFAULT_BILLING_DEPARTMENTS = [
  'Consultation urgences',
  'Consultation spécialisée',
  'Consultation externe',
  'Laboratoire',
  'Pharmacie',
  'Hospitalisation',
  'Imagerie médicale',
  'Urgences',
  'Soins infirmiers',
];
const ADMISSION_TYPES = [
  { value: 'emergency', label: 'Urgence' },
  { value: 'outpatient', label: 'Consultation externe' },
  { value: 'specialized_consultation', label: 'Consultation spécialisée' },
  { value: 'hospitalization', label: 'Hospitalisation' },
];
const RELATIONSHIP_OPTIONS = [
  { value: 'Père', label: 'Père' },
  { value: 'Mère', label: 'Mère' },
  { value: 'Fils', label: 'Fils' },
  { value: 'Fille', label: 'Fille' },
  { value: 'Autre', label: 'Autre' },
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
  { value: 'bank_transfer', label: 'Virement bancaire' },
  { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance_adjustment', label: 'Assurance' },
];
const REFUND_REASONS = [
  { value: 'deceased', label: 'Décès' },
  { value: 'service_cancelled', label: 'Service annulé' },
  { value: 'overpayment', label: 'Trop-perçu' },
  { value: 'other', label: 'Autre' },
];

const todayStr = new Date().toISOString().slice(0, 10);

const FIELD_HINTS = {
  patientId: 'Le numéro dossier sera généré automatiquement après enregistrement.',
  admissionNumber: 'Généré automatiquement après création de l\'admission.',
  invoiceNumber: 'Généré automatiquement après création de la facture.',
  refundNumber: 'Généré automatiquement après soumission.',
  age: 'Calculé automatiquement à partir de la date de naissance.',
};

const PATIENT_REQUIRED_NOTICE = 'Veuillez rechercher et sélectionner un patient.';
const INVOICE_PAYMENT_NOTICE = 'Créez ou sélectionnez une facture pour afficher le récapitulatif de paiement.';

const EMPTY_REG = {
  is_newborn: false,
  registration_date: todayStr,
  first_name: '',
  last_name: '',
  date_of_birth: '',
  date_of_birth_precision: 'full',
  birth_year: '',
  age_years: '',
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
  emergency_relationship_other: '',
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
  services: ['Consultation externe'],
  admission_type: 'outpatient',
  attending_clinician_user_id: '',
  attending_physician_name: '',
  confirmation_status: 'confirmed',
  specialty_code: '',
  specialty_other: '',
  notes: '',
};

const EMPTY_BILLING = {
  billing_date: todayStr,
  department: 'Consultation externe',
  exemption_percent: '0',
};
const newPaymentLineId = () => `pay-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
const emptyPaymentLine = () => ({ id: newPaymentLineId(), amount_gnf: '', payment_method: 'orange_money', reference: '' });
const EMPTY_REFUND = {
  invoice_id: '',
  service_paid_for: '',
  amount_consumed_gnf: '',
  refund_amount_gnf: '',
  recipient_name: '',
  recipient_phone: '',
  refund_method: 'orange_money',
  reason: 'service_cancelled',
  reason_notes: '',
};

const SERVICE_REQUEST_CATEGORIES = [
  { value: 'laboratory', label: 'Laboratoire' },
  { value: 'imaging', label: 'Imagerie' },
  { value: 'consultation', label: 'Consultation spécialisée' },
  { value: 'surgery', label: 'Actes chirurgicaux' },
  { value: 'nursing', label: 'Soins infirmiers' },
  { value: 'pharmacy', label: 'Pharmacie' },
  { value: 'doctor', label: 'Médecin' },
  { value: 'service', label: 'Services / Prestations' },
  { value: 'other', label: 'Autre' },
];

const SERVICE_REQUEST_STATUSES = [
  { value: 'pending', label: 'En attente' },
  { value: 'approved', label: 'Approuvée' },
  { value: 'completed', label: 'Terminée' },
  { value: 'cancelled', label: 'Annulée' },
];

const SERVICE_REQUEST_CHARGE_TYPES = {
  laboratory: 'laboratory',
  imaging: 'imaging',
  consultation: 'consultation',
  surgery: 'procedure',
  nursing: 'procedure',
  pharmacy: 'pharmacy',
  doctor: 'consultation',
  service: 'procedure',
  other: 'other',
};

const SERVICE_REQUEST_DEPARTMENTS = {
  laboratory: 'Laboratoire',
  imaging: 'Imagerie médicale',
  consultation: 'Consultation spécialisée',
  surgery: 'Chirurgie',
  nursing: 'Soins infirmiers',
  pharmacy: 'Pharmacie',
  doctor: 'Consultation spécialisée',
  service: 'Soins infirmiers',
  other: 'Urgences',
};

const EMPTY_SERVICE_REQUEST = {
  service_category: 'laboratory',
  service_name: '',
  catalog_code: '',
  charge_type: 'laboratory',
  unit_price_gnf: 0,
  status: 'pending',
};

const DEFAULT_SERVICE_PRESTATIONS = [
  { code: 'emergency_care_with_serum', label: "Soins d'urgence avec sérum", price_gnf: 500000 },
  { code: 'injection', label: 'Injection', price_gnf: 25000 },
  { code: 'small_dressing', label: 'Petit pansement', price_gnf: 30000 },
  { code: 'large_dressing', label: 'Grand pansement', price_gnf: 80000 },
  { code: 'pediatric_emergency_care', label: "Soins d'urgence pédiatrie", price_gnf: 250000 },
  { code: 'medical_transport_ambulance', label: 'Transport médical / Ambulance', price_gnf: 0 },
];

const DASHBOARD_BUCKET_TITLES = {
  total_patients: 'Total patients',
  patients_registered_today: 'Patients inscrits aujourd\'hui',
  admissions_today: 'Admissions aujourd\'hui',
  hospitalized_patients: 'Patients hospitalisés',
  paid_invoices: 'Factures payées',
  unpaid_invoices: 'Factures impayées',
  revenue_today: 'Recette du jour',
  revenue_month: 'Recette du mois',
  refunds: 'Remboursements',
};

const serviceRequestStatusLabel = (status) =>
  SERVICE_REQUEST_STATUSES.find((s) => s.value === status)?.label || status || '—';

const serviceRequestCategoryLabel = (cat) =>
  SERVICE_REQUEST_CATEGORIES.find((c) => c.value === cat)?.label || cat || '—';

const formatDateTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return String(value);
  }
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

const ReadOnlyDisplay = ({ value, hint }) => (
  <div className="reception-his-readonly-wrap">
    <div
      className={`reception-his-auto-display${value ? ' reception-his-auto-display--filled' : ' reception-his-auto-display--empty'}`}
      aria-live="polite"
    >
      {value || ''}
    </div>
    {hint && !value ? <span className="reception-his-field-hint">{hint}</span> : null}
  </div>
);

const AmountDisplay = ({ amountGnf, hint }) => {
  const hasAmount = amountGnf != null && amountGnf !== '' && !Number.isNaN(Number(amountGnf));
  return (
    <ReadOnlyDisplay
      value={hasAmount ? formatGNF(Number(amountGnf)) : ''}
      hint={hint}
    />
  );
};

const DisplayField = ({ label, value, hint }) => (
  <label>
    {label}
    <ReadOnlyDisplay value={value} hint={hint} />
  </label>
);

const FormNotice = ({ children }) => (
  children ? <p className="reception-his-form-notice">{children}</p> : null
);

const GeneratedIdBanner = ({ label, value }) => {
  if (!value) return null;
  return (
    <div className="reception-his-generated-id">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
};

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
  const regPrintRef = useRef(null);

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
  const [registrationPrintForm, setRegistrationPrintForm] = useState(null);
  const [lastAdmission, setLastAdmission] = useState(null);
  const [lastRefund, setLastRefund] = useState(null);

  const [invoices, setInvoices] = useState([]);
  const [activeInvoice, setActiveInvoice] = useState(null);
  const [refunds, setRefunds] = useState([]);

  const [regForm, setRegForm] = useState(EMPTY_REG);
  const [admissionForm, setAdmissionForm] = useState(EMPTY_ADMISSION);
  const [admissionImagingCode, setAdmissionImagingCode] = useState('');
  const [admissionLabSearchQ, setAdmissionLabSearchQ] = useState('');
  const [admissionLabSelection, setAdmissionLabSelection] = useState(null);
  const [billingForm, setBillingForm] = useState(EMPTY_BILLING);
  const [paymentLines, setPaymentLines] = useState([emptyPaymentLine()]);
  const [selectedSpecialty, setSelectedSpecialty] = useState('');
  const [selectedImaging, setSelectedImaging] = useState('');
  const [refundForm, setRefundForm] = useState(EMPTY_REFUND);

  const [invoiceSearchQ, setInvoiceSearchQ] = useState('');
  const [invoiceSearchHits, setInvoiceSearchHits] = useState([]);
  const [billingCatalog, setBillingCatalog] = useState(null);
  const [billingLineItems, setBillingLineItems] = useState([]);
  const [labSearchQ, setLabSearchQ] = useState('');
  const [activeStatBucket, setActiveStatBucket] = useState(null);
  const [queueRows, setQueueRows] = useState([]);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [serviceRequests, setServiceRequests] = useState([]);
  const [serviceRequestSearchQ, setServiceRequestSearchQ] = useState('');
  const [serviceRequestExamSearchQ, setServiceRequestExamSearchQ] = useState('');
  const [serviceRequestStatusFilter, setServiceRequestStatusFilter] = useState('');
  const [serviceRequestForm, setServiceRequestForm] = useState(EMPTY_SERVICE_REQUEST);
  const [editingServiceRequestId, setEditingServiceRequestId] = useState(null);
  const [loadingServiceRequests, setLoadingServiceRequests] = useState(false);
  const [lastCreatedServiceRequest, setLastCreatedServiceRequest] = useState(null);
  const [billingServiceRequestId, setBillingServiceRequestId] = useState('');
  const [loadingBillingServiceRequest, setLoadingBillingServiceRequest] = useState(false);

  const updateReg = (v) => setRegForm((p) => ({ ...p, ...v }));
  const updateAdmission = (v) => setAdmissionForm((p) => ({ ...p, ...v }));
  const updateBilling = (v) => setBillingForm((p) => ({ ...p, ...v }));
  const updatePaymentLine = (id, patch) =>
    setPaymentLines((rows) => rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  const addPaymentLine = () => setPaymentLines((rows) => [...rows, emptyPaymentLine()]);
  const removePaymentLine = (id) =>
    setPaymentLines((rows) => (rows.length <= 1 ? rows : rows.filter((r) => r.id !== id)));

  const specializedSpecialties = billingCatalog?.specialized_specialties || [];

  const resolveSpecialtyLabel = (code, other) => {
    if (code === SPECIALTY_OTHER_CODE) return (other || '').trim();
    return specializedSpecialties.find((s) => s.code === code)?.label || '';
  };

  const syncSpecialtyCode = (code) => {
    updateAdmission({ specialty_code: code });
    setSelectedSpecialty(code);
  };

  const syncSpecialtyOther = (text) => {
    updateAdmission({ specialty_other: text });
  };

  const showSpecialtyPicker =
    admissionForm.admission_type === 'specialized_consultation'
    || (admissionForm.services || []).includes('Consultation spécialisée');

  const renderSpecialtyPicker = (idSuffix = '', { required = showSpecialtyPicker } = {}) => (
    <div className="reception-his-specialty-picker">
      <label htmlFor={`specialty-select-${idSuffix}`}>
        Spécialité (consultation spécialisée) *
        <select
          id={`specialty-select-${idSuffix}`}
          required={required}
          value={admissionForm.specialty_code || selectedSpecialty}
          onChange={(e) => syncSpecialtyCode(e.target.value)}
        >
          <option value="">Choisir une spécialité…</option>
          {specializedSpecialties.map((spec) => (
            <option key={spec.code} value={spec.code}>
              {spec.label} · {formatGNF(spec.price_gnf || 250000)}
            </option>
          ))}
          <option value={SPECIALTY_OTHER_CODE}>Autre</option>
        </select>
      </label>
      {(admissionForm.specialty_code === SPECIALTY_OTHER_CODE || selectedSpecialty === SPECIALTY_OTHER_CODE) && (
        <label>
          Préciser la spécialité
          <input
            required
            value={admissionForm.specialty_other || ''}
            onChange={(e) => syncSpecialtyOther(e.target.value)}
            placeholder="Saisir la spécialité…"
          />
        </label>
      )}
    </div>
  );

  const addSpecializedConsultation = () => {
    const code = admissionForm.specialty_code || selectedSpecialty;
    const label = resolveSpecialtyLabel(code, admissionForm.specialty_other);
    if (!code) {
      setError('Sélectionnez une spécialité pour la consultation spécialisée.');
      return;
    }
    if (!label) {
      setError('Précisez la spécialité pour « Autre ».');
      return;
    }
    const spec = specializedSpecialties.find((s) => s.code === code);
    const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'specialized_consultation');
    const price = Number(spec?.price_gnf ?? svc?.price_gnf ?? 250000);
    addBillingLine({
      charge_type: svc?.charge_type || 'consultation',
      description: `Consultation spécialisée — ${label}`,
      quantity: 1,
      unit_price_gnf: price,
    });
    updateBilling({ department: 'Consultation spécialisée' });
    syncSpecialtyCode('');
    syncSpecialtyOther('');
    setError('');
  };

  const addEmergencyConsultation = () => {
    const code = admissionForm.specialty_code || selectedSpecialty;
    const label = resolveSpecialtyLabel(code, admissionForm.specialty_other);
    const spec = specializedSpecialties.find((s) => s.code === code);
    const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'emergency_consultation');
    const price = Number(spec?.emergency_price_gnf ?? svc?.price_gnf ?? 150000);
    const desc = label ? `Consultation d'urgences — ${label}` : (svc?.label || "Consultation d'urgences");
    addBillingLine({
      charge_type: svc?.charge_type || 'consultation',
      description: desc,
      quantity: 1,
      unit_price_gnf: price,
    });
    updateBilling({ department: "Consultation urgences" });
    setError('');
  };

  const imagingExaminations = billingCatalog?.imaging_examinations || [];

  const addImagingExam = () => {
    if (!selectedImaging) {
      setError('Sélectionnez un examen d\'imagerie médicale.');
      return;
    }
    const exam = imagingExaminations.find((e) => e.code === selectedImaging);
    if (!exam) return;
    addBillingLine({
      charge_type: 'radiology',
      description: exam.label,
      quantity: 1,
      unit_price_gnf: exam.price_gnf,
    });
    updateBilling({ department: 'Imagerie médicale' });
    setSelectedImaging('');
    setError('');
  };

  const prefillPaymentLines = (remaining) => {
    const amt = Number(remaining) || 0;
    setPaymentLines([{ ...emptyPaymentLine(), amount_gnf: amt > 0 ? String(amt) : '' }]);
  };
  const updateRefund = (v) => setRefundForm((p) => {
    const next = { ...p, ...v };
    if ('amount_consumed_gnf' in v && next.invoice_id) {
      const inv = invoices.find((item) => String(item.id) === String(next.invoice_id));
      const paid = Number(inv?.paid_amount_gnf || 0);
      const consumed = Number(next.amount_consumed_gnf || 0);
      if (next.amount_consumed_gnf !== '') {
        next.refund_amount_gnf = String(Math.max(0, paid - consumed));
      }
    }
    return next;
  });

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
    clinicalApi.receptionHisBillingCatalog().then((r) => setBillingCatalog(r.data || null)).catch(() => setBillingCatalog(null));
  }, [loadDashboard]);


  const loadServiceRequests = useCallback(async () => {
    setLoadingServiceRequests(true);
    try {
      const params = {};
      if (selectedPatient?.id) params.patient_id = selectedPatient.id;
      if (serviceRequestSearchQ.trim()) params.q = serviceRequestSearchQ.trim();
      if (serviceRequestStatusFilter) params.status = serviceRequestStatusFilter;
      const { data } = await clinicalApi.receptionHisListServiceRequests(params);
      setServiceRequests(data || []);
    } catch {
      setServiceRequests([]);
    } finally {
      setLoadingServiceRequests(false);
    }
  }, [selectedPatient?.id, serviceRequestSearchQ, serviceRequestStatusFilter]);

  const loadQueueBucket = async (bucket) => {
    if (activeStatBucket === bucket) {
      setActiveStatBucket(null);
      setQueueRows([]);
      return;
    }
    setActiveStatBucket(bucket);
    setLoadingQueue(true);
    setError('');
    try {
      const { data } = await clinicalApi.receptionHisDashboardQueue(bucket);
      setQueueRows(data || []);
    } catch (err) {
      setQueueRows([]);
      setError(formatApiError(err, 'Impossible de charger la liste'));
    } finally {
      setLoadingQueue(false);
    }
  };

  const openInvoiceById = async (invoiceId, patientId) => {
    if (!invoiceId) return;
    if (patientId) {
      await selectPatient({ id: patientId });
    }
    try {
      const { data } = await clinicalApi.receptionHisGetInvoice(invoiceId);
      if (data) {
        setActiveInvoice(data);
        setTab('billing');
      }
    } catch {
      setError('Impossible d\'ouvrir la facture.');
    }
  };

  const resetServiceRequestForm = () => {
    setServiceRequestForm(EMPTY_SERVICE_REQUEST);
    setServiceRequestExamSearchQ('');
    setEditingServiceRequestId(null);
  };

  const startEditServiceRequest = (row) => {
    setEditingServiceRequestId(row.id);
    setServiceRequestForm({
      service_category: row.service_category,
      service_name: row.service_name,
      catalog_code: row.catalog_code || '',
      charge_type: row.charge_type || SERVICE_REQUEST_CHARGE_TYPES[row.service_category] || 'other',
      unit_price_gnf: Number(row.unit_price_gnf || 0),
      status: row.status,
    });
    setServiceRequestExamSearchQ(row.service_name || '');
  };

  const saveServiceRequest = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Sélectionnez un patient pour créer une demande de service.');
    if (!serviceRequestForm.service_name.trim()) return setError('Indiquez le nom du service.');
    setLoading(true);
    setError('');
    try {
      const payload = {
        service_category: serviceRequestForm.service_category,
        service_name: serviceRequestForm.service_name.trim(),
        department: SERVICE_REQUEST_DEPARTMENTS[serviceRequestForm.service_category] || null,
        catalog_code: serviceRequestForm.catalog_code || null,
        charge_type:
          serviceRequestForm.charge_type
          || SERVICE_REQUEST_CHARGE_TYPES[serviceRequestForm.service_category]
          || 'other',
        unit_price_gnf: Number(serviceRequestForm.unit_price_gnf || 0),
        status: serviceRequestForm.status,
      };
      if (editingServiceRequestId) {
        await clinicalApi.receptionHisUpdateServiceRequest(editingServiceRequestId, payload);
        setMessage('Demande de service mise à jour.');
        setLastCreatedServiceRequest(null);
      } else {
        const { data } = await clinicalApi.receptionHisCreateServiceRequest({
          patient_id: selectedPatient.id,
          ...payload,
        });
        setLastCreatedServiceRequest(data);
        setMessage(
          `Demande enregistrée (${data.request_number}). Collez ce N° en facturation pour l'ajouter au tableau Produits / Services.`
        );
      }
      resetServiceRequestForm();
      await loadServiceRequests();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement de la demande impossible'));
    } finally {
      setLoading(false);
    }
  };

  const deleteServiceRequest = async (id) => {
    if (!window.confirm('Supprimer cette demande de service ?')) return;
    setLoading(true);
    try {
      await clinicalApi.receptionHisDeleteServiceRequest(id);
      setMessage('Demande de service supprimée.');
      if (editingServiceRequestId === id) resetServiceRequestForm();
      await loadServiceRequests();
    } catch (err) {
      setError(formatApiError(err, 'Suppression impossible'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === 'service_requests') {
      loadServiceRequests();
    }
  }, [tab, loadServiceRequests]);

  const filteredAdmissionLabTests = useMemo(() => {
    const tests = billingCatalog?.lab_tests || [];
    const q = admissionLabSearchQ.trim().toLowerCase();
    if (!q) return tests.slice(0, 12);
    return tests.filter((t) => `${t.name} ${t.code}`.toLowerCase().includes(q)).slice(0, 12);
  }, [billingCatalog, admissionLabSearchQ]);

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
    setLastAdmission(null);
    setLastRefund(null);
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

  const printRegistrationSheet = () => {
    if (!registeredPatient) return;
    window.print();
  };

  const resolveRelationship = (form) => {
    if (form.emergency_relationship === 'Autre') {
      return form.emergency_relationship_other?.trim() || 'Autre';
    }
    return form.emergency_relationship || undefined;
  };

  const renderQueueTable = () => {
    if (!activeStatBucket) return null;
    if (loadingQueue) return <p className="clinical-hint">Chargement…</p>;
    if (!queueRows.length) return <p className="clinical-hint">Aucun élément dans cette liste.</p>;

    const bucket = activeStatBucket;
    if (bucket === 'total_patients' || bucket === 'patients_registered_today') {
      return (
        <table className="lab-his-queue-table">
          <thead>
            <tr><th>Patient</th><th>N° dossier</th><th>Téléphone</th><th>Sexe</th><th>Date inscription</th><th /></tr>
          </thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={`${row.patient_id}-${row.patient_number}`}>
                <td>{row.patient_name}</td>
                <td>{row.patient_number || row.patient_id}</td>
                <td>{row.phone || '—'}</td>
                <td>{row.gender || '—'}</td>
                <td>{formatDateTime(row.registration_date)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectPatient({ id: row.patient_id })}>Ouvrir</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'admissions_today') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>Heure admission</th><th>Service</th><th>Statut</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.admission_id}>
                <td>{row.patient_name}</td>
                <td>{formatDateTime(row.admitted_at)}</td>
                <td>{row.department || '—'}</td>
                <td>{row.status}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectPatient({ id: row.patient_id })}>Ouvrir patient</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'hospitalized_patients') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>Chambre</th><th>Médecin</th><th>Date admission</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.admission_id}>
                <td>{row.patient_name}</td>
                <td>{row.room || '—'}</td>
                <td>{row.doctor_name || '—'}</td>
                <td>{formatDateTime(row.admitted_at)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectPatient({ id: row.patient_id })}>Ouvrir patient</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'paid_invoices') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>N° facture</th><th>Montant</th><th>Mode paiement</th><th>Date paiement</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.invoice_id}>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number}</td>
                <td>{formatGNF(row.amount_gnf || 0)}</td>
                <td>{methodLabel(PAYMENT_METHODS, row.payment_method)}</td>
                <td>{formatDateTime(row.paid_at)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openInvoiceById(row.invoice_id, row.patient_id)}>Ouvrir facture</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'unpaid_invoices') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>N° facture</th><th>Solde dû</th><th>Date facture</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.invoice_id}>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number}</td>
                <td>{formatGNF(row.outstanding_balance_gnf || 0)}</td>
                <td>{formatDateTime(row.issued_at)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openInvoiceById(row.invoice_id, row.patient_id)}>Ouvrir facture</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'revenue_today' || bucket === 'revenue_month') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>N° facture</th><th>Montant</th><th>Mode</th><th>Date / heure</th></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={`${row.payment_id}-${row.invoice_id}`}>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number || '—'}</td>
                <td>{formatGNF(row.amount_gnf || 0)}</td>
                <td>{methodLabel(PAYMENT_METHODS, row.payment_method)}</td>
                <td>{formatDateTime(row.paid_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'refunds') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>N° remboursement</th><th>Patient</th><th>Facture</th><th>Montant</th><th>Raison</th><th>Statut</th><th>Date</th></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.refund_id}>
                <td>{row.refund_number}</td>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number || '—'}</td>
                <td>{formatGNF(row.refund_amount_gnf || 0)}</td>
                <td>{row.reason}</td>
                <td>{refundStatusLabel(row.status)}</td>
                <td>{formatDateTime(row.paid_at || row.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    return null;
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const manualAge = regForm.age_years !== '' ? Number(regForm.age_years) : null;
      const resolvedDob =
        regForm.date_of_birth_precision === 'year' && regForm.birth_year.length === 4
          ? `${regForm.birth_year}-01-01`
          : (regForm.date_of_birth_precision === 'full' && regForm.date_of_birth ? regForm.date_of_birth : null);
      if (!resolvedDob && (manualAge == null || !Number.isFinite(manualAge))) {
        setError('Indiquez une date de naissance, une année de naissance ou saisissez l’âge du patient.');
        return;
      }
      const payload = {
        first_name: regForm.first_name.trim(),
        last_name: regForm.last_name.trim(),
        date_of_birth: resolvedDob,
        date_of_birth_precision: resolvedDob ? regForm.date_of_birth_precision : 'unknown',
        age_years: manualAge != null && Number.isFinite(manualAge) ? manualAge : undefined,
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
          relationship: resolveRelationship(regForm),
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
      setRegistrationPrintForm({ ...regForm });
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
      let services = (admissionForm.services || []).filter(Boolean);
      if (!services.length) return setError('Sélectionnez au moins un service.');
      if (showSpecialtyPicker) {
        const specialtyLabel = resolveSpecialtyLabel(admissionForm.specialty_code, admissionForm.specialty_other);
        if (!admissionForm.specialty_code) {
          return setError('Sélectionnez une spécialité pour la consultation spécialisée.');
        }
        if (!specialtyLabel) {
          return setError('Précisez la spécialité pour « Autre ».');
        }
        if (services.includes('Consultation spécialisée')) {
          services = services.map((s) =>
            s === 'Consultation spécialisée' ? `Consultation spécialisée — ${specialtyLabel}` : s
          );
        }
        if (admissionForm.admission_type === 'specialized_consultation' && !services.some((s) => s.startsWith('Consultation spécialisée'))) {
          services.push(`Consultation spécialisée — ${specialtyLabel}`);
        }
      }
      if (services.includes('Imagerie médicale')) {
        if (!admissionImagingCode) {
          return setError('Sélectionnez un examen d\'imagerie médicale.');
        }
        const exam = imagingExaminations.find((e) => e.code === admissionImagingCode);
        if (exam) {
          services = services.map((s) => (s === 'Imagerie médicale' ? `Imagerie médicale — ${exam.label}` : s));
        }
      }
      if (services.includes('Laboratoire')) {
        if (!admissionLabSelection) {
          return setError('Sélectionnez un examen de laboratoire.');
        }
        services = services.map((s) =>
          s === 'Laboratoire' ? `Laboratoire — ${admissionLabSelection.name}` : s
        );
      }
      const { data } = await clinicalApi.receptionHisCreateAdmission({
        patient_id: selectedPatient.id,
        admission_date: admissionForm.admission_date,
        admission_time: `${admissionForm.admission_time}:00`,
        services,
        department: services[0],
        admission_type: admissionForm.admission_type,
        attending_clinician_user_id: admissionForm.attending_clinician_user_id
          ? Number(admissionForm.attending_clinician_user_id)
          : undefined,
        attending_physician_name: admissionForm.attending_physician_name || undefined,
        confirmation_status: admissionForm.confirmation_status,
        specialty_code: admissionForm.specialty_code || undefined,
        specialty_other: admissionForm.specialty_other || undefined,
        notes: admissionForm.notes || undefined,
      });
      setLastAdmission(data || null);
      setAdmissionImagingCode('');
      setAdmissionLabSelection(null);
      setAdmissionLabSearchQ('');
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
    if (!selectedPatient?.id) return setError('Recherchez et sélectionnez un patient avant de créer la facture.');
    if (billingLineItems.length === 0) return setError('Ajoutez au moins une prestation à la facture.');
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.receptionHisCreateInvoice({
        patient_id: selectedPatient.id,
        department: billingForm.department,
        items: billingLineItems.map((l) => ({
          charge_type: l.charge_type,
          description: l.description,
          quantity: Number(l.quantity || 1),
          unit_price_gnf: Number(l.unit_price_gnf || 0),
          source_type: l.source_type || 'reception',
        })),
        exemption_percent: Number(billingForm.exemption_percent || 0),
        billing_date: billingForm.billing_date || undefined,
      });
      setActiveInvoice(data || null);
      setBillingLineItems([]);
      prefillPaymentLines(data?.remaining_balance_gnf ?? data?.total_amount_gnf ?? 0);
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
    prefillPaymentLines(inv?.remaining_balance_gnf ?? 0);
    updateRefund({
      invoice_id: inv ? String(inv.id) : '',
      service_paid_for: inv?.department || '',
      amount_consumed_gnf: '',
      refund_amount_gnf: '',
    });
  };

  const handlePayment = async (e) => {
    e.preventDefault();
    if (!activeInvoice?.id) return setError('Sélectionnez une facture du patient.');
    const lines = paymentLines.filter((l) => Number(l.amount_gnf) > 0);
    if (lines.length === 0) return setError('Ajoutez au moins une ligne de paiement avec un montant.');
    const draftTotal = lines.reduce((s, l) => s + Number(l.amount_gnf), 0);
    const remaining = Number(activeInvoice.remaining_balance_gnf ?? 0);
    if (draftTotal > remaining) {
      return setError(`Le total des paiements (${formatGNF(draftTotal)}) dépasse le reste à payer (${formatGNF(remaining)}).`);
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      let lastData = activeInvoice;
      for (const line of lines) {
        const { data } = await clinicalApi.receptionHisAddPayment(activeInvoice.id, {
          amount_gnf: Number(line.amount_gnf),
          payment_method: line.payment_method,
          reference: line.reference || undefined,
        });
        lastData = data || lastData;
      }
      setMessage(`Paiement(s) enregistré(s) · reste ${formatGNF(lastData?.remaining_balance_gnf || 0)}`);
      prefillPaymentLines(lastData?.remaining_balance_gnf ?? 0);
      setActiveInvoice(lastData || null);
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
    if (refundForm.reason === 'other' && !(refundForm.reason_notes || '').trim()) {
      return setError('Saisissez le motif du remboursement (Autre).');
    }
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
      { key: 'total_patients', label: 'Total patients', value: stats.total_patients ?? 0 },
      { key: 'patients_registered_today', label: 'Patients inscrits aujourd\'hui', value: stats.patients_registered_today ?? 0, variant: 'success' },
      { key: 'admissions_today', label: 'Admissions aujourd\'hui', value: stats.admissions_today ?? 0 },
      { key: 'hospitalized_patients', label: 'Patients hospitalisés', value: stats.hospitalized_patients ?? 0, variant: 'warning' },
      { key: 'paid_invoices', label: 'Factures payées', value: stats.paid_invoices ?? 0, variant: 'success' },
      { key: 'unpaid_invoices', label: 'Factures impayées', value: stats.unpaid_invoices ?? 0, variant: 'warning' },
      { key: 'revenue_today', label: 'Recette du jour', value: formatGNF(stats.revenue_today_gnf ?? 0), variant: 'accent' },
      { key: 'revenue_month', label: 'Recette du mois', value: formatGNF(stats.revenue_month_gnf ?? 0), variant: 'accent' },
      { key: 'refunds', label: 'Total remboursements', value: formatGNF(stats.refunds_total_gnf ?? 0) },
    ];
  }, [stats]);

  const filteredRefunds = useMemo(() => {
    if (!selectedPatient?.id) return [];
    return refunds.filter((r) => Number(r.patient_id) === Number(selectedPatient.id));
  }, [refunds, selectedPatient?.id]);

  const admissionServices = billingCatalog?.admission_services?.map((s) => s.label) || DEFAULT_ADMISSION_SERVICES;
  const billingDepartments = billingCatalog?.billing_departments || DEFAULT_BILLING_DEPARTMENTS;
  const servicePrestations = billingCatalog?.service_prestations || DEFAULT_SERVICE_PRESTATIONS;

  const addBillingLine = (line) => {
    setBillingLineItems((prev) => [...prev, { id: `line-${Date.now()}-${Math.random()}`, ...line }]);
  };

  const removeBillingLine = (id) => setBillingLineItems((prev) => prev.filter((l) => l.id !== id));

  const chooseServiceRequest = (category, name, extras = {}) => {
    setServiceRequestForm((prev) => ({
      ...prev,
      service_category: category,
      service_name: name,
      catalog_code: extras.catalog_code || '',
      charge_type: extras.charge_type || SERVICE_REQUEST_CHARGE_TYPES[category] || 'other',
      unit_price_gnf: Number(extras.unit_price_gnf ?? 0),
    }));
    setServiceRequestExamSearchQ(name);
    setError('');
  };

  const applyServiceRequestToBilling = async (request, { switchTab = true } = {}) => {
    if (!request?.id) return;
    if (selectedPatient?.id && Number(selectedPatient.id) !== Number(request.patient_id)) {
      await selectPatient({ id: request.patient_id });
    } else if (!selectedPatient?.id) {
      await selectPatient({ id: request.patient_id });
    }
    const chargeType =
      request.charge_type
      || SERVICE_REQUEST_CHARGE_TYPES[request.service_category]
      || 'other';
    const department =
      request.department
      || SERVICE_REQUEST_DEPARTMENTS[request.service_category]
      || billingForm.department;
    updateBilling({ department });
    addBillingLine({
      charge_type: chargeType,
      description: `${request.service_name} [${request.request_number}]`,
      quantity: 1,
      unit_price_gnf: Number(request.unit_price_gnf || 0),
      source_type: 'service_request',
      source_ref: request.request_number,
    });
    setBillingServiceRequestId(request.request_number || '');
    setLastCreatedServiceRequest(request);
    if (switchTab) setTab('billing');
    setMessage(`Demande ${request.request_number} ajoutée au tableau Produits / Services.`);
    setError('');
  };

  const loadServiceRequestIntoBilling = async (e) => {
    e?.preventDefault?.();
    const q = billingServiceRequestId.trim();
    if (!q) return setError('Collez le N° de demande de service (DSR-…).');
    setLoadingBillingServiceRequest(true);
    setError('');
    try {
      const { data } = await clinicalApi.receptionHisLookupServiceRequest(q);
      await applyServiceRequestToBilling(data, { switchTab: false });
    } catch (err) {
      setError(formatApiError(err, 'Demande de service introuvable'));
    } finally {
      setLoadingBillingServiceRequest(false);
    }
  };

  const billingSubtotal = useMemo(
    () => billingLineItems.reduce((sum, l) => sum + Number(l.quantity || 1) * Number(l.unit_price_gnf || 0), 0),
    [billingLineItems]
  );

  const draftExemptionPercent = Number(billingForm.exemption_percent || 0);
  const draftExemptionAmount = Math.round(billingSubtotal * draftExemptionPercent / 100);
  const draftNetTotal = Math.max(0, billingSubtotal - draftExemptionAmount);

  const filteredLabTests = useMemo(() => {
    const tests = billingCatalog?.lab_tests || [];
    const q = labSearchQ.trim().toLowerCase();
    if (!q) return tests;
    return tests.filter(
      (t) => String(t.name || '').toLowerCase().includes(q) || String(t.code || '').toLowerCase().includes(q)
    );
  }, [billingCatalog, labSearchQ]);

  const filteredServiceRequestLabTests = useMemo(() => {
    const tests = billingCatalog?.lab_tests || [];
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return tests;
    return tests.filter(
      (t) => String(t.name || '').toLowerCase().includes(q) || String(t.code || '').toLowerCase().includes(q)
    );
  }, [billingCatalog, serviceRequestExamSearchQ]);

  const filteredServiceRequestSpecialties = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return specializedSpecialties;
    return specializedSpecialties.filter(
      (s) => String(s.label || '').toLowerCase().includes(q) || String(s.code || '').toLowerCase().includes(q)
    );
  }, [specializedSpecialties, serviceRequestExamSearchQ]);

  const filteredServiceRequestImaging = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return imagingExaminations;
    return imagingExaminations.filter(
      (e) => String(e.label || '').toLowerCase().includes(q) || String(e.code || '').toLowerCase().includes(q)
    );
  }, [imagingExaminations, serviceRequestExamSearchQ]);

  const filteredServicePrestations = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return servicePrestations;
    return servicePrestations.filter(
      (svc) => String(svc.label || '').toLowerCase().includes(q) || String(svc.code || '').toLowerCase().includes(q)
    );
  }, [servicePrestations, serviceRequestExamSearchQ]);

  const surgicalActs = billingCatalog?.surgical_acts || [];
  const filteredSurgicalActs = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return surgicalActs;
    return surgicalActs.filter(
      (act) => String(act.label || '').toLowerCase().includes(q) || String(act.code || '').toLowerCase().includes(q)
    );
  }, [surgicalActs, serviceRequestExamSearchQ]);

  const refundInvoices = useMemo(() => {
    if (!invoiceSearchQ.trim()) return invoices;
    const q = invoiceSearchQ.trim().toLowerCase();
    const ids = new Set((invoiceSearchHits || []).map((x) => Number(x.id)));
    return invoices.filter((i) => String(i.invoice_number || '').toLowerCase().includes(q) || ids.has(Number(i.id)));
  }, [invoiceSearchQ, invoiceSearchHits, invoices]);

  const activeMeta = activeInvoice
    ? {
        subtotal: Number(activeInvoice.subtotal_amount_gnf ?? activeInvoice.total_amount_gnf ?? 0),
        exemptionPercent: Number(activeInvoice.exemption_percent || 0),
        exemptionAmount: Number(activeInvoice.exemption_amount_gnf || 0),
        total: Number(activeInvoice.total_amount_gnf || 0),
        paid: Number(activeInvoice.paid_amount_gnf || 0),
        remaining: Number(activeInvoice.remaining_balance_gnf || 0),
      }
    : null;

  const draftPaymentTotal = useMemo(
    () => paymentLines.reduce((s, l) => s + (Number(l.amount_gnf) || 0), 0),
    [paymentLines]
  );
  const draftRemainingAfterPay = activeMeta ? Math.max(0, activeMeta.remaining - draftPaymentTotal) : null;

  const patientDossier = selectedPatient?.patient_number || '';
  const patientDisplayName = patientFullName(selectedPatient);
  const patientPayerLabel = useMemo(() => {
    if (!selectedPatient) return '';
    try {
      const raw = selectedPatient.payer_json || selectedPatient.payer;
      if (!raw) return '';
      const payer = typeof raw === 'string' ? JSON.parse(raw) : raw;
      return payerTypeLabel(payer?.payer_type);
    } catch {
      return '';
    }
  }, [selectedPatient]);

  const PatientContextPanel = () => (
    <div className={`clinical-card reception-his-patient-context${selectedPatient ? ' reception-his-patient-context--active' : ''}`}>
      <h3>Patient sélectionné</h3>
      <div className="reception-his-patient-context-grid">
        <div><strong>N° dossier</strong><span className={selectedPatient?.patient_number ? 'reception-his-value-filled' : ''}>{selectedPatient?.patient_number || ''}</span></div>
        <div><strong>Nom</strong><span className={selectedPatient?.last_name ? 'reception-his-value-filled' : ''}>{selectedPatient?.last_name || ''}</span></div>
        <div><strong>Prénom</strong><span className={selectedPatient?.first_name ? 'reception-his-value-filled' : ''}>{selectedPatient?.first_name || ''}</span></div>
        <div><strong>Payeur</strong><span className={patientPayerLabel ? 'reception-his-value-filled' : ''}>{patientPayerLabel || ''}</span></div>
        <div><strong>Téléphone</strong><span className={selectedPatient?.phone ? 'reception-his-value-filled' : ''}>{selectedPatient?.phone || ''}</span></div>
        <div><strong>Âge</strong><span className={patientAge(selectedPatient) ? 'reception-his-value-filled' : ''}>{patientAge(selectedPatient)}</span></div>
        <div><strong>Sexe</strong><span className={selectedPatient?.gender ? 'reception-his-value-filled' : ''}>{genderLabel(selectedPatient?.gender)}</span></div>
      </div>
      {!selectedPatient && (
        <FormNotice>{PATIENT_REQUIRED_NOTICE}</FormNotice>
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
                  <button
                    type="button"
                    onClick={() => selectPatient(p)}
                  >
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
          <ClinicalStatGrid stats={statCards} onStatClick={loadQueueBucket} activeKey={activeStatBucket} />
          {activeStatBucket && (
            <section className="lab-his-queue-panel reception-his-queue-panel" aria-live="polite">
              <h3>{DASHBOARD_BUCKET_TITLES[activeStatBucket] || 'Liste détaillée'}</h3>
              <div className="lab-his-results-wrap">{renderQueueTable()}</div>
            </section>
          )}
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
          <form className="clinical-card reception-his-form-sheet" onSubmit={handleRegister}>
            <h2>Enregistrement patient</h2>
            <GeneratedIdBanner label="N° dossier patient généré" value={registeredPatient?.patient_number} />
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
              <DisplayField
                label="N° dossier patient"
                value={registeredPatient?.patient_number || ''}
                hint={registeredPatient?.patient_number ? undefined : FIELD_HINTS.patientId}
              />
              <label>Date inscription<input required type="date" value={regForm.registration_date} onChange={(e) => updateReg({ registration_date: e.target.value })} /></label>
              <label className="reception-his-check"><input type="checkbox" checked={regForm.is_newborn} onChange={(e) => updateReg({ is_newborn: e.target.checked })} />Nouveau-né</label>
              <label>Nom *<input required value={regForm.last_name} onChange={(e) => updateReg({ last_name: e.target.value })} /></label>
              <label>Prénom *<input required value={regForm.first_name} onChange={(e) => updateReg({ first_name: e.target.value })} /></label>
              <div className="reception-his-birthdate-field">
                <span>Date naissance *</span>
                <div className="reception-his-birthdate-modes">
                  <label>
                    <input
                      type="radio"
                      name="birth-date-mode"
                      value="full"
                      checked={regForm.date_of_birth_precision === 'full'}
                      onChange={() => updateReg({ date_of_birth_precision: 'full', birth_year: '' })}
                    />
                    Date complète (JJ/MM/AAAA)
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="birth-date-mode"
                      value="year"
                      checked={regForm.date_of_birth_precision === 'year'}
                      onChange={() => updateReg({ date_of_birth_precision: 'year', date_of_birth: '' })}
                    />
                    Année seulement (AAAA)
                  </label>
                </div>
                {regForm.date_of_birth_precision === 'year' ? (
                  <input
                    required
                    type="number"
                    inputMode="numeric"
                    min="1900"
                    max={new Date().getFullYear()}
                    placeholder="AAAA"
                    value={regForm.birth_year}
                    onChange={(e) => {
                      const year = e.target.value.replace(/[^\d]/g, '').slice(0, 4);
                      updateReg({
                        birth_year: year,
                        age_years: year.length === 4 ? String(new Date().getFullYear() - Number(year)) : regForm.age_years,
                      });
                    }}
                  />
                ) : (
                  <input
                    type="date"
                    value={regForm.date_of_birth}
                    onChange={(e) => {
                      const dob = e.target.value;
                      const age = calcAge(dob);
                      updateReg({
                        date_of_birth: dob,
                        age_years: age !== '' ? String(age) : regForm.age_years,
                      });
                    }}
                  />
                )}
              </div>
              <label>
                Âge *
                <input
                  required
                  type="number"
                  inputMode="numeric"
                  min="0"
                  max="130"
                  value={regForm.age_years}
                  onChange={(e) => updateReg({ age_years: e.target.value.replace(/[^\d]/g, '').slice(0, 3) })}
                  placeholder="Saisir ou corriger l’âge"
                />
                <span className="reception-his-field-hint">
                  Saisissable manuellement si la date exacte est inconnue.
                </span>
              </label>
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
                <label>
                  Relation *
                  <select
                    required
                    value={regForm.emergency_relationship}
                    onChange={(e) => updateReg({ emergency_relationship: e.target.value })}
                  >
                    <option value="">— Sélectionner —</option>
                    {RELATIONSHIP_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </label>
                {regForm.emergency_relationship === 'Autre' && (
                  <label>
                    Préciser la relation
                    <input
                      required
                      value={regForm.emergency_relationship_other}
                      onChange={(e) => updateReg({ emergency_relationship_other: e.target.value })}
                      placeholder="Saisir la relation…"
                    />
                  </label>
                )}
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
              <label>Type de payeur<select value={regForm.payer_type} onChange={(e) => updateReg({ payer_type: e.target.value })}>{PAYER_TYPE_OPTIONS.map((o) => (<option key={o.value} value={o.value}>{o.label}</option>))}</select></label>
              {regForm.payer_type === 'insurance' && (<><label>Compagnie d’assurance<input value={regForm.insurance_company} onChange={(e) => updateReg({ insurance_company: e.target.value })} /></label><label>Numéro d’assurance<input value={regForm.insurance_number} onChange={(e) => updateReg({ insurance_number: e.target.value })} /></label></>)}
              {regForm.payer_type === 'company' && <label>Nom de l’entreprise<input value={regForm.company_name} onChange={(e) => updateReg({ company_name: e.target.value })} /></label>}
              <label>Notes<textarea rows={2} value={regForm.payer_notes} onChange={(e) => updateReg({ payer_notes: e.target.value })} /></label>
            </div></fieldset>
            <button type="submit" className="clinical-btn" disabled={loading}>Enregistrer le patient</button>
            {registeredPatient && (
              <button
                type="button"
                className="clinical-btn clinical-btn--secondary"
                onClick={printRegistrationSheet}
              >
                Imprimer la fiche d&apos;enregistrement
              </button>
            )}
            {registeredPatient && (
              <button
                type="button"
                className="clinical-btn clinical-btn--secondary"
                onClick={() => {
                  setRegisteredPatient(null);
                  setRegistrationPrintForm(null);
                  setRegForm({ ...EMPTY_REG, registration_date: todayStr });
                  setMessage('');
                }}
              >
                Nouvel enregistrement
              </button>
            )}
          </form>
        </section>
      )}

      {tab === 'admission' && (
        <section className="reception-his-panel">
          <PatientContextPanel />
          <form className="clinical-card reception-his-form-sheet" onSubmit={handleAdmission}>
            <h2>Admission</h2>
            <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
            <GeneratedIdBanner label="N° admission généré" value={lastAdmission?.admission_number} />
            <fieldset>
              <legend>Admission</legend>
              <div className="reception-his-admission-grid">
                <div className="reception-his-admission-ids">
                  <DisplayField
                    label="N° d'admission"
                    value={lastAdmission?.admission_number || ''}
                    hint={lastAdmission?.admission_number ? undefined : FIELD_HINTS.admissionNumber}
                  />
                  <DisplayField label="N° dossier patient" value={patientDossier} />
                  <DisplayField label="Nom et prénom" value={patientDisplayName} />
                </div>

                <div className="reception-his-admission-services">
                  <span className="reception-his-multi-service-label">Services demandés *</span>
                  <div className="reception-his-multi-service-grid">
                    {admissionServices.map((svc) => (
                      <label key={svc} className="reception-his-check">
                        <input
                          type="checkbox"
                          checked={(admissionForm.services || []).includes(svc)}
                          onChange={() => {
                            const current = admissionForm.services || [];
                            updateAdmission({
                              services: current.includes(svc)
                                ? current.filter((s) => s !== svc)
                                : [...current, svc],
                            });
                          }}
                        />
                        {svc}
                      </label>
                    ))}
                  </div>
                </div>

                {(showSpecialtyPicker || (admissionForm.services || []).includes('Imagerie médicale') || (admissionForm.services || []).includes('Laboratoire')) && (
                  <div className="reception-his-admission-subopts">
                    {showSpecialtyPicker && renderSpecialtyPicker('admission')}
                    {(admissionForm.services || []).includes('Imagerie médicale') && imagingExaminations.length > 0 && (
                      <div className="reception-his-specialty-picker">
                        <label>
                          Examen d&apos;imagerie médicale *
                          <select
                            required
                            value={admissionImagingCode}
                            onChange={(e) => setAdmissionImagingCode(e.target.value)}
                          >
                            <option value="">Choisir un examen…</option>
                            {imagingExaminations.map((exam) => (
                              <option key={exam.code} value={exam.code}>{exam.label}</option>
                            ))}
                          </select>
                        </label>
                      </div>
                    )}
                    {(admissionForm.services || []).includes('Laboratoire') && (
                      <div className="reception-his-specialty-picker">
                        <label>
                          Examen de laboratoire *
                          <input
                            type="search"
                            value={admissionLabSearchQ}
                            onChange={(e) => setAdmissionLabSearchQ(e.target.value)}
                            placeholder="Rechercher un examen…"
                          />
                        </label>
                        {admissionLabSelection && (
                          <p className="clinical-hint">Sélectionné : <strong>{admissionLabSelection.name}</strong></p>
                        )}
                        {filteredAdmissionLabTests.length > 0 && (
                          <ul className="reception-his-lab-search-results">
                            {filteredAdmissionLabTests.map((test) => (
                              <li key={test.code}>
                                <button type="button" onClick={() => setAdmissionLabSelection(test)}>
                                  {test.name} ({test.code})
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="reception-his-admission-meta">
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
                      {doctors.map((d) => (
                        <option key={d.user_id || d.id} value={d.user_id || d.id}>
                          {d.name || d.full_name || d.email}
                        </option>
                      ))}
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
                    <select
                      value={admissionForm.admission_type}
                      onChange={(e) => {
                        const v = e.target.value;
                        const patch = { admission_type: v };
                        if (v === 'specialized_consultation') {
                          const current = admissionForm.services || [];
                          if (!current.includes('Consultation spécialisée')) {
                            patch.services = [...current, 'Consultation spécialisée'];
                          }
                        }
                        updateAdmission(patch);
                      }}
                    >
                      {ADMISSION_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </label>
                  <label>
                    Confirmation / rendez-vous
                    <select value={admissionForm.confirmation_status} onChange={(e) => updateAdmission({ confirmation_status: e.target.value })}>
                      {ADMISSION_CONFIRMATIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </label>
                  <label className="reception-his-notes-field reception-his-admission-notes">
                    Notes
                    <textarea rows={2} value={admissionForm.notes} onChange={(e) => updateAdmission({ notes: e.target.value })} />
                  </label>
                </div>
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
            <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>

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
                <DisplayField
                  label="N° facture"
                  value={activeInvoice?.invoice_number || ''}
                  hint={activeInvoice?.invoice_number ? undefined : FIELD_HINTS.invoiceNumber}
                />
                <DisplayField label="N° dossier patient" value={patientDossier} />
                <DisplayField label="Nom et prénom" value={patientDisplayName} />
                <label>
                  Date de facturation
                  {activeInvoice ? (
                    <ReadOnlyDisplay value={(activeInvoice.issued_at || activeInvoice.created_at || '').slice(0, 10)} />
                  ) : (
                    <input
                      required
                      type="date"
                      value={billingForm.billing_date}
                      onChange={(e) => updateBilling({ billing_date: e.target.value })}
                    />
                  )}
                </label>
              </div>
              <div className="reception-his-form-row">
                <label>
                  Service concerné
                  {activeInvoice ? (
                    <ReadOnlyDisplay value={activeInvoice.department || ''} />
                  ) : (
                    <select value={billingForm.department} onChange={(e) => updateBilling({ department: e.target.value })}>
                      {billingDepartments.map((d) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  )}
                </label>
              </div>
              {!activeInvoice && (
                <form className="reception-his-inline-create" onSubmit={handleCreateInvoice}>
                  <fieldset className="reception-his-nested-fieldset">
                    <legend>Demande de service enregistrée</legend>
                    <p className="clinical-hint">
                      Collez le N° de demande (DSR-…) pour l&apos;ajouter au tableau Produits / Services.
                    </p>
                    <div className="reception-his-search-inline">
                      <input
                        type="text"
                        value={billingServiceRequestId}
                        onChange={(e) => setBillingServiceRequestId(e.target.value)}
                        placeholder="Ex. DSR-001-000123"
                      />
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={loadServiceRequestIntoBilling}
                        disabled={loadingBillingServiceRequest || !billingServiceRequestId.trim()}
                      >
                        {loadingBillingServiceRequest ? 'Chargement…' : 'Ajouter à la facture'}
                      </button>
                    </div>
                  </fieldset>
                  <fieldset className="reception-his-nested-fieldset">
                    <legend>Service concerné / tarification</legend>
                    <p className="clinical-hint">
                      Sélectionnez le service ci-dessus, puis la spécialité ou l&apos;examen selon la fiche de tarifs AASMA.
                    </p>
                    {(billingForm.department === 'Consultation spécialisée'
                      || String(billingForm.department || '').startsWith('Consultation spécialisée')) && (
                      <div className="reception-his-specialty-picker">
                        {renderSpecialtyPicker('billing', { required: true })}
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addSpecializedConsultation}>
                          + Consultation spécialisée
                        </button>
                      </div>
                    )}
                    {(billingForm.department === 'Consultation urgences' || billingForm.department === 'Urgences') && (
                      <div className="reception-his-specialty-picker">
                        <label htmlFor="specialty-select-emergency">
                          Spécialité (tarif urgence)
                          <select
                            id="specialty-select-emergency"
                            value={admissionForm.specialty_code || selectedSpecialty}
                            onChange={(e) => syncSpecialtyCode(e.target.value)}
                          >
                            <option value="">Tarif général urgences…</option>
                            {specializedSpecialties.map((spec) => (
                              <option key={spec.code} value={spec.code}>
                                {spec.label} · {formatGNF(spec.emergency_price_gnf || 150000)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addEmergencyConsultation}>
                          + Consultation d&apos;urgences
                        </button>
                      </div>
                    )}
                    {billingForm.department === 'Consultation externe' && (
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => {
                          const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'outpatient_consultation');
                          addBillingLine({
                            charge_type: svc?.charge_type || 'consultation',
                            description: svc?.label || 'Consultation externe',
                            quantity: 1,
                            unit_price_gnf: svc?.price_gnf || 100000,
                          });
                        }}
                      >
                        + Consultation externe · {formatGNF((billingCatalog?.consultation_services || []).find((c) => c.code === 'outpatient_consultation')?.price_gnf || 100000)}
                      </button>
                    )}
                    {billingForm.department === 'Hospitalisation' && (
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => {
                          const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'hospitalization');
                          addBillingLine({
                            charge_type: svc?.charge_type || 'hospitalization',
                            description: svc?.label || 'Hospitalisation',
                            quantity: 1,
                            unit_price_gnf: svc?.price_gnf || 350000,
                          });
                        }}
                      >
                        + Hospitalisation · {formatGNF((billingCatalog?.consultation_services || []).find((c) => c.code === 'hospitalization')?.price_gnf || 350000)}
                      </button>
                    )}
                    {billingForm.department === 'Chirurgie' && surgicalActs.length > 0 && (
                      <div className="reception-his-service-options">
                        {surgicalActs.map((act) => (
                          <button
                            key={act.code}
                            type="button"
                            className="clinical-btn clinical-btn--secondary"
                            onClick={() => addBillingLine({
                              charge_type: 'procedure',
                              description: act.label,
                              quantity: 1,
                              unit_price_gnf: act.price_gnf || 0,
                            })}
                          >
                            + {act.label} · {formatGNF(act.price_gnf || 0)}
                          </button>
                        ))}
                      </div>
                    )}
                    {(billingForm.department === 'Imagerie médicale') && imagingExaminations.length > 0 && (
                      <div className="reception-his-specialty-picker">
                        <label>
                          Imagerie médicale — examen
                          <select value={selectedImaging} onChange={(e) => setSelectedImaging(e.target.value)}>
                            <option value="">Choisir un examen…</option>
                            {imagingExaminations.map((exam) => (
                              <option key={exam.code} value={exam.code}>{exam.label} · {formatGNF(exam.price_gnf)}</option>
                            ))}
                          </select>
                        </label>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addImagingExam}>
                          + Imagerie médicale
                        </button>
                      </div>
                    )}
                    {(billingForm.department === 'Soins infirmiers') && (
                      <div className="reception-his-service-options">
                        {servicePrestations.map((svc) => (
                          <button
                            key={svc.code}
                            type="button"
                            className="clinical-btn clinical-btn--secondary"
                            onClick={() => addBillingLine({
                              charge_type: 'procedure',
                              description: svc.label,
                              quantity: 1,
                              unit_price_gnf: svc.price_gnf || 0,
                            })}
                          >
                            + {svc.label} · {formatGNF(svc.price_gnf || 0)}
                          </button>
                        ))}
                      </div>
                    )}
                    {(billingForm.department === 'Laboratoire' || !['Consultation spécialisée', 'Consultation urgences', 'Urgences', 'Imagerie médicale', 'Soins infirmiers'].includes(billingForm.department)) && (
                      <>
                        <label>
                          Rechercher examen laboratoire
                          <input
                            type="search"
                            value={labSearchQ}
                            onChange={(e) => setLabSearchQ(e.target.value)}
                            placeholder="Nom ou code analyse…"
                          />
                        </label>
                        {filteredLabTests.length > 0 && (
                          <ul className="reception-his-lab-search-results">
                            {filteredLabTests.map((test) => (
                              <li key={test.code}>
                                <button
                                  type="button"
                                  onClick={() => addBillingLine({
                                    charge_type: 'laboratory',
                                    description: `${test.name} (${test.code})`,
                                    quantity: 1,
                                    unit_price_gnf: test.price_gnf || 0,
                                  })}
                                >
                                  {test.name} · {formatGNF(test.price_gnf || 0)}
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </>
                    )}
                  </fieldset>
                  <table className="reception-his-billing-lines">
                    <thead>
                      <tr>
                        <th>Produit / Service</th>
                        <th>Qté</th>
                        <th>Prix U</th>
                        <th>Total</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {billingLineItems.length === 0 ? (
                        <tr><td colSpan={5} className="reception-his-empty-row">Aucune prestation ajoutée.</td></tr>
                      ) : (
                        billingLineItems.map((line) => (
                          <tr key={line.id}>
                            <td>{line.description}</td>
                            <td>{line.quantity}</td>
                            <td>{formatGNF(line.unit_price_gnf)}</td>
                            <td>{formatGNF(Number(line.quantity || 1) * Number(line.unit_price_gnf || 0))}</td>
                            <td>
                              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removeBillingLine(line.id)}>Retirer</button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                  <div className="reception-his-form-row reception-his-form-row--3">
                    <label>
                      Montant total
                      <AmountDisplay amountGnf={billingSubtotal || null} />
                    </label>
                    <label>
                      Exemption (%)
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={billingForm.exemption_percent}
                        onChange={(e) => updateBilling({ exemption_percent: e.target.value })}
                      />
                    </label>
                    <label>
                      Montant exemption
                      <AmountDisplay amountGnf={draftExemptionAmount || null} />
                    </label>
                  </div>
                  <div className="reception-his-form-row reception-his-form-row--2">
                    <label>
                      Nouveau total
                      <AmountDisplay amountGnf={draftNetTotal || null} />
                    </label>
                  </div>
                  <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient || billingLineItems.length === 0}>
                    Créer facture
                  </button>
                </form>
              )}
              {activeInvoice && (activeInvoice.items || []).length > 0 && (
                <table className="reception-his-billing-lines">
                  <thead>
                    <tr>
                      <th>Produit / Service</th>
                      <th>Qté</th>
                      <th>Prix U</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(activeInvoice.items || []).map((item) => (
                      <tr key={item.id}>
                        <td>{item.description}</td>
                        <td>{item.quantity}</td>
                        <td>{formatGNF(item.unit_price_gnf)}</td>
                        <td>{formatGNF(item.amount_gnf)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </fieldset>

            <fieldset>
              <legend>Paiement</legend>
              {!activeInvoice && (
                <FormNotice>{INVOICE_PAYMENT_NOTICE}</FormNotice>
              )}
              <div className="reception-his-form-row reception-his-form-row--4">
                <label>
                  Montant total
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.subtotal : (billingSubtotal || null)} />
                </label>
                <label>
                  Exemption (%)
                  <ReadOnlyDisplay value={activeInvoice ? `${activeMeta?.exemptionPercent || 0}` : String(billingForm.exemption_percent || 0)} />
                </label>
                <label>
                  Montant exemption
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.exemptionAmount : (draftExemptionAmount || null)} />
                </label>
                <label>
                  Nouveau total
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.total : (draftNetTotal || null)} />
                </label>
              </div>
              <div className="reception-his-form-row reception-his-form-row--3">
                <label>
                  Montant reçu
                  <AmountDisplay amountGnf={activeInvoice ? (activeMeta?.paid ?? 0) : null} />
                </label>
                <label>
                  Reste à payer
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.remaining : null} />
                </label>
                {activeInvoice && draftPaymentTotal > 0 && (
                  <>
                    <label>
                      Total saisi (lignes)
                      <AmountDisplay amountGnf={draftPaymentTotal} />
                    </label>
                    <label>
                      Reste après saisie
                      <AmountDisplay amountGnf={draftRemainingAfterPay} />
                    </label>
                  </>
                )}
              </div>
              {activeInvoice ? (
                <form onSubmit={handlePayment}>
                  <p className="clinical-hint">Ajoutez une ou plusieurs lignes de paiement (Orange Money, Espèces, Virement, Assurance…).</p>
                  <table className="reception-his-billing-lines">
                    <thead>
                      <tr>
                        <th>Mode de paiement</th>
                        <th>Montant (GNF)</th>
                        <th>Référence</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {paymentLines.map((line) => (
                        <tr key={line.id}>
                          <td>
                            <select
                              value={line.payment_method}
                              onChange={(e) => updatePaymentLine(line.id, { payment_method: e.target.value })}
                            >
                              {PAYMENT_METHODS.map((m) => (
                                <option key={m.value} value={m.value}>{m.label}</option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              type="text"
                              inputMode="numeric"
                              pattern="[0-9]*"
                              value={line.amount_gnf}
                              onChange={(e) => updatePaymentLine(line.id, { amount_gnf: e.target.value.replace(/[^\d]/g, '') })}
                              placeholder="Montant"
                            />
                          </td>
                          <td>
                            <input
                              value={line.reference}
                              onChange={(e) => updatePaymentLine(line.id, { reference: e.target.value })}
                              placeholder="N° transaction…"
                            />
                          </td>
                          <td>
                            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removePaymentLine(line.id)}>
                              ×
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="pharmacy-his-actions">
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addPaymentLine}>
                      + Ligne de paiement
                    </button>
                    <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>
                      Enregistrer le(s) paiement(s)
                    </button>
                  </div>
                </form>
              ) : (
                <FormNotice>{INVOICE_PAYMENT_NOTICE}</FormNotice>
              )}
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
            <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
            <GeneratedIdBanner label="N° remboursement généré" value={lastRefund?.refund_number} />

            <form onSubmit={handleRefund}>
              <fieldset>
                <legend>Demande de remboursement</legend>
                <div className="reception-his-form-row reception-his-form-row--4">
                  <DisplayField
                    label="N° remboursement"
                    value={lastRefund?.refund_number || ''}
                    hint={lastRefund?.refund_number ? undefined : FIELD_HINTS.refundNumber}
                  />
                  <DisplayField label="N° dossier patient" value={patientDossier} />
                  <DisplayField label="Nom et prénom" value={patientDisplayName} />
                  <label>
                    Service payé
                    <input value={refundForm.service_paid_for} onChange={(e) => updateRefund({ service_paid_for: e.target.value })} />
                  </label>
                </div>
                <div className="reception-his-form-row reception-his-form-row--2">
                  <label>
                    Facture originale *
                    <ReadOnlyDisplay value={refundForm.invoice_id && activeInvoice ? (activeInvoice.invoice_number || '') : ''} />
                    {selectedPatient ? (
                      <>
                        <input
                          type="search"
                          placeholder="Rechercher N° facture…"
                          value={invoiceSearchQ}
                          onChange={(e) => setInvoiceSearchQ(e.target.value)}
                        />
                        <select
                          required
                          value={refundForm.invoice_id}
                          onChange={(e) => { updateRefund({ invoice_id: e.target.value }); selectInvoice(e.target.value); }}
                        >
                          <option value="">— Sélectionner —</option>
                          {refundInvoices.map((i) => (
                            <option key={i.id} value={i.id}>
                              {i.invoice_number} · payé {formatGNF(i.paid_amount_gnf || 0)}
                            </option>
                          ))}
                        </select>
                      </>
                    ) : null}
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
                    <AmountDisplay amountGnf={refundForm.invoice_id ? (activeInvoice?.paid_amount_gnf ?? 0) : null} />
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
                <div className="reception-his-form-row reception-his-form-row--2">
                  <label>
                    Bénéficiaire *
                    <input required value={refundForm.recipient_name} onChange={(e) => updateRefund({ recipient_name: e.target.value })} />
                  </label>
                  <label>
                    Tél. bénéficiaire *
                    <input required value={refundForm.recipient_phone} onChange={(e) => updateRefund({ recipient_phone: e.target.value })} />
                  </label>
                </div>
                {refundForm.reason === 'other' ? (
                  <label className="reception-his-notes-field">
                    Motif (préciser) *
                    <textarea
                      required
                      rows={2}
                      value={refundForm.reason_notes}
                      onChange={(e) => updateRefund({ reason_notes: e.target.value })}
                      placeholder="Saisir le motif du remboursement…"
                    />
                  </label>
                ) : (
                  <label className="reception-his-notes-field">
                    Notes
                    <textarea rows={2} value={refundForm.reason_notes} onChange={(e) => updateRefund({ reason_notes: e.target.value })} />
                  </label>
                )}
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

      {tab === 'service_requests' && (
        <section className="reception-his-panel">
          <PatientContextPanel />
          <div className="clinical-card reception-his-form-sheet">
            <h2>Demandes de service</h2>
            <div className="reception-his-search-inline reception-his-service-request-filters">
              <input
                type="search"
                placeholder="Rechercher une demande (service, n°…)"
                value={serviceRequestSearchQ}
                onChange={(e) => setServiceRequestSearchQ(e.target.value)}
              />
              <select value={serviceRequestStatusFilter} onChange={(e) => setServiceRequestStatusFilter(e.target.value)}>
                <option value="">Tous les statuts</option>
                {SERVICE_REQUEST_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={loadServiceRequests}>Actualiser</button>
            </div>

            <form className="reception-his-service-request-form" onSubmit={saveServiceRequest}>
              <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
              <div className="clinical-form-row">
                <label>
                  Catégorie
                  <select
                    value={serviceRequestForm.service_category}
                    onChange={(e) => {
                      const category = e.target.value;
                      setServiceRequestForm((p) => ({
                        ...p,
                        service_category: category,
                        service_name: '',
                        catalog_code: '',
                        charge_type: SERVICE_REQUEST_CHARGE_TYPES[category] || 'other',
                        unit_price_gnf: 0,
                      }));
                      setServiceRequestExamSearchQ('');
                    }}
                    disabled={!selectedPatient}
                  >
                    {SERVICE_REQUEST_CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Service / examen sélectionné
                  <ReadOnlyDisplay value={serviceRequestForm.service_name} />
                </label>
                <label>
                  Statut
                  <select
                    value={serviceRequestForm.status}
                    onChange={(e) => setServiceRequestForm((p) => ({ ...p, status: e.target.value }))}
                    disabled={!selectedPatient}
                  >
                    {SERVICE_REQUEST_STATUSES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              {serviceRequestForm.service_category === 'laboratory' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Tous les examens de laboratoire</legend>
                  <label>
                    Rechercher un examen
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Nom ou code analyse…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <ul className="reception-his-lab-search-results">
                    {filteredServiceRequestLabTests.map((test) => (
                      <li key={test.code}>
                        <button
                          type="button"
                          onClick={() => chooseServiceRequest('laboratory', `${test.name} (${test.code})`, {
                            catalog_code: test.code,
                            charge_type: 'laboratory',
                            unit_price_gnf: test.price_gnf || 0,
                          })}
                          disabled={!selectedPatient}
                        >
                          {test.name} ({test.code})
                          {test.category ? ` · ${test.category}` : ''}
                          {` · ${formatGNF(test.price_gnf || 0)}`}
                        </button>
                      </li>
                    ))}
                  </ul>
                  {filteredServiceRequestLabTests.length === 0 && (
                    <p className="clinical-hint">Aucun examen trouvé.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'imaging' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Tous les examens d&apos;imagerie</legend>
                  <label>
                    Rechercher un examen
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Nom examen imagerie…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <div className="reception-his-service-options">
                    {filteredServiceRequestImaging.map((exam) => (
                      <button
                        key={exam.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest('imaging', exam.label, {
                          catalog_code: exam.code,
                          charge_type: 'imaging',
                          unit_price_gnf: exam.price_gnf || 0,
                        })}
                        disabled={!selectedPatient}
                      >
                        {exam.label} · {formatGNF(exam.price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                  {filteredServiceRequestImaging.length === 0 && (
                    <p className="clinical-hint">Aucun examen d&apos;imagerie trouvé.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'consultation' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Spécialités (tarifs fiche AASMA)</legend>
                  <label>
                    Rechercher une spécialité
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Médecine, Chirurgie, Pédiatrie…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <div className="reception-his-service-options">
                    {filteredServiceRequestSpecialties.map((spec) => (
                      <button
                        key={spec.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest(
                          'consultation',
                          `Consultation spécialisée — ${spec.label}`,
                          {
                            catalog_code: spec.code,
                            charge_type: 'consultation',
                            unit_price_gnf: spec.price_gnf || 0,
                          }
                        )}
                        disabled={!selectedPatient}
                      >
                        {spec.label}
                        {' · spé. '}
                        {formatGNF(spec.price_gnf || 0)}
                        {' · urg. '}
                        {formatGNF(spec.emergency_price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                  {filteredServiceRequestSpecialties.length === 0 && (
                    <p className="clinical-hint">Aucune spécialité trouvée.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'surgery' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Actes chirurgicaux</legend>
                  <label>
                    Rechercher un acte
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Suture, césarienne, hernie…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <div className="reception-his-service-options">
                    {filteredSurgicalActs.map((act) => (
                      <button
                        key={act.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest('surgery', act.label, {
                          catalog_code: act.code,
                          charge_type: 'procedure',
                          unit_price_gnf: act.price_gnf || 0,
                        })}
                        disabled={!selectedPatient}
                      >
                        {act.label} · {formatGNF(act.price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                  {filteredSurgicalActs.length === 0 && (
                    <p className="clinical-hint">Aucun acte chirurgical trouvé.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'service' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Services / Prestations</legend>
                  <div className="reception-his-service-options">
                    {filteredServicePrestations.map((svc) => (
                      <button
                        key={svc.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest('service', svc.label, {
                          catalog_code: svc.code,
                          charge_type: 'procedure',
                          unit_price_gnf: svc.price_gnf || 0,
                        })}
                        disabled={!selectedPatient}
                      >
                        {svc.label} · {formatGNF(svc.price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                </fieldset>
              )}

              {['nursing', 'pharmacy', 'doctor', 'other'].includes(serviceRequestForm.service_category) && (
                <label>
                  Service / prestation
                  <input
                    value={serviceRequestForm.service_name}
                    onChange={(e) => setServiceRequestForm((p) => ({
                      ...p,
                      service_name: e.target.value,
                      charge_type: SERVICE_REQUEST_CHARGE_TYPES[p.service_category] || 'other',
                    }))}
                    disabled={!selectedPatient}
                    required
                  />
                </label>
              )}
              {serviceRequestForm.service_name ? (
                <p className="clinical-hint">
                  Sélection enregistrée : <strong>{serviceRequestForm.service_name}</strong>
                  {' · '}
                  {formatGNF(serviceRequestForm.unit_price_gnf || 0)}
                  {' — cliquez « Créer la demande » pour la conserver.'}
                </p>
              ) : null}
              <div className="reception-his-form-actions">
                <button type="submit" className="clinical-btn" disabled={!selectedPatient || loading || !serviceRequestForm.service_name.trim()}>
                  {editingServiceRequestId ? 'Mettre à jour la demande' : 'Créer la demande'}
                </button>
                {editingServiceRequestId && (
                  <button type="button" className="clinical-btn clinical-btn--secondary" onClick={resetServiceRequestForm}>Annuler</button>
                )}
                {lastCreatedServiceRequest?.request_number && (
                  <button
                    type="button"
                    className="clinical-btn clinical-btn--secondary"
                    onClick={() => applyServiceRequestToBilling(lastCreatedServiceRequest)}
                  >
                    Facturer {lastCreatedServiceRequest.request_number}
                  </button>
                )}
              </div>
            </form>

            {loadingServiceRequests ? (
              <FormNotice>Chargement des demandes…</FormNotice>
            ) : serviceRequests.length === 0 ? (
              <FormNotice>Aucune demande de service{selectedPatient ? ' pour ce patient' : ''}.</FormNotice>
            ) : (
              <table className="reception-his-billing-lines">
                <thead>
                  <tr>
                    <th>N° demande</th>
                    <th>Patient</th>
                    <th>Catégorie</th>
                    <th>Service</th>
                    <th>Statut</th>
                    <th>Créée le</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {serviceRequests.map((row) => (
                    <tr key={row.id}>
                      <td>{row.request_number}</td>
                      <td>{row.patient_name || row.patient_id}</td>
                      <td>{serviceRequestCategoryLabel(row.service_category)}</td>
                      <td>{row.service_name}</td>
                      <td>{serviceRequestStatusLabel(row.status)}</td>
                      <td>{formatDateTime(row.created_at)}</td>
                      <td>
                        <div className="reception-his-refund-actions">
                          <button type="button" className="clinical-btn" onClick={() => applyServiceRequestToBilling(row)}>Facturer</button>
                          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => startEditServiceRequest(row)}>Modifier</button>
                          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => deleteServiceRequest(row.id)}>Supprimer</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      )}

      {registeredPatient && registrationPrintForm && (
        <div className="reception-his-registration-print" ref={regPrintRef}>
          <PatientRegistrationPrint
            patient={{
              ...registeredPatient,
              emergency_relationship: resolveRelationship(registrationPrintForm),
            }}
            form={registrationPrintForm}
            printedBy={(user?.full_name || user?.email || '').toUpperCase()}
          />
        </div>
      )}
    </div>
  );
}
