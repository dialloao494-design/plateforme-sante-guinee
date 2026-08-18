export function readClinicalPatientId(searchParams) {
  return searchParams.get('patient') || '';
}

export function updateClinicalPatientId(searchParams, patientId) {
  const next = new URLSearchParams(searchParams);
  if (patientId) next.set('patient', String(patientId));
  else next.delete('patient');
  return next;
}
