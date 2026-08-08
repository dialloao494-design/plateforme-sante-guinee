import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../../../services/clinicalApi';
import { useAuth } from '../../../../contexts/AuthContext.jsx';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';
import { formatApiError } from '../../../../utils/apiError.js';
import { resolveRegistrationConflict } from '../registrationConflict.js';
import { SPECIALTY_OTHER_CODE } from '../../../../constants/clinicBranding.js';
import { payerTypeLabel } from '../../../../constants/clinicBranding.js';
import {
  ADMISSION_TYPES,
  DASHBOARD_BUCKET_TITLES,
  EMPTY_ADMISSION,
  EMPTY_BILLING,
  EMPTY_REFUND,
  EMPTY_REG,
  EMPTY_SERVICE_REQUEST,
  PATIENT_REQUIRED_NOTICE,
  PAYMENT_METHODS,
  REFUND_METHODS,
  REFUND_REASONS,
  SERVICE_REQUEST_CHARGE_TYPES,
  SERVICE_REQUEST_DEPARTMENTS,
  SERVICE_REQUEST_STATUSES,
  TABS,
  emptyPaymentLine,
} from '../constants.js';
import {
  formatDateTime,
  methodLabel,
  patientFullName,
  refundStatusLabel,
} from '../utils.js';
import SpecialtyPicker from '../components/SpecialtyPicker.jsx';
import { useBillingCatalogFilters } from './useBillingCatalogFilters.js';
import { buildInvoiceItemPayload } from './buildInvoiceItemPayload.js';
import {
  isCompleteRegistrationResponse,
  REGISTRATION_INCOMPLETE_MESSAGE,
} from '../registrationSuccess.js';
export function useReceptionDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);
  const regPrintRef = useRef(null);

  const [tab, setTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [stats, setStats] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const [selectedPatient, setSelectedPatient] = useState(null);
  const [registeredPatient, setRegisteredPatient] = useState(null);
  const [registrationPrintForm, setRegistrationPrintForm] = useState(null);
  const [lastAdmission, setLastAdmission] = useState(null);
  const [lastRefund, setLastRefund] = useState(null);

  const [invoices, setInvoices] = useState([]);
  const [activeInvoice, setActiveInvoice] = useState(null);
  const [refunds, setRefunds] = useState([]);

  const [regForm, setRegForm] = useState(EMPTY_REG);
  const [duplicateMatches, setDuplicateMatches] = useState([]);
  const [pendingRegPayload, setPendingRegPayload] = useState(null);
  const [admissionForm, setAdmissionForm] = useState(EMPTY_ADMISSION);
  const [admissionImagingCode, setAdmissionImagingCode] = useState('');
  const [admissionLabSearchQ, setAdmissionLabSearchQ] = useState('');
  const [admissionLabSelection, setAdmissionLabSelection] = useState(null);
  const [billingForm, setBillingForm] = useState(EMPTY_BILLING);
  const [paymentLines, setPaymentLines] = useState([emptyPaymentLine()]);
  const [selectedSpecialty, setSelectedSpecialty] = useState('');
  const [selectedImaging, setSelectedImaging] = useState('');
  const [refundForm, setRefundForm] = useState(EMPTY_REFUND);

  const [invoiceSearchQ, setInvoiceSearchQ] = useState('');
  const [invoiceSearchHits, setInvoiceSearchHits] = useState([]);
  const [billingCatalog, setBillingCatalog] = useState(null);
  const [billingLineItems, setBillingLineItems] = useState([]);
  const [labSearchQ, setLabSearchQ] = useState('');
  const [activeStatBucket, setActiveStatBucket] = useState(null);
  const [queueRows, setQueueRows] = useState([]);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [serviceRequests, setServiceRequests] = useState([]);
  const [serviceRequestSearchQ, setServiceRequestSearchQ] = useState('');
  const [serviceRequestExamSearchQ, setServiceRequestExamSearchQ] = useState('');
  const [serviceRequestStatusFilter, setServiceRequestStatusFilter] = useState('');
  const [serviceRequestForm, setServiceRequestForm] = useState(EMPTY_SERVICE_REQUEST);
  const [editingServiceRequestId, setEditingServiceRequestId] = useState(null);
  const [loadingServiceRequests, setLoadingServiceRequests] = useState(false);
  const [lastCreatedServiceRequest, setLastCreatedServiceRequest] = useState(null);
  const [billingServiceRequestId, setBillingServiceRequestId] = useState('');
  const [loadingBillingServiceRequest, setLoadingBillingServiceRequest] = useState(false);

  const {
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
  } = useBillingCatalogFilters(billingCatalog, {
    labSearchQ,
    admissionLabSearchQ,
    serviceRequestExamSearchQ,
  });

  const updateReg = (v) => setRegForm((p) => ({ ...p, ...v }));
  const updateAdmission = (v) => setAdmissionForm((p) => ({ ...p, ...v }));
  const updateBilling = (v) => setBillingForm((p) => ({ ...p, ...v }));
  const updatePaymentLine = (id, patch) =>
    setPaymentLines((rows) => rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  const addPaymentLine = () => setPaymentLines((rows) => [...rows, emptyPaymentLine()]);
  const removePaymentLine = (id) =>
    setPaymentLines((rows) => (rows.length <= 1 ? rows : rows.filter((r) => r.id !== id)));

  const resolveSpecialtyLabel = (code, other) => {
    if (code === SPECIALTY_OTHER_CODE) return (other || '').trim();
    return specializedSpecialties.find((s) => s.code === code)?.label || '';
  };

  const syncSpecialtyCode = (code) => {
    updateAdmission({ specialty_code: code });
    setSelectedSpecialty(code);
  };

  const syncSpecialtyOther = (text) => {
    updateAdmission({ specialty_other: text });
  };

  const showSpecialtyPicker =
    admissionForm.admission_type === 'specialized_consultation'
    || (admissionForm.services || []).includes('Consultation spécialisée');

  const renderSpecialtyPicker = (idSuffix = '', { required = showSpecialtyPicker } = {}) => (
    <SpecialtyPicker
      idSuffix={idSuffix}
      required={required}
      admissionForm={admissionForm}
      selectedSpecialty={selectedSpecialty}
      specializedSpecialties={specializedSpecialties}
      onCodeChange={syncSpecialtyCode}
      onOtherChange={syncSpecialtyOther}
    />
  );

  const addSpecializedConsultation = () => {
    const code = admissionForm.specialty_code || selectedSpecialty;
    const label = resolveSpecialtyLabel(code, admissionForm.specialty_other);
    if (!code) {
      setError('Sélectionnez une spécialité pour la consultation spécialisée.');
      return;
    }
    if (!label) {
      setError('Précisez la spécialité pour « Autre ».');
      return;
    }
    const spec = specializedSpecialties.find((s) => s.code === code);
    const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'specialized_consultation');
    const price = Number(spec?.price_gnf ?? svc?.price_gnf ?? 250000);
    addBillingLine({
      charge_type: svc?.charge_type || 'consultation',
      description: `Consultation spécialisée — ${label}`,
      quantity: 1,
      unit_price_gnf: price,
      catalog_code: code !== SPECIALTY_OTHER_CODE ? code : undefined,
      price_variant: code !== SPECIALTY_OTHER_CODE ? 'specialized' : undefined,
    });
    updateBilling({ department: 'Consultation spécialisée' });
    syncSpecialtyCode('');
    syncSpecialtyOther('');
    setError('');
  };

  const addEmergencyConsultation = () => {
    const code = admissionForm.specialty_code || selectedSpecialty;
    const label = resolveSpecialtyLabel(code, admissionForm.specialty_other);
    const spec = specializedSpecialties.find((s) => s.code === code);
    const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'emergency_consultation');
    const price = Number(spec?.emergency_price_gnf ?? svc?.price_gnf ?? 150000);
    const desc = label ? `Consultation d'urgences — ${label}` : (svc?.label || "Consultation d'urgences");
    // Always send a catalog code: specialty code + emergency variant, or generic emergency.
    const catalogCode =
      code && code !== SPECIALTY_OTHER_CODE
        ? code
        : (svc?.code || 'emergency_consultation');
    addBillingLine({
      charge_type: svc?.charge_type || 'consultation',
      description: desc,
      quantity: 1,
      unit_price_gnf: price,
      catalog_code: catalogCode,
      price_variant: 'emergency',
    });
    updateBilling({ department: "Consultation urgences" });
    setError('');
  };

  const addImagingExam = () => {
    if (!selectedImaging) {
      setError('Sélectionnez un examen d\'imagerie médicale.');
      return;
    }
    const exam = imagingExaminations.find((e) => e.code === selectedImaging);
    if (!exam) return;
    addBillingLine({
      charge_type: 'radiology',
      description: exam.label,
      quantity: 1,
      unit_price_gnf: exam.price_gnf,
      catalog_code: exam.code,
    });
    updateBilling({ department: 'Imagerie médicale' });
    setSelectedImaging('');
    setError('');
  };

  const prefillPaymentLines = (remaining) => {
    const amt = Number(remaining) || 0;
    setPaymentLines([{ ...emptyPaymentLine(), amount_gnf: amt > 0 ? String(amt) : '' }]);
  };
  const updateRefund = (v) => setRefundForm((p) => {
    const next = { ...p, ...v };
    if ('amount_consumed_gnf' in v && next.invoice_id) {
      const inv = invoices.find((item) => String(item.id) === String(next.invoice_id));
      const paid = Number(inv?.paid_amount_gnf || 0);
      const consumed = Number(next.amount_consumed_gnf || 0);
      if (next.amount_consumed_gnf !== '') {
        next.refund_amount_gnf = String(Math.max(0, paid - consumed));
      }
    }
    return next;
  });

  const loadDashboard = useCallback(async () => {
    try {
      const { data } = await clinicalApi.receptionHisDashboard({ forceRefresh: true });
      setStats(data || null);
    } catch (e) {
      setError(formatApiError(e, 'Impossible de charger le tableau de bord'));
    }
  }, []);

  const loadInvoices = useCallback(async (patientId) => {
    if (!patientId) {
      setInvoices([]);
      return;
    }
    try {
      const { data } = await clinicalApi.receptionHisListInvoices(patientId);
      setInvoices(data || []);
    } catch {
      setInvoices([]);
    }
  }, []);

  const loadRefunds = useCallback(async (patientId) => {
    try {
      const { data } = await clinicalApi.receptionHisListRefunds(patientId);
      setRefunds(data || []);
    } catch {
      setRefunds([]);
    }
  }, []);

  const refresh = useCallback(async () => {
    await Promise.all([loadDashboard(), loadInvoices(selectedPatient?.id), loadRefunds(selectedPatient?.id)]);
  }, [loadDashboard, loadInvoices, loadRefunds, selectedPatient?.id]);

  useEffect(() => {
    loadDashboard();
    clinicalApi.clinicDoctors().then((r) => setDoctors(r.data || [])).catch(() => setDoctors([]));
    clinicalApi.receptionHisBillingCatalog().then((r) => setBillingCatalog(r.data || null)).catch(() => setBillingCatalog(null));
  }, [loadDashboard]);


  const loadServiceRequests = useCallback(async () => {
    setLoadingServiceRequests(true);
    try {
      const params = {};
      if (selectedPatient?.id) params.patient_id = selectedPatient.id;
      if (serviceRequestSearchQ.trim()) params.q = serviceRequestSearchQ.trim();
      if (serviceRequestStatusFilter) params.status = serviceRequestStatusFilter;
      const { data } = await clinicalApi.receptionHisListServiceRequests(params);
      setServiceRequests(data || []);
    } catch {
      setServiceRequests([]);
    } finally {
      setLoadingServiceRequests(false);
    }
  }, [selectedPatient?.id, serviceRequestSearchQ, serviceRequestStatusFilter]);

  const loadQueueBucket = async (bucket) => {
    if (activeStatBucket === bucket) {
      setActiveStatBucket(null);
      setQueueRows([]);
      return;
    }
    setActiveStatBucket(bucket);
    setLoadingQueue(true);
    setError('');
    try {
      const { data } = await clinicalApi.receptionHisDashboardQueue(bucket);
      setQueueRows(data || []);
    } catch (err) {
      setQueueRows([]);
      setError(formatApiError(err, 'Impossible de charger la liste'));
    } finally {
      setLoadingQueue(false);
    }
  };

  const openInvoiceById = async (invoiceId, patientId) => {
    if (!invoiceId) return;
    if (patientId) {
      await selectPatient({ id: patientId });
    }
    try {
      const { data } = await clinicalApi.receptionHisGetInvoice(invoiceId);
      if (data) {
        setActiveInvoice(data);
        setTab('billing');
      }
    } catch {
      setError('Impossible d\'ouvrir la facture.');
    }
  };

  const resetServiceRequestForm = () => {
    setServiceRequestForm(EMPTY_SERVICE_REQUEST);
    setServiceRequestExamSearchQ('');
    setEditingServiceRequestId(null);
  };

  const startEditServiceRequest = (row) => {
    setEditingServiceRequestId(row.id);
    setServiceRequestForm({
      service_category: row.service_category,
      service_name: row.service_name,
      catalog_code: row.catalog_code || '',
      charge_type: row.charge_type || SERVICE_REQUEST_CHARGE_TYPES[row.service_category] || 'other',
      unit_price_gnf: Number(row.unit_price_gnf || 0),
      status: row.status,
    });
    setServiceRequestExamSearchQ(row.service_name || '');
  };

  const saveServiceRequest = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Sélectionnez un patient pour créer une demande de service.');
    if (!serviceRequestForm.service_name.trim()) return setError('Indiquez le nom du service.');
    setLoading(true);
    setError('');
    try {
      const payload = {
        service_category: serviceRequestForm.service_category,
        service_name: serviceRequestForm.service_name.trim(),
        department: SERVICE_REQUEST_DEPARTMENTS[serviceRequestForm.service_category] || null,
        catalog_code: serviceRequestForm.catalog_code || null,
        charge_type:
          serviceRequestForm.charge_type
          || SERVICE_REQUEST_CHARGE_TYPES[serviceRequestForm.service_category]
          || 'other',
        unit_price_gnf: Number(serviceRequestForm.unit_price_gnf || 0),
        status: serviceRequestForm.status,
      };
      if (editingServiceRequestId) {
        await clinicalApi.receptionHisUpdateServiceRequest(editingServiceRequestId, payload);
        setMessage('Demande de service mise à jour.');
        setLastCreatedServiceRequest(null);
      } else {
        const { data } = await clinicalApi.receptionHisCreateServiceRequest({
          patient_id: selectedPatient.id,
          ...payload,
        });
        setLastCreatedServiceRequest(data);
        setMessage(
          `Demande enregistrée (${data.request_number}). Collez ce N° en facturation pour l'ajouter au tableau Produits / Services.`
        );
      }
      resetServiceRequestForm();
      await loadServiceRequests();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement de la demande impossible'));
    } finally {
      setLoading(false);
    }
  };

  const deleteServiceRequest = async (id) => {
    if (!window.confirm('Supprimer cette demande de service ?')) return;
    setLoading(true);
    try {
      await clinicalApi.receptionHisDeleteServiceRequest(id);
      setMessage('Demande de service supprimée.');
      if (editingServiceRequestId === id) resetServiceRequestForm();
      await loadServiceRequests();
    } catch (err) {
      setError(formatApiError(err, 'Suppression impossible'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === 'service_requests') {
      loadServiceRequests();
    }
  }, [tab, loadServiceRequests]);

  const runPatientSearch = useCallback(async (query) => {
    const q = (query ?? searchQ).trim();
    if (!q) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const { data } = await clinicalApi.receptionHisSearch(q);
      setSearchResults(data || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, [searchQ]);

  useEffect(() => {
    if (!searchQ.trim()) return void setSearchResults([]);
    const t = setTimeout(() => runPatientSearch(searchQ), 250);
    return () => clearTimeout(t);
  }, [searchQ, runPatientSearch]);

  useEffect(() => {
    if (!selectedPatient?.id || !invoiceSearchQ.trim()) return void setInvoiceSearchHits([]);
    const t = setTimeout(async () => {
      try {
        const { data } = await clinicalApi.receptionHisSearchInvoice(invoiceSearchQ.trim(), selectedPatient.id);
        setInvoiceSearchHits(data ? [data] : []);
      } catch {
        setInvoiceSearchHits([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [invoiceSearchQ, selectedPatient?.id]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === 'F3') {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;
      const hit = TABS.find((t) => t.shortcut === e.key);
      if (hit) setTab(hit.id);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const selectPatient = async (p) => {
    if (!p?.id) return;
    let patient = p;
    try {
      const { data } = await clinicalApi.receptionHisGetPatient(p.id);
      if (data?.id) patient = data;
    } catch {
      try {
        const { data } = await clinicalApi.receptionHisSearch(String(p.patient_number || p.id));
        const hit = (data || []).find((row) => row.id === p.id) || data?.[0];
        if (hit?.id) patient = hit;
      } catch {
        /* keep partial payload */
      }
    }
    setSelectedPatient(patient);
    setLastAdmission(null);
    setLastRefund(null);
    setSearchQ('');
    setSearchResults([]);
    setActiveInvoice(null);
    setInvoiceSearchQ('');
    setInvoiceSearchHits([]);
    setRefundForm((prev) => ({
      ...prev,
      invoice_id: '',
      recipient_name: prev.recipient_name || patientFullName(patient),
      recipient_phone: prev.recipient_phone || patient.phone || '',
    }));
    await Promise.all([loadInvoices(patient.id), loadRefunds(patient.id)]);
    setMessage(`Patient sélectionné : ${patientFullName(patient)} · N° dossier ${patient.patient_number || '—'}`);
  };

  const clearPatient = () => {
    setSelectedPatient(null);
    setInvoices([]);
    setRefunds([]);
    setActiveInvoice(null);
    setRefundForm((prev) => ({ ...prev, invoice_id: '' }));
  };

  const onPhotoFile = (file) => {
    if (!file) return updateReg({ photo_url: '' });
    if (file.size > 400 * 1024) return setError('La photo doit faire moins de 400 KB.');
    const reader = new FileReader();
    reader.onload = () => {
      updateReg({ photo_url: String(reader.result || '') });
      setError('');
    };
    reader.onerror = () => setError('Lecture de la photo impossible.');
    reader.readAsDataURL(file);
  };

  const printRegistrationSheet = () => {
    if (!registeredPatient) return;
    window.print();
  };

  const resolveRelationship = (form) => {
    if (form.emergency_relationship === 'Autre') {
      return form.emergency_relationship_other?.trim() || 'Autre';
    }
    return form.emergency_relationship || undefined;
  };

  const renderQueueTable = () => {
    if (!activeStatBucket) return null;
    if (loadingQueue) return <p className="clinical-hint">Chargement…</p>;
    if (!queueRows.length) return <p className="clinical-hint">Aucun élément dans cette liste.</p>;

    const bucket = activeStatBucket;
    if (bucket === 'total_patients' || bucket === 'patients_registered_today') {
      return (
        <table className="lab-his-queue-table">
          <thead>
            <tr><th>Patient</th><th>N° dossier</th><th>Téléphone</th><th>Sexe</th><th>Date inscription</th><th /></tr>
          </thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={`${row.patient_id}-${row.patient_number}`}>
                <td>{row.patient_name}</td>
                <td>{row.patient_number || row.patient_id}</td>
                <td>{row.phone || '—'}</td>
                <td>{row.gender || '—'}</td>
                <td>{formatDateTime(row.registration_date)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectPatient({ id: row.patient_id })}>Ouvrir</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'admissions_today') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>Heure admission</th><th>Service</th><th>Statut</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.admission_id}>
                <td>{row.patient_name}</td>
                <td>{formatDateTime(row.admitted_at)}</td>
                <td>{row.department || '—'}</td>
                <td>{row.status}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectPatient({ id: row.patient_id })}>Ouvrir patient</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'hospitalized_patients') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>Chambre</th><th>Médecin</th><th>Date admission</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.admission_id}>
                <td>{row.patient_name}</td>
                <td>{row.room || '—'}</td>
                <td>{row.doctor_name || '—'}</td>
                <td>{formatDateTime(row.admitted_at)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectPatient({ id: row.patient_id })}>Ouvrir patient</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'paid_invoices') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>N° facture</th><th>Montant</th><th>Mode paiement</th><th>Date paiement</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.invoice_id}>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number}</td>
                <td>{formatGNF(row.amount_gnf || 0)}</td>
                <td>{methodLabel(PAYMENT_METHODS, row.payment_method)}</td>
                <td>{formatDateTime(row.paid_at)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openInvoiceById(row.invoice_id, row.patient_id)}>Ouvrir facture</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'unpaid_invoices') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>N° facture</th><th>Solde dû</th><th>Date facture</th><th /></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.invoice_id}>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number}</td>
                <td>{formatGNF(row.outstanding_balance_gnf || 0)}</td>
                <td>{formatDateTime(row.issued_at)}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openInvoiceById(row.invoice_id, row.patient_id)}>Ouvrir facture</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'revenue_today' || bucket === 'revenue_month') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>Patient</th><th>N° facture</th><th>Montant</th><th>Mode</th><th>Date / heure</th></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={`${row.payment_id}-${row.invoice_id}`}>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number || '—'}</td>
                <td>{formatGNF(row.amount_gnf || 0)}</td>
                <td>{methodLabel(PAYMENT_METHODS, row.payment_method)}</td>
                <td>{formatDateTime(row.paid_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (bucket === 'refunds') {
      return (
        <table className="lab-his-queue-table">
          <thead><tr><th>N° remboursement</th><th>Patient</th><th>Facture</th><th>Montant</th><th>Raison</th><th>Statut</th><th>Date</th></tr></thead>
          <tbody>
            {queueRows.map((row) => (
              <tr key={row.refund_id}>
                <td>{row.refund_number}</td>
                <td>{row.patient_name}</td>
                <td>{row.invoice_number || '—'}</td>
                <td>{formatGNF(row.refund_amount_gnf || 0)}</td>
                <td>{row.reason}</td>
                <td>{refundStatusLabel(row.status)}</td>
                <td>{formatDateTime(row.paid_at || row.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    return null;
  };

  const buildRegistrationPayload = (confirmDuplicate = false) => {
    const manualAge = regForm.age_years !== '' ? Number(regForm.age_years) : null;
    const resolvedDob =
      regForm.date_of_birth_precision === 'year' && regForm.birth_year.length === 4
        ? `${regForm.birth_year}-01-01`
        : (regForm.date_of_birth_precision === 'full' && regForm.date_of_birth ? regForm.date_of_birth : null);
    if (!resolvedDob && (manualAge == null || !Number.isFinite(manualAge))) {
      return { error: 'Indiquez une date de naissance, une année de naissance ou saisissez l’âge du patient.' };
    }
    return {
      payload: {
        first_name: regForm.first_name.trim(),
        last_name: regForm.last_name.trim(),
        date_of_birth: resolvedDob,
        date_of_birth_precision: resolvedDob ? regForm.date_of_birth_precision : 'unknown',
        age_years: manualAge != null && Number.isFinite(manualAge) ? manualAge : undefined,
        gender: regForm.gender,
        is_newborn: regForm.is_newborn,
        registration_date: regForm.registration_date || undefined,
        marital_status: regForm.marital_status || undefined,
        nationality: regForm.nationality || undefined,
        mother_last_name: regForm.mother_last_name || undefined,
        mother_first_name: regForm.mother_first_name || undefined,
        profession: regForm.profession || undefined,
        preferred_language: regForm.preferred_language || undefined,
        email: regForm.email || undefined,
        photo_url: regForm.photo_url || undefined,
        address: regForm.address.trim(),
        phone: regForm.phone.trim(),
        phone_secondary: regForm.phone_secondary || undefined,
        commune: regForm.commune || undefined,
        city: regForm.city || undefined,
        region: regForm.region || undefined,
        country: regForm.country || undefined,
        emergency_contact: {
          same_address_as_patient: regForm.emergency_same_address,
          full_name: regForm.emergency_full_name.trim(),
          relationship: resolveRelationship(regForm),
          phone: regForm.emergency_phone.trim(),
          address: regForm.emergency_same_address ? regForm.address : regForm.emergency_address || undefined,
          commune: regForm.emergency_same_address ? regForm.commune : regForm.emergency_commune || undefined,
          region: regForm.emergency_same_address ? regForm.region : regForm.emergency_region || undefined,
          country: regForm.emergency_same_address ? regForm.country : regForm.emergency_country || undefined,
        },
        payer: {
          payer_type: regForm.payer_type,
          insurance_company: regForm.payer_type === 'insurance' ? regForm.insurance_company || undefined : undefined,
          insurance_number: regForm.payer_type === 'insurance' ? regForm.insurance_number || undefined : undefined,
          company_name: regForm.payer_type === 'company' ? regForm.company_name || undefined : undefined,
          notes: regForm.payer_notes || undefined,
        },
        confirm_duplicate: Boolean(confirmDuplicate),
      },
    };
  };

  const submitRegistration = async (payload) => {
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.receptionHisRegister(payload);
      // Offline/optimistic queue returns 202 without a real dossier number — never
      // present that as a successful registration (clinic sees "data taken, no ID").
      if (!isCompleteRegistrationResponse(data)) {
        setError(REGISTRATION_INCOMPLETE_MESSAGE);
        return false;
      }
      setDuplicateMatches([]);
      setPendingRegPayload(null);
      setRegistrationPrintForm({ ...regForm });
      setRegisteredPatient(data);
      // Keep identity fields filled so staff can see name + generated ID together.
      // Form clears only via « Nouvel enregistrement ».
      setMessage(`Patient enregistré · N° dossier patient ${data.patient_number}`);
      if (data?.id) await selectPatient(data);
      await loadDashboard();
      return true;
    } catch (err) {
      const conflict = resolveRegistrationConflict(err, payload);
      setDuplicateMatches(conflict.matches);
      setPendingRegPayload(conflict.pendingPayload);
      setError(conflict.message);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const built = buildRegistrationPayload(false);
    if (built.error) {
      setError(built.error);
      return;
    }
    await submitRegistration(built.payload);
  };

  const handleConfirmDuplicateRegister = async () => {
    const payload = pendingRegPayload || buildRegistrationPayload(true).payload;
    if (!payload) {
      setError('Impossible de confirmer l’enregistrement. Resaisissez le formulaire.');
      return;
    }
    await submitRegistration({ ...payload, confirm_duplicate: true });
  };

  const openExistingDuplicate = async (match) => {
    if (!match?.id) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await clinicalApi.receptionHisGetPatient(match.id);
      setDuplicateMatches([]);
      setPendingRegPayload(null);
      await selectPatient(data || match);
      setTab('admission');
      setMessage(`Patient existant ouvert · N° dossier patient ${(data || match)?.patient_number || '—'}`);
    } catch (err) {
      setError(formatApiError(err, 'Ouverture du patient existant impossible'));
    } finally {
      setLoading(false);
    }
  };

  const clearDuplicatePanel = () => {
    setDuplicateMatches([]);
    setPendingRegPayload(null);
    setError('');
  };

  const handleAdmission = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Recherchez et sélectionnez un patient avant de créer l’admission.');
    setLoading(true);
    setError('');
    setMessage('');
    try {
      let services = (admissionForm.services || []).filter(Boolean);
      if (!services.length) return setError('Sélectionnez au moins un service.');
      if (showSpecialtyPicker) {
        const specialtyLabel = resolveSpecialtyLabel(admissionForm.specialty_code, admissionForm.specialty_other);
        if (!admissionForm.specialty_code) {
          return setError('Sélectionnez une spécialité pour la consultation spécialisée.');
        }
        if (!specialtyLabel) {
          return setError('Précisez la spécialité pour « Autre ».');
        }
        if (services.includes('Consultation spécialisée')) {
          services = services.map((s) =>
            s === 'Consultation spécialisée' ? `Consultation spécialisée — ${specialtyLabel}` : s
          );
        }
        if (admissionForm.admission_type === 'specialized_consultation' && !services.some((s) => s.startsWith('Consultation spécialisée'))) {
          services.push(`Consultation spécialisée — ${specialtyLabel}`);
        }
      }
      if (services.includes('Imagerie médicale')) {
        if (!admissionImagingCode) {
          return setError('Sélectionnez un examen d\'imagerie médicale.');
        }
        const exam = imagingExaminations.find((e) => e.code === admissionImagingCode);
        if (exam) {
          services = services.map((s) => (s === 'Imagerie médicale' ? `Imagerie médicale — ${exam.label}` : s));
        }
      }
      if (services.includes('Laboratoire')) {
        if (!admissionLabSelection) {
          return setError('Sélectionnez un examen de laboratoire.');
        }
        services = services.map((s) =>
          s === 'Laboratoire' ? `Laboratoire — ${admissionLabSelection.name}` : s
        );
      }
      const { data } = await clinicalApi.receptionHisCreateAdmission({
        patient_id: selectedPatient.id,
        admission_date: admissionForm.admission_date,
        admission_time: `${admissionForm.admission_time}:00`,
        services,
        department: services[0],
        admission_type: admissionForm.admission_type,
        attending_clinician_user_id: admissionForm.attending_clinician_user_id
          ? Number(admissionForm.attending_clinician_user_id)
          : undefined,
        attending_physician_name: admissionForm.attending_physician_name || undefined,
        confirmation_status: admissionForm.confirmation_status,
        specialty_code: admissionForm.specialty_code || undefined,
        specialty_other: admissionForm.specialty_other || undefined,
        notes: admissionForm.notes || undefined,
      });
      setLastAdmission(data || null);
      setAdmissionImagingCode('');
      setAdmissionLabSelection(null);
      setAdmissionLabSearchQ('');
      setMessage(`Admission créée · N° admission ${data?.admission_number || '—'}`);
      await loadDashboard();
      setTab('billing');
    } catch (err) {
      setError(formatApiError(err, 'Création de l’admission impossible'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInvoice = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Recherchez et sélectionnez un patient avant de créer la facture.');
    if (billingLineItems.length === 0) return setError('Ajoutez au moins une prestation à la facture.');
    if (Number(billingForm.exemption_percent || 0) > 0 && !String(billingForm.exemption_reason || '').trim()) {
      return setError('Indiquez le motif d’exemption avant de créer la facture.');
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.receptionHisCreateInvoice({
        patient_id: selectedPatient.id,
        department: billingForm.department,
        items: billingLineItems.map((l) => buildInvoiceItemPayload(l)),
        exemption_percent: Number(billingForm.exemption_percent || 0),
        exemption_reason:
          Number(billingForm.exemption_percent || 0) > 0
            ? (billingForm.exemption_reason || '').trim() || undefined
            : undefined,
        billing_date: billingForm.billing_date || undefined,
      });
      setActiveInvoice(data || null);
      setBillingLineItems([]);
      prefillPaymentLines(data?.remaining_balance_gnf ?? data?.total_amount_gnf ?? 0);
      setMessage(`Facture créée · N° facture ${data?.invoice_number || '—'}`);
      await Promise.all([loadInvoices(selectedPatient.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Création de facture impossible'));
    } finally {
      setLoading(false);
    }
  };

  const selectInvoice = (id) => {
    const inv = invoices.find((item) => String(item.id) === String(id));
    setActiveInvoice(inv || null);
    prefillPaymentLines(inv?.remaining_balance_gnf ?? 0);
    updateRefund({
      invoice_id: inv ? String(inv.id) : '',
      service_paid_for: inv?.department || '',
      amount_consumed_gnf: '',
      refund_amount_gnf: '',
    });
  };

  const handlePayment = async (e) => {
    e.preventDefault();
    if (!activeInvoice?.id) return setError('Sélectionnez une facture du patient.');
    const lines = paymentLines.filter((l) => Number(l.amount_gnf) > 0);
    if (lines.length === 0) return setError('Ajoutez au moins une ligne de paiement avec un montant.');
    const draftTotal = lines.reduce((s, l) => s + Number(l.amount_gnf), 0);
    const remaining = Number(activeInvoice.remaining_balance_gnf ?? 0);
    if (draftTotal > remaining) {
      return setError(`Le total des paiements (${formatGNF(draftTotal)}) dépasse le reste à payer (${formatGNF(remaining)}).`);
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      let lastData = activeInvoice;
      for (const line of lines) {
        const { data } = await clinicalApi.receptionHisAddPayment(activeInvoice.id, {
          amount_gnf: Number(line.amount_gnf),
          payment_method: line.payment_method,
          reference: line.reference || undefined,
        });
        lastData = data || lastData;
      }
      setMessage(`Paiement(s) enregistré(s) · reste ${formatGNF(lastData?.remaining_balance_gnf || 0)}`);
      prefillPaymentLines(lastData?.remaining_balance_gnf ?? 0);
      setActiveInvoice(lastData || null);
      await Promise.all([loadInvoices(selectedPatient?.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement du paiement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const handleRefund = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) return setError('Recherchez et sélectionnez un patient avant de créer l’admission.');
    if (!refundForm.invoice_id) return setError('Sélectionnez une facture du patient.');
    if (refundForm.reason === 'other' && !(refundForm.reason_notes || '').trim()) {
      return setError('Saisissez le motif du remboursement (Autre).');
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.receptionHisCreateRefund({
        invoice_id: Number(refundForm.invoice_id),
        service_paid_for: refundForm.service_paid_for || undefined,
        amount_consumed_gnf: Number(refundForm.amount_consumed_gnf || 0),
        refund_amount_gnf: Number(refundForm.refund_amount_gnf || 0),
        recipient_name: refundForm.recipient_name.trim(),
        recipient_phone: refundForm.recipient_phone.trim(),
        refund_method: refundForm.refund_method,
        reason: refundForm.reason,
        reason_notes: refundForm.reason_notes || undefined,
      });
      setMessage(`Demande enregistrée · N° remboursement ${data?.refund_number || '—'}`);
      setLastRefund(data || null);
      setRefundForm((prev) => ({ ...EMPTY_REFUND, invoice_id: prev.invoice_id }));
      await Promise.all([loadRefunds(selectedPatient.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Création du remboursement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const updateRefundStatus = async (id, status) => {
    setLoading(true);
    setError('');
    try {
      await clinicalApi.receptionHisUpdateRefund(id, { status });
      setMessage(`Remboursement mis à jour : ${refundStatusLabel(status)}`);
      await Promise.all([loadRefunds(selectedPatient?.id), loadDashboard()]);
    } catch (err) {
      setError(formatApiError(err, 'Mise à jour du remboursement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const printInvoiceReceipt = async (invoiceId) => {
    try {
      const { data } = await clinicalApi.receptionHisInvoiceReceipt(invoiceId);
      window.open(URL.createObjectURL(data), '_blank');
    } catch (err) {
      const status = err?.response?.status;
      setError(
        status === 401 || status === 403
          ? 'Session expirée : reconnectez-vous puis réessayez l’impression du reçu.'
          : formatApiError(err, 'Impossible d’imprimer le reçu.')
      );
    }
  };

  const printRefundReceipt = async (refundId) => {
    try {
      const { data } = await clinicalApi.receptionHisRefundReceipt(refundId);
      window.open(URL.createObjectURL(data), '_blank');
    } catch (err) {
      const status = err?.response?.status;
      setError(
        status === 401 || status === 403
          ? 'Session expirée : reconnectez-vous puis réessayez l’impression du reçu.'
          : formatApiError(err, 'Impossible d’imprimer le reçu de remboursement.')
      );
    }
  };

  const statCards = useMemo(() => {
    if (!stats) return [];
    return [
      { key: 'total_patients', label: 'Total patients', value: stats.total_patients ?? 0 },
      { key: 'patients_registered_today', label: 'Patients inscrits aujourd\'hui', value: stats.patients_registered_today ?? 0, variant: 'success' },
      { key: 'admissions_today', label: 'Admissions aujourd\'hui', value: stats.admissions_today ?? 0 },
      { key: 'hospitalized_patients', label: 'Patients hospitalisés', value: stats.hospitalized_patients ?? 0, variant: 'warning' },
      { key: 'paid_invoices', label: 'Factures payées', value: stats.paid_invoices ?? 0, variant: 'success' },
      { key: 'unpaid_invoices', label: 'Factures impayées', value: stats.unpaid_invoices ?? 0, variant: 'warning' },
      { key: 'revenue_today', label: 'Recette du jour', value: formatGNF(stats.revenue_today_gnf ?? 0), variant: 'accent' },
      { key: 'revenue_month', label: 'Recette du mois', value: formatGNF(stats.revenue_month_gnf ?? 0), variant: 'accent' },
      { key: 'refunds', label: 'Total remboursements', value: formatGNF(stats.refunds_total_gnf ?? 0) },
    ];
  }, [stats]);

  const filteredRefunds = useMemo(() => {
    if (!selectedPatient?.id) return [];
    return refunds.filter((r) => Number(r.patient_id) === Number(selectedPatient.id));
  }, [refunds, selectedPatient?.id]);

  const addBillingLine = (line) => {
    setBillingLineItems((prev) => [...prev, { id: `line-${Date.now()}-${Math.random()}`, ...line }]);
  };

  const removeBillingLine = (id) => setBillingLineItems((prev) => prev.filter((l) => l.id !== id));

  const chooseServiceRequest = (category, name, extras = {}) => {
    setServiceRequestForm((prev) => ({
      ...prev,
      service_category: category,
      service_name: name,
      catalog_code: extras.catalog_code || '',
      charge_type: extras.charge_type || SERVICE_REQUEST_CHARGE_TYPES[category] || 'other',
      unit_price_gnf: Number(extras.unit_price_gnf ?? 0),
    }));
    setServiceRequestExamSearchQ(name);
    setError('');
  };

  const applyServiceRequestToBilling = async (request, { switchTab = true } = {}) => {
    if (!request?.id) return;
    if (selectedPatient?.id && Number(selectedPatient.id) !== Number(request.patient_id)) {
      await selectPatient({ id: request.patient_id });
    } else if (!selectedPatient?.id) {
      await selectPatient({ id: request.patient_id });
    }
    const chargeType =
      request.charge_type
      || SERVICE_REQUEST_CHARGE_TYPES[request.service_category]
      || 'other';
    const department =
      request.department
      || SERVICE_REQUEST_DEPARTMENTS[request.service_category]
      || billingForm.department;
    updateBilling({ department });
    addBillingLine({
      charge_type: chargeType,
      description: `${request.service_name} [${request.request_number}]`,
      quantity: 1,
      unit_price_gnf: Number(request.unit_price_gnf || 0),
      source_type: 'service_request',
      source_ref: request.request_number,
      catalog_code: request.catalog_code || undefined,
    });
    setBillingServiceRequestId(request.request_number || '');
    setLastCreatedServiceRequest(request);
    if (switchTab) setTab('billing');
    setMessage(`Demande ${request.request_number} ajoutée au tableau Produits / Services.`);
    setError('');
  };

  const loadServiceRequestIntoBilling = async (e) => {
    e?.preventDefault?.();
    const q = billingServiceRequestId.trim();
    if (!q) return setError('Collez le N° de demande de service (DSR-…).');
    setLoadingBillingServiceRequest(true);
    setError('');
    try {
      const { data } = await clinicalApi.receptionHisLookupServiceRequest(q);
      await applyServiceRequestToBilling(data, { switchTab: false });
    } catch (err) {
      setError(formatApiError(err, 'Demande de service introuvable'));
    } finally {
      setLoadingBillingServiceRequest(false);
    }
  };

  const billingSubtotal = useMemo(
    () => billingLineItems.reduce((sum, l) => sum + Number(l.quantity || 1) * Number(l.unit_price_gnf || 0), 0),
    [billingLineItems]
  );

  const draftExemptionPercent = Number(billingForm.exemption_percent || 0);
  const draftExemptionAmount = Math.round(billingSubtotal * draftExemptionPercent / 100);
  const draftNetTotal = Math.max(0, billingSubtotal - draftExemptionAmount);

  const refundInvoices = useMemo(() => {
    if (!invoiceSearchQ.trim()) return invoices;
    const q = invoiceSearchQ.trim().toLowerCase();
    const ids = new Set((invoiceSearchHits || []).map((x) => Number(x.id)));
    return invoices.filter((i) => String(i.invoice_number || '').toLowerCase().includes(q) || ids.has(Number(i.id)));
  }, [invoiceSearchQ, invoiceSearchHits, invoices]);

  const activeMeta = activeInvoice
    ? {
        subtotal: Number(activeInvoice.subtotal_amount_gnf ?? activeInvoice.total_amount_gnf ?? 0),
        exemptionPercent: Number(activeInvoice.exemption_percent || 0),
        exemptionAmount: Number(activeInvoice.exemption_amount_gnf || 0),
        total: Number(activeInvoice.total_amount_gnf || 0),
        paid: Number(activeInvoice.paid_amount_gnf || 0),
        remaining: Number(activeInvoice.remaining_balance_gnf || 0),
      }
    : null;

  const draftPaymentTotal = useMemo(
    () => paymentLines.reduce((s, l) => s + (Number(l.amount_gnf) || 0), 0),
    [paymentLines]
  );
  const draftRemainingAfterPay = activeMeta ? Math.max(0, activeMeta.remaining - draftPaymentTotal) : null;

  const patientDossier = selectedPatient?.patient_number || '';
  const patientDisplayName = patientFullName(selectedPatient);
  const patientPayerLabel = useMemo(() => {
    if (!selectedPatient) return '';
    try {
      const raw = selectedPatient.payer_json || selectedPatient.payer;
      if (!raw) return '';
      const payer = typeof raw === 'string' ? JSON.parse(raw) : raw;
      return payerTypeLabel(payer?.payer_type);
    } catch {
      return '';
    }
  }, [selectedPatient]);
  return {
    user,
    tab,
    setTab,
    TABS,
    searchRef,
    regPrintRef,
    loading,
    message,
    setMessage,
    error,
    stats,
    doctors,
    searchQ,
    setSearchQ,
    searchResults,
    searching,
    runPatientSearch,
    selectedPatient,
    clearPatient,
    selectPatient,
    registeredPatient,
    registrationPrintForm,
    setRegisteredPatient,
    setRegistrationPrintForm,
    regForm,
    updateReg,
    setRegForm,
    handleRegister,
    handleConfirmDuplicateRegister,
    openExistingDuplicate,
    clearDuplicatePanel,
    duplicateMatches,
    pendingRegPayload,
    onPhotoFile,
    printRegistrationSheet,
    lastAdmission,
    admissionForm,
    updateAdmission,
    admissionServices,
    admissionImagingCode,
    setAdmissionImagingCode,
    admissionLabSearchQ,
    setAdmissionLabSearchQ,
    admissionLabSelection,
    setAdmissionLabSelection,
    filteredAdmissionLabTests,
    showSpecialtyPicker,
    renderSpecialtyPicker,
    handleAdmission,
    imagingExaminations,
    invoices,
    activeInvoice,
    billingForm,
    updateBilling,
    billingDepartments,
    billingCatalog,
    billingLineItems,
    labSearchQ,
    setLabSearchQ,
    filteredLabTests,
    billingServiceRequestId,
    setBillingServiceRequestId,
    loadingBillingServiceRequest,
    loadServiceRequestIntoBilling,
    addSpecializedConsultation,
    addEmergencyConsultation,
    specializedSpecialties,
    selectedSpecialty,
    syncSpecialtyCode,
    selectedImaging,
    setSelectedImaging,
    addImagingExam,
    surgicalActs,
    servicePrestations,
    addBillingLine,
    removeBillingLine,
    billingSubtotal,
    draftExemptionPercent,
    draftExemptionAmount,
    draftNetTotal,
    handleCreateInvoice,
    selectInvoice,
    paymentLines,
    updatePaymentLine,
    addPaymentLine,
    removePaymentLine,
    handlePayment,
    activeMeta,
    draftPaymentTotal,
    draftRemainingAfterPay,
    printInvoiceReceipt,
    patientDossier,
    patientDisplayName,
    patientPayerLabel,
    refundForm,
    updateRefund,
    lastRefund,
    handleRefund,
    invoiceSearchQ,
    setInvoiceSearchQ,
    refundInvoices,
    filteredRefunds,
    updateRefundStatus,
    printRefundReceipt,
    serviceRequests,
    serviceRequestSearchQ,
    setServiceRequestSearchQ,
    serviceRequestStatusFilter,
    setServiceRequestStatusFilter,
    loadServiceRequests,
    serviceRequestForm,
    setServiceRequestForm,
    serviceRequestExamSearchQ,
    setServiceRequestExamSearchQ,
    filteredServiceRequestLabTests,
    filteredServiceRequestSpecialties,
    filteredServiceRequestImaging,
    filteredServicePrestations,
    filteredSurgicalActs,
    chooseServiceRequest,
    saveServiceRequest,
    editingServiceRequestId,
    resetServiceRequestForm,
    lastCreatedServiceRequest,
    applyServiceRequestToBilling,
    loadingServiceRequests,
    startEditServiceRequest,
    deleteServiceRequest,
    statCards,
    loadQueueBucket,
    activeStatBucket,
    renderQueueTable,
    refresh,
    resolveRelationship,
  };
}
