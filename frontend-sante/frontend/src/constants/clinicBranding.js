/** Official clinic branding — printable documents only. */
export const CLINIC_COUNTRY = 'République de Guinée';
export const CLINIC_MOTTO = 'Travail - Justice - Solidarité';
export const CLINIC_MINISTRY = "Ministère de la Santé et de l'Hygiène Publique";
export const CLINIC_PRINT_NAME = 'CHFMP - Polyclinique AASMA';
export const CLINIC_PRINT_NAME_FULL = 'CHFMP - Polyclinique AASMA';
export const CLINIC_ADDRESS = 'Kobaya chinoiya, sur la colline entre la Pharmacie Dara et les écoles MOLASY';
export const CLINIC_PHONE = '613 04 94 48';
export const CLINIC_EMAIL = 'contactpolycliniqueaasma@gmail.com';
export const CLINIC_LOGO_URL = '/branding/aasma-clinic-logo.png';
export const SPECIALTY_OTHER_CODE = '__other__';

export const PAYER_TYPE_OPTIONS = [
  { value: 'patient', label: 'Patient' },
  { value: 'insurance', label: 'Assurance' },
  { value: 'company', label: 'Entreprise' },
  { value: 'employee', label: 'Employé' },
  { value: 'dg', label: 'DG' },
  { value: 'mshp', label: 'MSHP' },
];

export const payerTypeLabel = (type) =>
  PAYER_TYPE_OPTIONS.find((o) => o.value === type)?.label || type || '—';
