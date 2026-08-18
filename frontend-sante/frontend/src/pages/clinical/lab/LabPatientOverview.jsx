import { formatClinicalDate } from '../../../utils/clinicalPresentation.js';

const qrImageUrl = (token) =>
  token ? `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(token)}` : '';

function calculateAge(patient) {
  if (patient?.age != null && patient.age !== '') return String(patient.age);
  if (!patient?.date_of_birth) return '';

  const birthDate = new Date(patient.date_of_birth);
  if (Number.isNaN(birthDate.getTime())) return '';

  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDifference = today.getMonth() - birthDate.getMonth();
  if (monthDifference < 0 || (monthDifference === 0 && today.getDate() < birthDate.getDate())) age -= 1;
  return age >= 0 ? String(age) : '';
}

function genderLabel(gender) {
  if (gender === 'F') return 'Féminin';
  if (gender === 'M') return 'Masculin';
  return gender || '';
}

export function ReadOnlyDisplay({ value }) {
  return (
    <div
      className={`reception-his-auto-display${value ? ' reception-his-auto-display--filled' : ' reception-his-auto-display--empty'}`}
    >
      {value || '—'}
    </div>
  );
}

function DisplayField({ label, value, identifier = false }) {
  return (
    <div className="lab-his-patient-field">
      <span>{label}</span>
      <div translate={identifier ? 'no' : undefined}>
        <ReadOnlyDisplay value={value} />
      </div>
    </div>
  );
}

export default function LabPatientOverview({ patient, onChangePatient }) {
  return (
    <section
      className="lab-his-workflow-card lab-his-workflow-card--patient reception-his-patient-context reception-his-patient-context--active"
      data-testid="lab-patient-overview"
      aria-labelledby="lab-patient-overview-title"
    >
      <h3 id="lab-patient-overview-title">Informations patient</h3>
      <div className="reception-his-form-row reception-his-form-row--4">
        <DisplayField label="N° dossier" value={patient.patient_number || String(patient.id)} identifier />
        <DisplayField label="Nom" value={patient.last_name} />
        <DisplayField label="Prénom" value={patient.first_name} />
        <DisplayField label="Date de naissance" value={formatClinicalDate(patient.date_of_birth, '')} />
      </div>
      <div className="reception-his-form-row reception-his-form-row--4">
        <DisplayField label="Âge" value={calculateAge(patient)} />
        <DisplayField label="Sexe" value={genderLabel(patient.gender)} />
        <DisplayField label="Profession" value={patient.profession} />
        <DisplayField label="Téléphone" value={patient.phone} />
      </div>
      <div className="reception-his-form-row reception-his-form-row--4">
        <DisplayField label="Adresse" value={patient.address || patient.quartier} />
        <DisplayField label="Ville" value={patient.city} />
        <DisplayField label="Région" value={patient.region} />
        <DisplayField label="Pays" value={patient.country} />
      </div>
      {patient.qr_token && (
        <div className="reception-his-qr-block">
          <img src={qrImageUrl(patient.qr_token)} alt="QR patient" width={120} height={120} />
          <DisplayField label="Code QR" value={patient.qr_token} identifier />
        </div>
      )}
      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={onChangePatient}>
        Changer de patient
      </button>
    </section>
  );
}
