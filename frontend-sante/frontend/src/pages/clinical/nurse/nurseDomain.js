export const EMPTY_NURSE_ASSESSMENT = {
  temperature_c: '', bp_systolic: '', bp_diastolic: '', heart_rate: '', respiratory_rate: '',
  oxygen_saturation: '', pain_score: '', height_cm: '', weight_kg: '',
  arm_circumference_cm: '', head_circumference_cm: '', consciousness_level: 'alert',
  escalation_level: 'routine', vitals_observations: '', reason_for_consultation: '',
  history_of_present_illness: '', medical_history: '', surgical_history: '', gynecological_history: '',
  allergies: '', current_treatments: '', hospitalized_daily_vitals: '', prescription: '', nurse_notes: '',
  care_plan: '', handover_sbar: '', medication_administration: '', specimen_collection: '',
  wound_assessment: '', safety_checklist: '',
};

export function calculateBmi(weightKg, heightCm) {
  const weight = Number(weightKg);
  const height = Number(heightCm);
  if (!weight || !height || height <= 0) return '';
  return (weight / ((height / 100) ** 2)).toFixed(1);
}

export function vitalAlerts(form) {
  const alerts = [];
  const temperature = Number(form.temperature_c);
  const systolic = Number(form.bp_systolic);
  const saturation = Number(form.oxygen_saturation);
  const pulse = Number(form.heart_rate);
  const respiration = Number(form.respiratory_rate);
  const pain = Number(form.pain_score);
  if (temperature && (temperature < 35 || temperature >= 39)) alerts.push('Température critique');
  if (systolic && (systolic < 90 || systolic >= 180)) alerts.push('Tension systolique critique');
  if (saturation && saturation < 92) alerts.push('Saturation basse');
  if (pulse && (pulse < 50 || pulse > 120)) alerts.push('Pouls anormal');
  if (respiration && (respiration < 10 || respiration > 24)) alerts.push('Fréquence respiratoire anormale');
  if (pain >= 7) alerts.push('Douleur sévère');
  return alerts;
}

export function nursingCompletion(form) {
  const vitals = ['temperature_c', 'bp_systolic', 'bp_diastolic', 'heart_rate', 'respiratory_rate']
    .filter((key) => String(form[key] || '').trim()).length;
  return {
    vitalsComplete: vitals === 5,
    contextComplete: Boolean(String(form.reason_for_consultation || '').trim()),
    continuityComplete: Boolean(String(form.nurse_notes || form.handover_sbar || '').trim()),
  };
}
