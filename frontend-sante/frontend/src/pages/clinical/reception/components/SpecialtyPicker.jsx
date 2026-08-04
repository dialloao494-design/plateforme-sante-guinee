import { SPECIALTY_OTHER_CODE } from '../../../../constants/clinicBranding.js';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';

export default function SpecialtyPicker({
  idSuffix = '',
  required,
  admissionForm,
  selectedSpecialty,
  specializedSpecialties,
  onCodeChange,
  onOtherChange,
}) {
  return (
    <div className="reception-his-specialty-picker">
      <label htmlFor={`specialty-select-${idSuffix}`}>
        Spécialité (consultation spécialisée) *
        <select
          id={`specialty-select-${idSuffix}`}
          required={required}
          value={admissionForm.specialty_code || selectedSpecialty}
          onChange={(e) => onCodeChange(e.target.value)}
        >
          <option value="">Choisir une spécialité…</option>
          {specializedSpecialties.map((spec) => (
            <option key={spec.code} value={spec.code}>
              {spec.label} · {formatGNF(spec.price_gnf || 250000)}
            </option>
          ))}
          <option value={SPECIALTY_OTHER_CODE}>Autre</option>
        </select>
      </label>
      {(admissionForm.specialty_code === SPECIALTY_OTHER_CODE || selectedSpecialty === SPECIALTY_OTHER_CODE) && (
        <label>
          Préciser la spécialité
          <input
            required
            value={admissionForm.specialty_other || ''}
            onChange={(e) => onOtherChange(e.target.value)}
            placeholder="Saisir la spécialité…"
          />
        </label>
      )}
    </div>
  );
}
