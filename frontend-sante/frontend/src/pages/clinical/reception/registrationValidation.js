const FIELD_LABELS = {
  registration_date: 'Date d’inscription', last_name: 'Nom', first_name: 'Prénom',
  gender: 'Sexe', date_of_birth: 'Date complète', birth_year: 'Année de naissance',
  age_value: 'Âge déclaré', age_unit: 'Unité de l’âge', phone: 'Téléphone principal',
  address: 'Adresse', emergency_full_name: 'Nom du contact',
  emergency_relationship: 'Relation avec le contact',
  emergency_relationship_other: 'Précision de la relation',
  emergency_phone: 'Téléphone du contact', email: 'Email',
};

export function revealInvalidRegistrationField(field, setError) {
  if (field.form?.querySelector(':invalid') !== field) return;
  const collapsedSection = field.closest('details:not([open])');
  if (collapsedSection) collapsedSection.open = true;
  const label = FIELD_LABELS[field.name] || 'Champ obligatoire';
  setError(`Enregistrement non envoyé : vérifiez le champ « ${label} » indiqué dans le formulaire.`);
  window.requestAnimationFrame(() => {
    field.scrollIntoView({ behavior: 'smooth', block: 'center' });
    field.focus({ preventScroll: true });
  });
}
