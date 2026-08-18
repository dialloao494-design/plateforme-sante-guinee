import { patientFullName } from '../utils.js';

function patientAge(patient) {
  if (patient?.age_years !== null && patient?.age_years !== undefined && patient?.age_years !== '') {
    return `${patient.age_years} ans`;
  }
  if (!patient?.date_of_birth) return 'Âge non renseigné';
  const birth = new Date(patient.date_of_birth);
  if (Number.isNaN(birth.getTime())) return 'Âge non renseigné';
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today < new Date(today.getFullYear(), birth.getMonth(), birth.getDate())) age -= 1;
  return `${Math.max(0, age)} ans`;
}

export default function PatientSafetyStrip({ patient, onClose }) {
  if (!patient) return null;
  return (
    <section className="patient-safety-strip" aria-label="Dossier patient ouvert">
      <span className="patient-safety-strip__marker" aria-hidden="true">P</span>
      <div className="patient-safety-strip__identity">
        <span className="patient-safety-strip__eyebrow">Dossier patient ouvert</span>
        <strong>{patientFullName(patient)}</strong>
      </div>
      <dl className="patient-safety-strip__facts">
        <div><dt>N° dossier</dt><dd translate="no">{patient.patient_number || 'Non attribué'}</dd></div>
        <div><dt>Âge</dt><dd>{patientAge(patient)}</dd></div>
        <div><dt>Sexe</dt><dd>{patient.gender || 'Non renseigné'}</dd></div>
        <div><dt>Téléphone</dt><dd>{patient.phone || 'Non renseigné'}</dd></div>
      </dl>
      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={onClose}>
        Fermer le dossier
      </button>
    </section>
  );
}
