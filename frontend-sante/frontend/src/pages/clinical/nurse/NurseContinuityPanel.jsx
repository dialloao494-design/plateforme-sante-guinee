import { TextAreaField } from './NurseFormPrimitives.jsx';

export default function NurseContinuityPanel({ form, onChange }) {
  return (
    <fieldset className="nurse-continuity-block">
      <legend>3 · Soins, sécurité et transmission</legend>
      <div className="nurse-continuity-grid">
        <TextAreaField label="Plan de soins et tâches à réaliser" rows={3} value={form.care_plan} onChange={(event) => onChange({ care_plan: event.target.value })} />
        <TextAreaField label="Administration des médicaments (heure, dose, voie, résultat)" rows={3} value={form.medication_administration} onChange={(event) => onChange({ medication_administration: event.target.value })} />
        <TextAreaField label="Prélèvements (type, heure, acheminement)" rows={3} value={form.specimen_collection} onChange={(event) => onChange({ specimen_collection: event.target.value })} />
        <TextAreaField label="Plaie / pansement (site, dimensions, aspect, soin)" rows={3} value={form.wound_assessment} onChange={(event) => onChange({ wound_assessment: event.target.value })} />
        <TextAreaField label="Sécurité (chute, escarre, allergie, dispositif)" rows={3} value={form.safety_checklist} onChange={(event) => onChange({ safety_checklist: event.target.value })} />
        <TextAreaField label="Transmission SBAR (situation, contexte, évaluation, recommandation)" rows={4} value={form.handover_sbar} onChange={(event) => onChange({ handover_sbar: event.target.value })} />
      </div>
    </fieldset>
  );
}
