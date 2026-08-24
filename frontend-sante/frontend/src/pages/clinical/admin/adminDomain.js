export const MODULE_OPTIONS = [
  ['reception', 'Réception'], ['billing', 'Facturation'], ['consultation', 'Consultations'],
  ['laboratory', 'Laboratoire'], ['pharmacy', 'Pharmacie'], ['hospitalization', 'Hospitalisation'],
  ['nursing', 'Soins infirmiers'], ['pev', 'PEV'], ['nutrition', 'Nutrition'],
];

export const PAYMENT_OPTIONS = [
  ['cash', 'Espèces'], ['orange_money', 'Orange Money'], ['mobile_money', 'Autre mobile money'],
  ['transfer', 'Virement'], ['insurance', 'Assurance'],
];

export const ROLE_LABELS = {
  receptionist: 'Réceptionniste', cashier: 'Caissier', doctor: 'Médecin',
  lab_technician: 'Laborantin', pharmacist: 'Pharmacien', nutritionist: 'Nutritionniste',
  pev_agent: 'Agent PEV', nurse: 'Infirmier(ère)', midwife: 'Sage-femme',
  clinic_admin: 'Administrateur clinique', admin: 'Administrateur clinique',
};

export function buildAttentionItems(onboarding, activity) {
  const items = [];
  for (const check of onboarding?.checklist || []) {
    if (!check.complete) items.push({ key: check.key, label: check.label, detail: check.detail, target: check.target });
  }
  if ((activity?.pendingCharges || 0) > 0) {
    items.push({ key: 'unpaid', label: `${activity.pendingCharges} facture(s) à encaisser`, detail: 'Ouvrir la facturation et traiter les soldes en attente.', href: '/clinical/billing' });
  }
  return items;
}
