import { PATIENT_REQUIRED_NOTICE } from '../constants.js';
import { genderLabel, patientAge } from '../utils.js';
import { FormNotice } from './FormPrimitives.jsx';

export default function PatientContextPanel({ selectedPatient, patientPayerLabel }) {
  return (
    <div className={`clinical-card reception-his-patient-context${selectedPatient ? ' reception-his-patient-context--active' : ''}`}>
      <h3>Patient sélectionné</h3>
      <div className="reception-his-patient-context-grid">
        <div><strong>{selectedPatient?._sync_status === 'queued' ? 'ID local' : 'N° dossier'}</strong><span className={(selectedPatient?.patient_number || selectedPatient?.id) ? 'reception-his-value-filled' : ''}>{selectedPatient?.patient_number || (selectedPatient?._sync_status === 'queued' ? selectedPatient.id : '')}</span></div>
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
}
