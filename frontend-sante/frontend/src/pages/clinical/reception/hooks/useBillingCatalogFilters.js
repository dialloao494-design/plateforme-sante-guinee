import { useMemo } from 'react';
import { DEFAULT_ADMISSION_SERVICES, DEFAULT_BILLING_DEPARTMENTS, DEFAULT_SERVICE_PRESTATIONS } from '../constants.js';

const EMPTY_ARRAY = [];

export function useBillingCatalogFilters(billingCatalog, {
  labSearchQ = '',
  admissionLabSearchQ = '',
  serviceRequestExamSearchQ = '',
} = {}) {
  const specializedSpecialties = useMemo(
    () => billingCatalog?.specialized_specialties ?? EMPTY_ARRAY,
    [billingCatalog?.specialized_specialties]
  );

  const imagingExaminations = useMemo(
    () => billingCatalog?.imaging_examinations ?? EMPTY_ARRAY,
    [billingCatalog?.imaging_examinations]
  );

  const surgicalActs = useMemo(
    () => billingCatalog?.surgical_acts ?? EMPTY_ARRAY,
    [billingCatalog?.surgical_acts]
  );

  const admissionServices = useMemo(
    () => billingCatalog?.admission_services?.map((s) => s.label) ?? DEFAULT_ADMISSION_SERVICES,
    [billingCatalog?.admission_services]
  );

  const billingDepartments = useMemo(
    () => billingCatalog?.billing_departments ?? DEFAULT_BILLING_DEPARTMENTS,
    [billingCatalog?.billing_departments]
  );

  const servicePrestations = useMemo(
    () => billingCatalog?.service_prestations ?? DEFAULT_SERVICE_PRESTATIONS,
    [billingCatalog?.service_prestations]
  );

  const filteredAdmissionLabTests = useMemo(() => {
    const tests = billingCatalog?.lab_tests ?? EMPTY_ARRAY;
    const q = admissionLabSearchQ.trim().toLowerCase();
    if (!q) return EMPTY_ARRAY;
    return tests.filter((t) => `${t.name} ${t.code}`.toLowerCase().includes(q)).slice(0, 8);
  }, [billingCatalog?.lab_tests, admissionLabSearchQ]);

  const filteredLabTests = useMemo(() => {
    const tests = billingCatalog?.lab_tests ?? EMPTY_ARRAY;
    const q = labSearchQ.trim().toLowerCase();
    if (!q) return tests;
    return tests.filter(
      (t) => String(t.name || '').toLowerCase().includes(q) || String(t.code || '').toLowerCase().includes(q)
    );
  }, [billingCatalog?.lab_tests, labSearchQ]);

  const filteredServiceRequestLabTests = useMemo(() => {
    const tests = billingCatalog?.lab_tests ?? EMPTY_ARRAY;
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return tests;
    return tests.filter(
      (t) => String(t.name || '').toLowerCase().includes(q) || String(t.code || '').toLowerCase().includes(q)
    );
  }, [billingCatalog?.lab_tests, serviceRequestExamSearchQ]);

  const filteredServiceRequestSpecialties = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return specializedSpecialties;
    return specializedSpecialties.filter(
      (s) => String(s.label || '').toLowerCase().includes(q) || String(s.code || '').toLowerCase().includes(q)
    );
  }, [specializedSpecialties, serviceRequestExamSearchQ]);

  const filteredServiceRequestImaging = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return imagingExaminations;
    return imagingExaminations.filter(
      (e) => String(e.label || '').toLowerCase().includes(q) || String(e.code || '').toLowerCase().includes(q)
    );
  }, [imagingExaminations, serviceRequestExamSearchQ]);

  const filteredServicePrestations = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return servicePrestations;
    return servicePrestations.filter(
      (svc) => String(svc.label || '').toLowerCase().includes(q) || String(svc.code || '').toLowerCase().includes(q)
    );
  }, [servicePrestations, serviceRequestExamSearchQ]);

  const filteredSurgicalActs = useMemo(() => {
    const q = serviceRequestExamSearchQ.trim().toLowerCase();
    if (!q) return surgicalActs;
    return surgicalActs.filter(
      (act) => String(act.label || '').toLowerCase().includes(q) || String(act.code || '').toLowerCase().includes(q)
    );
  }, [surgicalActs, serviceRequestExamSearchQ]);

  return {
    specializedSpecialties,
    imagingExaminations,
    surgicalActs,
    admissionServices,
    billingDepartments,
    servicePrestations,
    filteredAdmissionLabTests,
    filteredLabTests,
    filteredServiceRequestLabTests,
    filteredServiceRequestSpecialties,
    filteredServiceRequestImaging,
    filteredServicePrestations,
    filteredSurgicalActs,
  };
}
