export const EMPTY_NURSE_ASSESSMENT = {
  temperature_c: '', bp_systolic: '', bp_diastolic: '', heart_rate: '', respiratory_rate: '',
  height_cm: '', weight_kg: '', vitals_observations: '', reason_for_consultation: '',
  history_of_present_illness: '', medical_history: '', surgical_history: '', gynecological_history: '',
  allergies: '', current_treatments: '', hospitalized_daily_vitals: '', prescription: '', nurse_notes: '',
};

export function calculateBmi(weightKg, heightCm) {
  const weight = Number(weightKg);
  const height = Number(heightCm);
  if (!weight || !height || height <= 0) return '';
  return (weight / ((height / 100) ** 2)).toFixed(1);
}
