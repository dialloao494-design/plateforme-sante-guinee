import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

import { readClinicalPatientId, updateClinicalPatientId } from '../utils/clinicalPatientRoute.js';

export function useClinicalPatientRoute() {
  const [searchParams, setSearchParams] = useSearchParams();
  const patientId = readClinicalPatientId(searchParams);

  const setPatientId = useCallback((nextPatientId, options = { replace: true }) => {
    setSearchParams(
      (current) => updateClinicalPatientId(current, nextPatientId),
      options,
    );
  }, [setSearchParams]);

  return { patientId, setPatientId };
}
