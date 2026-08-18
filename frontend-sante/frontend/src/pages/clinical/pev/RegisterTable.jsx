import { formatClinicalDate } from '../../../utils/clinicalPresentation.js';
import { INJECTION_SITE_LABELS, STRATEGY_LABELS } from './pevPresentation.js';
const GENDER_LABELS = { M: 'M', F: 'F', male: 'M', female: 'F', other: '—' };

export default function RegisterTable({ rows, title }) {
  if (!rows?.length) {
    return <section className="clinical-card"><h2>{title}</h2><p>Aucune vaccination enregistrée pour cette période.</p></section>;
  }
  return (
    <section className="clinical-card pev-register-card">
      <h2>{title}</h2>
      <div className="pev-register-scroll">
        <table className="clinical-table pev-register-table">
          <thead><tr>
            <th>N°</th><th>Date</th><th>Nom enfant</th><th>Sexe</th><th>Date naiss.</th><th>Âge</th>
            <th>Mère / tuteur</th><th>Quartier</th><th>Vaccin</th><th>Dose</th><th>Lot</th><th>Péremption</th>
            <th>Site</th><th>Stratégie</th><th>Vaccinateur</th><th>Proch. RDV</th><th>Observations</th>
          </tr></thead>
          <tbody>{rows.map(({ line_number: lineNumber, patient, record }) => (
            <tr key={record.id}>
              <td>{lineNumber}</td><td>{formatClinicalDate(record.administered_at)}</td>
              <td>{patient.first_name} {patient.last_name}</td><td>{GENDER_LABELS[patient.gender] || patient.gender || '—'}</td>
              <td>{formatClinicalDate(patient.date_of_birth)}</td>
              <td>{record.age_at_vaccination_months != null ? `${record.age_at_vaccination_months} mois` : patient.age_display || '—'}</td>
              <td>{patient.mother_or_guardian || '—'}</td><td>{patient.address || '—'}</td><td>{record.vaccine_name}</td>
              <td>{record.dose_label || record.dose_number || '—'}</td><td>{record.batch_number || '—'}</td>
              <td>{formatClinicalDate(record.vaccine_expiry_date)}</td>
              <td>{INJECTION_SITE_LABELS[record.injection_site] || record.injection_site || '—'}</td>
              <td>{STRATEGY_LABELS[record.vaccination_strategy] || record.vaccination_strategy || 'Routine'}</td>
              <td>{record.vaccinator_name || '—'}</td><td>{formatClinicalDate(record.next_appointment_date)}</td>
              <td>{record.notes || record.aefi_notes || '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </section>
  );
}
