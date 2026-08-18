function patientFullName(patient) {
  return patient?.full_name
    || [patient?.last_name, patient?.first_name].filter(Boolean).join(' ')
    || 'Identité non renseignée';
}

function patientAge(patient) {
  const explicitAge = patient?.age_years ?? patient?.age;
  if (explicitAge !== null && explicitAge !== undefined && explicitAge !== '') {
    return `${explicitAge} ans`;
  }
  if (!patient?.date_of_birth) return 'Non renseigné';
  const birth = new Date(patient.date_of_birth);
  if (Number.isNaN(birth.getTime())) return 'Non renseigné';
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today < new Date(today.getFullYear(), birth.getMonth(), birth.getDate())) age -= 1;
  return `${Math.max(0, age)} ans`;
}

function patientGender(patient) {
  const gender = patient?.gender || patient?.sex;
  if (gender === 'F') return 'Féminin';
  if (gender === 'M') return 'Masculin';
  return gender || 'Non renseigné';
}

export default function PatientSafetyStrip({ patient, onClose, contextLabel = 'Dossier patient ouvert' }) {
  if (!patient) return null;
  return (
    <section className="patient-safety-strip" aria-label={contextLabel} data-testid="patient-safety-strip">
      <span className="patient-safety-strip__marker" aria-hidden="true">P</span>
      <div className="patient-safety-strip__identity">
        <span className="patient-safety-strip__eyebrow">{contextLabel}</span>
        <strong>{patientFullName(patient)}</strong>
      </div>
      <dl className="patient-safety-strip__facts">
        <div><dt>N° dossier</dt><dd translate="no">{patient.patient_number || 'Non attribué'}</dd></div>
        <div><dt>Âge</dt><dd>{patientAge(patient)}</dd></div>
        <div><dt>Sexe</dt><dd>{patientGender(patient)}</dd></div>
        <div><dt>Téléphone</dt><dd>{patient.phone || 'Non renseigné'}</dd></div>
      </dl>
      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={onClose}>
        Fermer le dossier
      </button>
    </section>
  );
}
