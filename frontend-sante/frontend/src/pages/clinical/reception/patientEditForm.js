import { EMPTY_REG } from './constants.js';

const parseJson = (value) => {
  try { return typeof value === 'string' ? JSON.parse(value) : (value || {}); }
  catch { return {}; }
};

export function patientToRegistrationForm(patient) {
  const emergency = parseJson(patient.emergency_contact_json);
  const payer = parseJson(patient.payer_json);
  const relationship = emergency.relationship || '';
  const known = ['Père', 'Mère', 'Fils', 'Fille'].includes(relationship);
  return {
    ...EMPTY_REG,
    registration_date: patient.registration_date || patient.created_at?.slice?.(0, 10) || EMPTY_REG.registration_date,
    first_name: patient.first_name || '', last_name: patient.last_name || '', gender: patient.gender || 'F',
    date_of_birth: patient.date_of_birth || '',
    date_of_birth_precision: patient.date_of_birth_precision || (patient.date_of_birth ? 'full' : 'unknown'),
    birth_year: patient.date_of_birth_precision === 'year' ? String(patient.date_of_birth || '').slice(0, 4) : '',
    age_years: String(patient.age ?? ''), age_value: String(patient.age_value ?? patient.age ?? ''), age_unit: patient.age_unit || 'years',
    is_newborn: Boolean(patient.is_newborn), phone: patient.phone || '', phone_secondary: patient.phone_secondary || '',
    email: patient.email || '', address: patient.address || '', commune: patient.commune || '', city: patient.city || '',
    region: patient.region || '', country: patient.country || 'Guinée', nationality: patient.nationality || '',
    marital_status: patient.marital_status || '', mother_first_name: patient.mother_first_name || '',
    mother_last_name: patient.mother_last_name || '', profession: patient.profession || '',
    preferred_language: patient.preferred_language || '', photo_url: patient.photo_url || '',
    emergency_same_address: Boolean(emergency.same_address_as_patient), emergency_full_name: emergency.full_name || '',
    emergency_relationship: known ? relationship : relationship ? 'Autre' : '', emergency_relationship_other: known ? '' : relationship,
    emergency_phone: emergency.phone || '', emergency_address: emergency.address || '', emergency_commune: emergency.commune || '',
    emergency_region: emergency.region || '', emergency_country: emergency.country || 'Guinée',
    payer_type: payer.payer_type || 'patient', insurance_company: payer.insurance_company || '',
    insurance_number: payer.insurance_number || '', company_name: payer.company_name || '', payer_notes: payer.notes || '',
  };
}
