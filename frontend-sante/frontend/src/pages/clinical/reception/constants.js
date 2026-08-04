export const TABS = [
  { id: 'dashboard', label: 'Tableau de bord', shortcut: '1' },
  { id: 'register', label: 'Enregistrement', shortcut: '2' },
  { id: 'admission', label: 'Admission', shortcut: '3' },
  { id: 'billing', label: 'Facturation', shortcut: '4' },
  { id: 'refund', label: 'Remboursement', shortcut: '5' },
  { id: 'service_requests', label: 'Demandes de service', shortcut: '6' },
];

export const DEFAULT_ADMISSION_SERVICES = [
  'Consultation urgences',
  'Consultation spécialisée',
  'Consultation externe',
  'Laboratoire',
  'Pharmacie',
  'Hospitalisation',
  'Imagerie médicale',
];

export const DEFAULT_BILLING_DEPARTMENTS = [
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

export const ADMISSION_TYPES = [
  { value: 'emergency', label: 'Urgence' },
  { value: 'outpatient', label: 'Consultation externe' },
  { value: 'specialized_consultation', label: 'Consultation spécialisée' },
  { value: 'hospitalization', label: 'Hospitalisation' },
];

export const RELATIONSHIP_OPTIONS = [
  { value: 'Père', label: 'Père' },
  { value: 'Mère', label: 'Mère' },
  { value: 'Fils', label: 'Fils' },
  { value: 'Fille', label: 'Fille' },
  { value: 'Autre', label: 'Autre' },
];

export const ADMISSION_CONFIRMATIONS = [
  { value: 'confirmed', label: 'Confirmée' },
  { value: 'pending', label: 'En attente' },
];

export const PAYMENT_METHODS = [
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'cash', label: 'Espèces' },
  { value: 'bank_transfer', label: 'Virement bancaire' },
  { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance', label: 'Assurance' },
];

export const REFUND_METHODS = [
  { value: 'cash', label: 'Espèces' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'bank_transfer', label: 'Virement bancaire' },
  { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance_adjustment', label: 'Assurance' },
];

export const REFUND_REASONS = [
  { value: 'deceased', label: 'Décès' },
  { value: 'service_cancelled', label: 'Service annulé' },
  { value: 'overpayment', label: 'Trop-perçu' },
  { value: 'other', label: 'Autre' },
];

export const todayStr = new Date().toISOString().slice(0, 10);

export const FIELD_HINTS = {
  patientId: 'Le numéro dossier sera généré automatiquement après enregistrement.',
  admissionNumber: 'Généré automatiquement après création de l\'admission.',
  invoiceNumber: 'Généré automatiquement après création de la facture.',
  refundNumber: 'Généré automatiquement après soumission.',
  age: 'Calculé automatiquement à partir de la date de naissance.',
};

export const PATIENT_REQUIRED_NOTICE = 'Veuillez rechercher et sélectionner un patient.';
export const INVOICE_PAYMENT_NOTICE = 'Créez ou sélectionnez une facture pour afficher le récapitulatif de paiement.';

export const EMPTY_REG = {
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

export const EMPTY_ADMISSION = {
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

export const EMPTY_BILLING = {
  billing_date: todayStr,
  department: 'Consultation externe',
  exemption_percent: '0',
  exemption_reason: '',
};

export const newPaymentLineId = () => `pay-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
export const emptyPaymentLine = () => ({ id: newPaymentLineId(), amount_gnf: '', payment_method: 'orange_money', reference: '' });

export const EMPTY_REFUND = {
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

export const SERVICE_REQUEST_CATEGORIES = [
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

export const SERVICE_REQUEST_STATUSES = [
  { value: 'pending', label: 'En attente' },
  { value: 'approved', label: 'Approuvée' },
  { value: 'completed', label: 'Terminée' },
  { value: 'cancelled', label: 'Annulée' },
];

export const SERVICE_REQUEST_CHARGE_TYPES = {
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

export const SERVICE_REQUEST_DEPARTMENTS = {
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

export const EMPTY_SERVICE_REQUEST = {
  service_category: 'laboratory',
  service_name: '',
  catalog_code: '',
  charge_type: 'laboratory',
  unit_price_gnf: 0,
  status: 'pending',
};

export const DEFAULT_SERVICE_PRESTATIONS = [
  { code: 'emergency_care_with_serum', label: "Soins d'urgence avec sérum", price_gnf: 500000 },
  { code: 'injection', label: 'Injection', price_gnf: 25000 },
  { code: 'small_dressing', label: 'Petit pansement', price_gnf: 30000 },
  { code: 'large_dressing', label: 'Grand pansement', price_gnf: 80000 },
  { code: 'pediatric_emergency_care', label: "Soins d'urgence pédiatrie", price_gnf: 250000 },
  { code: 'medical_transport_ambulance', label: 'Transport médical / Ambulance', price_gnf: 0 },
];

export const DASHBOARD_BUCKET_TITLES = {
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
