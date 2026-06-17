/** Human-readable role labels for UI. */

const ROLE_LABELS = {
  patient: 'Patient',
  doctor: 'Médecin',
  admin: 'Admin clinique',
  clinic_admin: 'Admin clinique',
  platform_owner: 'Propriétaire plateforme',
  platform_admin: 'Admin plateforme',
  receptionist: 'Réception',
  cashier: 'Caisse',
  lab_technician: 'Laboratoire',
  pharmacist: 'Pharmacie',
};

export function getRoleLabel(role) {
  const r = String(role || '').toLowerCase();
  return ROLE_LABELS[r] || r || 'Utilisateur';
}

export default ROLE_LABELS;
