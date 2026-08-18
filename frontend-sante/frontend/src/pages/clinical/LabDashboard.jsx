import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatApiError } from '../../utils/apiError.js';
import { useClinicalPatientRoute } from '../../hooks/useClinicalPatientRoute.js';
import { detectLabTemplateId, LAB_TEMPLATES, LAB_TEMPLATE_OPTIONS, templateRowsForExam, templateRowsForTemplateId } from '../../data/labReportTemplates.js';
import PatientSafetyStrip from '../../components/clinical/PatientSafetyStrip.jsx';
import PrintClinicHeader from '../../components/print/PrintClinicHeader.jsx';
import PrintDocumentFooter from '../../components/print/PrintDocumentFooter.jsx';
import { formatClinicalDateTime, patientDisplayName } from '../../utils/clinicalPresentation.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import LabPatientOverview, { ReadOnlyDisplay } from './lab/LabPatientOverview.jsx';
import {
  EMPTY_RESULT_ROW,
  nowInputValue,
  ORDER_STATUS_MAP,
  parseLabPayload,
  SAMPLE_TYPES,
  sampleCodesFromLabels,
  todayInputValue,
  VALIDATION_STATUSES,
} from './lab/labDomain.js';
import './clinical.css';
import './lab/lab.css';

const TABS = [
  { id: 'workflow', label: 'Tableau de bord Labo', shortcut: '1' },
];

const STAT_BUCKETS = [
  { key: 'pending', label: 'En attente', variant: 'warning', statKey: 'pending_exams', fallbackKey: 'pending_results' },
  { key: 'sampling', label: 'En prélèvement', variant: 'accent', statKey: 'in_sampling' },
  { key: 'analysis', label: 'En analyse', variant: 'accent', statKey: 'in_analysis' },
  { key: 'validated_today', label: 'Validés aujourd\'hui', variant: 'success', statKey: 'validated_today' },
];

const BUCKET_TITLES = {
  pending: 'Patients en attente',
  sampling: 'Patients en prélèvement',
  analysis: 'Patients en analyse',
  validated_today: 'Examens validés aujourd\'hui',
};

const FormNotice = ({ children }) =>
  children ? <p className="reception-his-form-notice">{children}</p> : null;

export default function LabDashboard() {
  const { user } = useAuth();
  const { patientId: routePatientId, setPatientId: setRoutePatientId } = useClinicalPatientRoute();
  const searchRef = useRef(null);
  const closingPatientIdRef = useRef('');

  const [tab, setTab] = useState('workflow');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [labStats, setLabStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [activeStatBucket, setActiveStatBucket] = useState(null);
  const [queueRows, setQueueRows] = useState([]);
  const [loadingQueue, setLoadingQueue] = useState(false);

  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [serviceRequests, setServiceRequests] = useState([]);

  const [sampleForm, setSampleForm] = useState({
    collection_date: todayInputValue(),
    collection_time: nowInputValue(),
    collector: '',
  });
  const [sampleTypes, setSampleTypes] = useState([]);
  const [sampleOther, setSampleOther] = useState('');

  const [activeOrderId, setActiveOrderId] = useState(null);
  const [resultRows, setResultRows] = useState([{ ...EMPTY_RESULT_ROW }]);
  const [validationForm, setValidationForm] = useState({
    technician: '',
    validation_date: todayInputValue(),
    validation_time: nowInputValue(),
    status: 'pending',
    observations: '',
  });
  const [activeTemplateId, setActiveTemplateId] = useState(null);
  const [lastResultId, setLastResultId] = useState(null);
  const [validationSummary, setValidationSummary] = useState(null);
  const [ecbuMacro, setEcbuMacro] = useState('');
  const [savedSampleInfo, setSavedSampleInfo] = useState(null);

  const load = useCallback(async () => {
    const [queueRes, dashRes] = await Promise.allSettled([
      clinicalApi.labQueue(),
      clinicalApi.labDashboardStats(),
    ]);
    if (queueRes.status === 'fulfilled') setOrders(queueRes.value.data || []);
    if (dashRes.status === 'fulfilled') setLabStats(dashRes.value.data || null);
  }, []);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  useEffect(() => {
    if (!searchQ.trim()) {
      setSearchResults([]);
      return undefined;
    }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await clinicalApi.labPatientSearch(searchQ.trim());
        setSearchResults(data || []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [searchQ]);

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

  useEffect(() => {
    if (!selectedPatient?.id) {
      setServiceRequests([]);
      return undefined;
    }
    let cancelled = false;
    clinicalApi
      .labServiceRequests(selectedPatient.id)
      .then(async ({ data }) => {
        if (!cancelled) {
          setServiceRequests(data || []);
          await load();
        }
      })
      .catch(() => {
        if (!cancelled) setServiceRequests([]);
      });
    return () => {
      cancelled = true;
    };
  }, [load, selectedPatient?.id]);

  const patientOrders = useMemo(() => {
    if (!selectedPatient?.id) return [];
    const fromQueue = orders.filter((o) => o.patient_id === selectedPatient.id);
    const knownIds = new Set(fromQueue.map((o) => o.id));
    const fromRequests = (serviceRequests || [])
      .filter((r) => r.lab_order_id && !knownIds.has(r.lab_order_id))
      .map((r) => ({
        id: r.lab_order_id,
        patient_id: selectedPatient.id,
        test_name: r.exam_name,
        test_code: r.exam_code || '',
        status: 'ordered',
        payment_status: r.payment_status,
      }));
    return [...fromQueue, ...fromRequests];
  }, [orders, selectedPatient?.id, serviceRequests]);

  const actionableOrders = useMemo(
    () => patientOrders.filter((o) => o.status !== 'completed' && o.status !== 'cancelled'),
    [patientOrders],
  );

  const activeOrder = useMemo(() => {
    if (!activeOrderId) return null;
    const fromPatient = patientOrders.find((o) => o.id === activeOrderId);
    if (fromPatient) return fromPatient;
    const fromQueue = orders.find((o) => o.id === activeOrderId);
    if (fromQueue) return fromQueue;
    const req = serviceRequests.find((r) => r.lab_order_id === activeOrderId);
    if (req) {
      return {
        id: activeOrderId,
        test_name: req.exam_name,
        status: 'ordered',
        patient_id: selectedPatient?.id,
      };
    }
    return null;
  }, [orders, activeOrderId, serviceRequests, selectedPatient?.id, patientOrders]);

  const stats = useMemo(() => {
    if (!labStats) {
      return [{ key: 'pending', label: 'Examens en cours', value: orders.length, variant: 'accent' }];
    }
    return STAT_BUCKETS.map((bucket) => ({
      key: bucket.key,
      label: bucket.label,
      variant: bucket.variant,
      value: labStats[bucket.statKey] ?? (bucket.fallbackKey ? labStats[bucket.fallbackKey] : 0) ?? 0,
    }));
  }, [labStats, orders.length]);

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
      const { data } = await clinicalApi.labQueueByStatus(bucket);
      setQueueRows(data || []);
    } catch (err) {
      setQueueRows([]);
      setError(formatApiError(err, 'Impossible de charger la file d\'attente'));
    } finally {
      setLoadingQueue(false);
    }
  };

  const selectPatient = useCallback(async (p) => {
    if (!p?.id) return;
    let patient = p;
    try {
      const { data } = await clinicalApi.labGetPatient(p.id);
      if (data?.id) patient = data;
    } catch {
      /* keep search payload */
    }
    setSelectedPatient(patient);
    closingPatientIdRef.current = '';
    setRoutePatientId(patient.id);
    setSearchQ('');
    setSearchResults([]);
    setActiveOrderId(null);
    setActiveTemplateId(null);
    setSavedSampleInfo(null);
    setValidationSummary(null);
    setSampleTypes([]);
    setSampleOther('');
    setMessage(`Patient sélectionné : ${patientDisplayName(patient)} · N° ${patient.patient_number || patient.id}`);
    setError('');
  }, [setRoutePatientId]);

  const clearPatient = () => {
    closingPatientIdRef.current = String(selectedPatient?.id || routePatientId || '');
    setSelectedPatient(null);
    setRoutePatientId('');
    setServiceRequests([]);
    setActiveOrderId(null);
    setResultRows([{ ...EMPTY_RESULT_ROW }]);
    setActiveTemplateId(null);
    setValidationSummary(null);
    setSavedSampleInfo(null);
    setEcbuMacro('');
  };

  useEffect(() => {
    if (!routePatientId) {
      closingPatientIdRef.current = '';
      return;
    }
    if (closingPatientIdRef.current === routePatientId || String(selectedPatient?.id || '') === routePatientId) return;
    void selectPatient({ id: routePatientId });
  }, [routePatientId, selectPatient, selectedPatient?.id]);

  const hydrateSampleFromOrder = useCallback((order) => {
    const parsed = parseLabPayload(order?.clinical_notes);
    if (!parsed) {
      setSavedSampleInfo(null);
      return;
    }
    setSavedSampleInfo(parsed);
    setSampleForm({
      collection_date: parsed.collection_date || todayInputValue(),
      collection_time: parsed.collection_time || nowInputValue(),
      collector: parsed.collector || '',
    });
    const codes = sampleCodesFromLabels(parsed.sample_types || []);
    setSampleTypes(codes);
    setSampleOther(parsed.sample_other || '');
  }, []);

  const hydrateResultsFromOrder = useCallback((order) => {
    const payload = parseLabPayload(order?.result_data);
    if (!payload?.rows?.length) return false;
    setActiveTemplateId(payload.template_id || detectLabTemplateId(order.test_name));
    setResultRows(payload.rows);
    setEcbuMacro(payload.macro_appearance || '');
    if (payload.validation) {
      setValidationForm((prev) => ({ ...prev, ...payload.validation }));
    }
    if (order.latest_result_id) setLastResultId(order.latest_result_id);
    if (order.result_status === 'validated') {
      setValidationSummary({
        patient: patientDisplayName(selectedPatient),
        patientNumber: selectedPatient?.patient_number || selectedPatient?.id,
        exam: order.test_name,
        rows: payload.rows,
        technician: payload.validation?.technician || order.technician_name || '—',
        date: payload.validation?.validation_date || todayInputValue(),
        time: payload.validation?.validation_time || nowInputValue(),
        status: 'Validé',
        macro: payload.macro_appearance || '',
      });
    }
    return true;
  }, [selectedPatient]);

  const pickOrderForTemplate = (templateId) => {
    if (!actionableOrders.length) return null;
    if (templateId) {
      const match = actionableOrders.find((o) => detectLabTemplateId(o.test_name) === templateId);
      if (match) return match;
    }
    return actionableOrders[0];
  };

  const ensureActiveOrder = (templateId = null) => {
    if (activeOrderId && activeOrder) return activeOrder;
    const pick = pickOrderForTemplate(templateId);
    if (!pick) return null;
    setActiveOrderId(pick.id);
    hydrateSampleFromOrder(pick);
    return pick;
  };

  const selectOrder = useCallback((order) => {
    if (!order?.id) return;
    setActiveOrderId(order.id);
    setValidationSummary(null);
    hydrateSampleFromOrder(order);
    const hasSavedResults = hydrateResultsFromOrder(order);
    if (!hasSavedResults) {
      const templateId = detectLabTemplateId(order.test_name);
      setActiveTemplateId(templateId);
      setResultRows(templateId ? templateRowsForTemplateId(templateId) : templateRowsForExam(order.test_name));
      setEcbuMacro('');
      setLastResultId(null);
    }
    const status =
      order.status === 'completed'
        ? 'validated'
        : order.status === 'in_analysis'
          ? 'in_progress'
          : order.status === 'cancelled'
            ? 'rejected'
            : 'pending';
    setValidationForm((p) => ({
      ...p,
      technician: order.technician_name || p.technician || '',
      status,
      validation_date: todayInputValue(),
      validation_time: nowInputValue(),
    }));
    setMessage(`Examen actif : ${order.test_name}`);
    setError('');
  }, [hydrateResultsFromOrder, hydrateSampleFromOrder]);

  useEffect(() => {
    if (!selectedPatient?.id || activeOrderId) return undefined;
    if (actionableOrders.length > 0) {
      selectOrder(actionableOrders[0]);
    }
    return undefined;
  }, [selectedPatient?.id, actionableOrders, activeOrderId, selectOrder]);

  const toggleSampleType = (code) => {
    setSampleTypes((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  };

  const buildSampleNotes = () => JSON.stringify({
    sample_types: sampleTypes.map((c) => SAMPLE_TYPES.find((s) => s.code === c)?.label || c),
    sample_other: sampleTypes.includes('other') ? sampleOther.trim() : '',
    collection_date: sampleForm.collection_date,
    collection_time: sampleForm.collection_time,
    collector: sampleForm.collector,
  });

  const saveSampleCollection = async () => {
    const order = ensureActiveOrder() || activeOrder;
    if (!order?.id) {
      setError('Aucun examen laboratoire en cours. Facturez d\'abord l\'examen à la réception.');
      return;
    }
    if (sampleTypes.length === 0) {
      setError('Sélectionnez au moins un type d\'échantillon.');
      return;
    }
    if (sampleTypes.includes('other') && !sampleOther.trim()) {
      setError('Précisez le type d\'échantillon « Autre ».');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const notes = buildSampleNotes();
      const { data } = await clinicalApi.updateLabOrder(order.id, {
        status: 'sample_collected',
        clinical_notes: notes,
      });
      const snapshot = parseLabPayload(notes);
      setSavedSampleInfo(snapshot);
      setActiveOrderId(order.id);
      setMessage('Prélèvement enregistré.');
      await load();
      if (data?.clinical_notes) hydrateSampleFromOrder(data);
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement du prélèvement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const addResultRow = () => setResultRows((rows) => [...rows, { ...EMPTY_RESULT_ROW }]);
  const updateResultRow = (idx, field, value) => {
    setResultRows((rows) => rows.map((r, i) => (i === idx ? { ...r, [field]: value } : r)));
  };
  const removeResultRow = (idx) => {
    setResultRows((rows) => (rows.length <= 1 ? rows : rows.filter((_, i) => i !== idx)));
  };

  const applyLabTemplate = (templateId) => {
    if (!templateId) return;
    if (!selectedPatient) {
      setError('Sélectionnez d\'abord un patient.');
      return;
    }
    const order = ensureActiveOrder(templateId);
    setActiveTemplateId(templateId);
    setResultRows(templateRowsForTemplateId(templateId));
    if (templateId === 'ecbu') setEcbuMacro('');
    setMessage(
      order
        ? `Modèle chargé : ${LAB_TEMPLATES[templateId]?.title || templateId}`
        : `Modèle chargé (aperçu) : ${LAB_TEMPLATES[templateId]?.title || templateId} — facturez l'examen à la réception pour enregistrer.`,
    );
    setError(order ? '' : "Aucun examen facturé en cours — le tableau est prêt pour la saisie, mais l'enregistrement nécessite une commande.");
  };

  const printLabReport = async (resultId) => {
    const id = resultId || lastResultId;
    if (!id) {
      setError('Aucun résultat validé à imprimer.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await clinicalApi.downloadLabPdf(id, `lab-result-${id}.pdf`);
      setMessage('Rapport laboratoire téléchargé.');
    } catch (err) {
      setError(formatApiError(err, 'Impression du rapport impossible'));
    } finally {
      setLoading(false);
    }
  };

  const submitResults = async (e) => {
    e?.preventDefault?.();
    const order = ensureActiveOrder(activeTemplateId) || activeOrder;
    if (!order?.id) {
      setError('Aucun examen laboratoire actif. Facturez l\'examen à la réception puis sélectionnez-le dans « Examens à traiter ».');
      return;
    }
    const filledRows = resultRows.filter((r) => r.parameter.trim() || r.result.trim());
    if (filledRows.length === 0) {
      setError('Ajoutez au moins une ligne de résultat.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const summary = filledRows.map((r) => `${r.parameter}: ${r.result}${r.unit ? ` ${r.unit}` : ''}`).join(' · ');
      const refs = filledRows
        .filter((r) => r.reference)
        .map((r) => `${r.parameter} (${r.reference})`)
        .join('; ');
      const referenceRange =
        refs.length > 250 ? `${refs.slice(0, 247)}…` : refs || null;
      const payload = {
        result_summary: summary,
        result_data: JSON.stringify({
          rows: filledRows,
          validation: validationForm,
          template_id: activeTemplateId || detectLabTemplateId(order.test_name),
          ...(activeTemplateId === 'ecbu' && ecbuMacro.trim() ? { macro_appearance: ecbuMacro.trim() } : {}),
        }),
        reference_range: referenceRange,
        interpretation: validationForm.observations || null,
      };
      const orderStatus = ORDER_STATUS_MAP[validationForm.status] || 'in_analysis';
      const patch = {};
      const statusRank = { ordered: 0, sample_collected: 1, in_analysis: 2, completed: 3, cancelled: -1 };
      const currentRank = statusRank[order.status] ?? 0;
      if (validationForm.status === 'validated') {
        if (currentRank < statusRank.in_analysis) {
          patch.status = 'in_analysis';
        }
      } else if (validationForm.status === 'rejected') {
        patch.status = 'cancelled';
      } else if (orderStatus !== order.status && (statusRank[orderStatus] ?? 0) >= currentRank) {
        patch.status = orderStatus;
      }
      if (sampleTypes.length > 0) {
        patch.clinical_notes = buildSampleNotes();
      }
      if (Object.keys(patch).length) {
        await clinicalApi.updateLabOrder(order.id, patch);
      }
      if (validationForm.status === 'validated') {
        const { data: result } = await clinicalApi.recordLabResult(order.id, payload);
        await clinicalApi.validateLabResult(result.id);
        setLastResultId(result.id);
        setActiveOrderId(order.id);
        setValidationSummary({
          patient: patientDisplayName(selectedPatient),
          patientNumber: selectedPatient?.patient_number || selectedPatient?.id,
          exam: order.test_name,
          rows: filledRows,
          technician: validationForm.technician || user?.email || '—',
          date: validationForm.validation_date,
          time: validationForm.validation_time,
          status: 'Validé',
          macro: activeTemplateId === 'ecbu' ? ecbuMacro.trim() : '',
          observations: validationForm.observations || '',
        });
        setMessage(`Résultats validés pour ${order.test_name} — vous pouvez imprimer le rapport.`);
      } else if (validationForm.status === 'rejected') {
        setMessage(`Examen rejeté : ${order.test_name}`);
        setActiveOrderId(null);
        setResultRows([{ ...EMPTY_RESULT_ROW }]);
        setActiveTemplateId(null);
      } else {
        const { data: result } = await clinicalApi.recordLabResult(order.id, payload);
        setLastResultId(result.id);
        setActiveOrderId(order.id);
        setMessage(`Résultats enregistrés pour ${order.test_name}`);
      }
      await load();
      if (selectedPatient?.id) {
        const { data } = await clinicalApi.labServiceRequests(selectedPatient.id);
        setServiceRequests(data || []);
      }
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement des résultats impossible'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="clinical-page reception-his lab-his-page" data-testid="lab-dashboard">
      <header className="reception-his-header">
        <div>
          <p className="reception-his-eyebrow">Plateforme Santé · Guinée</p>
          <h1>Tableau de bord — Laboratoire</h1>
          <p className="clinical-lead">
            Examens biologiques, prélèvement et résultats — {user?.clinic_name || 'Clinique'}
          </p>
          <p className="clinical-hint">Le catalogue tarifaire est géré à la Réception (onglet Facturation).</p>
        </div>
        <div className="reception-his-search">
          <label htmlFor="lab-patient-search">
            Recherche patient <span className="reception-his-optional-shortcut">(F3)</span>
          </label>
          <div className="reception-his-search-inline">
            <input
              id="lab-patient-search"
              ref={searchRef}
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="N° dossier, QR code, nom ou téléphone"
              autoComplete="off"
            />
            {searching && <span className="reception-his-optional-shortcut">…</span>}
          </div>
          {searchResults.length > 0 && (
            <ul className="reception-his-search-results" role="listbox">
              {searchResults.map((p) => (
                <li key={p.id}>
                  <button type="button" onClick={() => selectPatient(p)}>
                    <strong>{p.last_name} {p.first_name}</strong>
                    <span>
                      N° {p.patient_number || p.id}
                      {p.phone ? ` · ${p.phone}` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {searchQ.trim() && !searching && searchResults.length === 0 && (
            <p className="reception-his-no-results">Aucun patient trouvé.</p>
          )}
        </div>
      </header>

      <PatientSafetyStrip patient={selectedPatient} onClose={clearPatient} contextLabel="Patient actif au laboratoire" />

      {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
      {message && <p className="clinical-message clinical-message--ok" role="status">{message}</p>}

      <nav className="reception-his-tabs" role="tablist" aria-label="Sections laboratoire">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`reception-his-tab${tab === t.id ? ' reception-his-tab--active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            <kbd>{t.shortcut}</kbd>
          </button>
        ))}
      </nav>

      {tab === 'workflow' && (
        <>
          <ClinicalStatGrid stats={stats} onStatClick={loadQueueBucket} activeKey={activeStatBucket} />

          {activeStatBucket && (
            <section className="lab-his-queue-panel" aria-live="polite">
              <h3>{BUCKET_TITLES[activeStatBucket] || 'File d\'attente'}</h3>
              {loadingQueue ? (
                <p className="clinical-hint">Chargement…</p>
              ) : queueRows.length === 0 ? (
                <p className="clinical-hint">Aucun patient dans cette file.</p>
              ) : (
                <div className="lab-his-results-wrap">
                  <table className="lab-his-queue-table">
                    <thead>
                      <tr>
                        <th>N° dossier</th>
                        <th>Nom</th>
                        <th>Prénom</th>
                        <th>Examens / services demandés</th>
                        {activeStatBucket === 'validated_today' && <th>Résumé des résultats</th>}
                        <th>Statut</th>
                        <th>Date / heure</th>
                      </tr>
                    </thead>
                    <tbody>
                      {queueRows.map((row) => (
                        <tr key={`${row.patient_id}-${row.date_time || row.exams}`}>
                          <td>{row.patient_number || row.patient_id}</td>
                          <td>{row.last_name}</td>
                          <td>{row.first_name}</td>
                          <td>{row.exams}</td>
                          {activeStatBucket === 'validated_today' && (
                            <td className="lab-his-queue-summary">
                              {row.result_summary || '—'}
                              {row.technician ? ` · ${row.technician}` : ''}
                            </td>
                          )}
                          <td>{row.status}</td>
                          <td>{formatClinicalDateTime(row.date_time)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}

          <div className="lab-his-workflow">
            <h2 className="lab-his-workflow-title">Examens biologiques</h2>

            {!selectedPatient ? (
              <section className="lab-his-workflow-card">
                <FormNotice>Recherchez un patient par numéro de dossier ou code QR (enregistré à la réception).</FormNotice>
              </section>
            ) : (
              <>
                <LabPatientOverview patient={selectedPatient} onChangePatient={clearPatient} />

                <section className="lab-his-workflow-card lab-his-workflow-card--exams">
                  <h3>Examens à traiter</h3>
                  <p className="clinical-hint">
                    Commandes laboratoire en cours pour ce patient — sélectionnez un examen pour saisir les résultats.
                  </p>
                  {patientOrders.length === 0 ? (
                    <FormNotice>Aucun examen laboratoire en cours pour ce patient.</FormNotice>
                  ) : (
                    <div className="lab-his-worklist">
                      {patientOrders.map((order) => (
                        <div
                          key={order.id}
                          className={`lab-his-worklist-item${activeOrderId === order.id ? ' lab-his-worklist-item--active' : ''}`}
                        >
                          <span>
                            <strong>{order.test_name}</strong> — {order.status}
                          </span>
                          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectOrder(order)}>
                            Saisir résultats
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section className="lab-his-workflow-card lab-his-workflow-card--sample">
                  <h3>Prélèvement</h3>
                  <div className="reception-his-form-row reception-his-form-row--4">
                    <label>
                      Date de prélèvement
                      <input
                        type="date"
                        value={sampleForm.collection_date}
                        onChange={(e) => setSampleForm((p) => ({ ...p, collection_date: e.target.value }))}
                      />
                    </label>
                    <label>
                      Heure de prélèvement
                      <input
                        type="time"
                        value={sampleForm.collection_time}
                        onChange={(e) => setSampleForm((p) => ({ ...p, collection_time: e.target.value }))}
                      />
                    </label>
                    <label>
                      Agent de prélèvement
                      <input
                        value={sampleForm.collector}
                        onChange={(e) => setSampleForm((p) => ({ ...p, collector: e.target.value }))}
                      />
                    </label>
                  </div>
                  <fieldset className="lab-his-sample-types">
                    <legend>Types d&apos;échantillon</legend>
                    <div className="lab-his-sample-checkboxes" role="group" aria-label="Types d'échantillon">
                      {SAMPLE_TYPES.map((s) => (
                        <label key={s.code} className="lab-his-sample-check">
                          <input
                            type="checkbox"
                            checked={sampleTypes.includes(s.code)}
                            onChange={() => toggleSampleType(s.code)}
                          />
                          {s.label}
                        </label>
                      ))}
                    </div>
                    {sampleTypes.includes('other') && (
                      <label className="lab-his-sample-other">
                        Autre échantillon
                        <input
                          value={sampleOther}
                          onChange={(e) => setSampleOther(e.target.value)}
                          placeholder="ex. Liquide pleural, Liquide ascitique, Salive…"
                        />
                      </label>
                    )}
                  </fieldset>
                  {savedSampleInfo && (
                    <div className="lab-his-saved-sample" aria-live="polite">
                      <strong>Prélèvement enregistré</strong>
                      <p>
                        {(savedSampleInfo.sample_types || []).join(', ') || '—'}
                        {savedSampleInfo.sample_other ? ` · ${savedSampleInfo.sample_other}` : ''}
                      </p>
                      <p className="clinical-hint">
                        {savedSampleInfo.collection_date || '—'} {savedSampleInfo.collection_time || ''}
                        {savedSampleInfo.collector ? ` · ${savedSampleInfo.collector}` : ''}
                      </p>
                    </div>
                  )}
                  <button
                    type="button"
                    className="clinical-btn clinical-btn--secondary"
                    onClick={saveSampleCollection}
                    disabled={loading}
                  >
                    {loading ? 'Enregistrement…' : 'Enregistrer le prélèvement'}
                  </button>
                </section>

                <section className="lab-his-workflow-card lab-his-workflow-card--templates">
                  <h3>Modèles de rapport officiels</h3>
                  <p className="clinical-hint">
                    Sélectionnez le modèle validé par la clinique (Hémogramme, BU ou ECBU). Les paramètres et valeurs de référence se chargent automatiquement.
                  </p>
                  <div className="lab-his-template-picker" role="group" aria-label="Modèles de rapport">
                    {LAB_TEMPLATE_OPTIONS.map((opt) => (
                      <button
                        key={opt.id}
                        type="button"
                        className={`clinical-btn clinical-btn--secondary lab-his-template-btn${activeTemplateId === opt.id ? ' lab-his-template-btn--active' : ''}`}
                        onClick={() => applyLabTemplate(opt.id)}
                        disabled={loading || !selectedPatient}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  {!selectedPatient && (
                    <FormNotice>Sélectionnez d&apos;abord un patient pour charger un modèle.</FormNotice>
                  )}
                  {activeTemplateId === 'ecbu' && (
                    <label className="lab-his-ecbu-macro-field">
                      Aspect macroscopique
                      <textarea
                        rows={2}
                        value={ecbuMacro}
                        onChange={(e) => setEcbuMacro(e.target.value)}
                        placeholder="Saisir l'aspect macroscopique (ex. urine jaune clair, culot léger…)"
                      />
                    </label>
                  )}
                  {activeTemplateId === 'hemogram' && LAB_TEMPLATES.hemogram?.note && (
                    <p className="clinical-hint">{LAB_TEMPLATES.hemogram.note}</p>
                  )}
                </section>

                <section className="lab-his-workflow-card lab-his-workflow-card--results">
                  <h3>Résultats</h3>
                  {activeOrder ? (
                    <p className="clinical-lead lab-his-active-order">
                      Examen actif : <strong>{activeOrder.test_name}</strong>
                      {activeTemplateId && LAB_TEMPLATES[activeTemplateId] ? (
                        <span className="clinical-hint"> · Modèle : {LAB_TEMPLATES[activeTemplateId].title}</span>
                      ) : null}
                    </p>
                  ) : (
                    <p className="clinical-lead lab-his-active-order">Sélectionnez une commande pour saisir les résultats.</p>
                  )}
                  <div className="lab-his-results-wrap">
                    <table className={`lab-his-results-table${activeTemplateId === 'hemogram' ? ' lab-his-results-table--hemogram' : ''}`}>
                      <thead>
                        <tr>
                          <th>Paramètre</th>
                          <th>Résultat</th>
                          {activeTemplateId === 'hemogram' ? (
                            <>
                              <th>Unités</th>
                              <th>Enfant</th>
                              <th>Homme</th>
                              <th>Femme</th>
                            </>
                          ) : activeTemplateId === 'bu' ? (
                            <th>Valeurs de référence</th>
                          ) : (
                            <>
                              <th>Valeurs de référence</th>
                              <th>Unité</th>
                            </>
                          )}
                          <th scope="col">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {resultRows.map((row, idx) => (
                          <tr key={idx}>
                            <td>
                              <input
                                value={row.parameter}
                                onChange={(e) => updateResultRow(idx, 'parameter', e.target.value)}
                                placeholder="ex. Glucose"
                                readOnly={Boolean(activeTemplateId)}
                              />
                            </td>
                            <td>
                              <input
                                value={row.result}
                                onChange={(e) => updateResultRow(idx, 'result', e.target.value)}
                                placeholder="Valeur"
                              />
                            </td>
                            {activeTemplateId === 'hemogram' ? (
                              <>
                                <td><ReadOnlyDisplay value={row.unit} /></td>
                                <td><ReadOnlyDisplay value={row.ref_child} /></td>
                                <td><ReadOnlyDisplay value={row.ref_male} /></td>
                                <td><ReadOnlyDisplay value={row.ref_female} /></td>
                              </>
                            ) : activeTemplateId === 'bu' ? (
                              <>
                                <td>
                                  <input
                                    value={row.reference}
                                    onChange={(e) => updateResultRow(idx, 'reference', e.target.value)}
                                    placeholder="0,7 – 1,1 g/L"
                                    readOnly={Boolean(activeTemplateId)}
                                  />
                                </td>
                              </>
                            ) : (
                              <>
                                <td>
                                  <input
                                    value={row.reference}
                                    onChange={(e) => updateResultRow(idx, 'reference', e.target.value)}
                                    placeholder="0,7 – 1,1 g/L"
                                    readOnly={Boolean(activeTemplateId)}
                                  />
                                </td>
                                <td>
                                  <input
                                    value={row.unit}
                                    onChange={(e) => updateResultRow(idx, 'unit', e.target.value)}
                                    placeholder="g/L"
                                    readOnly={Boolean(activeTemplateId)}
                                  />
                                </td>
                              </>
                            )}
                            <td>
                              {!activeTemplateId && (
                                <button
                                  type="button"
                                  className="clinical-btn clinical-btn--secondary"
                                  onClick={() => removeResultRow(idx)}
                                  aria-label={`Supprimer la ligne de résultat ${idx + 1}`}
                                >
                                  ×
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!activeTemplateId && (
                    <button type="button" className="clinical-btn clinical-btn--secondary lab-his-add-row" onClick={addResultRow}>
                      + Ajouter une ligne
                    </button>
                  )}
                </section>

                <section className="lab-his-workflow-card lab-his-workflow-card--validation">
                  <h3>Validation</h3>
                  <div className="reception-his-form-row reception-his-form-row--3">
                    <label>
                      Biologiste / technicien
                      <input
                        value={validationForm.technician}
                        onChange={(e) => setValidationForm((p) => ({ ...p, technician: e.target.value }))}
                      />
                    </label>
                    <label>
                      Date de validation
                      <input
                        type="date"
                        value={validationForm.validation_date}
                        onChange={(e) => setValidationForm((p) => ({ ...p, validation_date: e.target.value }))}
                      />
                    </label>
                    <label>
                      Heure de validation
                      <input
                        type="time"
                        value={validationForm.validation_time}
                        onChange={(e) => setValidationForm((p) => ({ ...p, validation_time: e.target.value }))}
                      />
                    </label>
                  </div>
                  <div className="lab-his-status-options" role="radiogroup" aria-label="Statut">
                    {VALIDATION_STATUSES.map((s) => (
                      <label key={s.value}>
                        <input
                          type="radio"
                          name="lab-status"
                          checked={validationForm.status === s.value}
                          onChange={() => setValidationForm((p) => ({ ...p, status: s.value }))}
                        />
                        {s.label}
                      </label>
                    ))}
                  </div>
                  <label className="lab-his-notes-field">
                    Observations / notes
                    <textarea
                      rows={3}
                      value={validationForm.observations}
                      onChange={(e) => setValidationForm((p) => ({ ...p, observations: e.target.value }))}
                      placeholder="Notes cliniques, commentaires…"
                    />
                  </label>
                  <div className="lab-his-validation-actions">
                    <button
                      type="button"
                      className="clinical-btn lab-his-workflow-action"
                      onClick={submitResults}
                      disabled={loading}
                    >
                      {loading ? 'Enregistrement…' : 'Enregistrer les résultats'}
                    </button>
                    {lastResultId && (
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => printLabReport(lastResultId)}
                        disabled={loading}
                      >
                        Imprimer le rapport
                      </button>
                    )}
                  </div>
                  {validationSummary && (
                    <section className="lab-his-validation-summary" aria-live="polite">
                      <h4>Résumé de validation</h4>
                      <dl className="lab-his-summary-grid">
                        <div><dt>Patient</dt><dd>{validationSummary.patient} · N° {validationSummary.patientNumber}</dd></div>
                        <div><dt>Examen</dt><dd>{validationSummary.exam}</dd></div>
                        <div><dt>Technicien</dt><dd>{validationSummary.technician}</dd></div>
                        <div><dt>Date</dt><dd>{validationSummary.date} {validationSummary.time}</dd></div>
                        <div><dt>Statut</dt><dd>{validationSummary.status}</dd></div>
                      </dl>
                      {validationSummary.macro ? (
                        <p className="lab-his-summary-macro"><strong>Aspect macroscopique :</strong> {validationSummary.macro}</p>
                      ) : null}
                      {validationSummary.observations ? (
                        <p className="lab-his-summary-macro"><strong>Observations :</strong> {validationSummary.observations}</p>
                      ) : null}
                      <div className="lab-his-results-wrap">
                        <table className="lab-his-results-table">
                          <thead>
                            <tr>
                              <th>Paramètre</th>
                              <th>Résultat</th>
                              <th>Référence</th>
                            </tr>
                          </thead>
                          <tbody>
                            {validationSummary.rows.map((row, idx) => (
                              <tr key={idx}>
                                <td>{row.parameter}</td>
                                <td>{row.result}</td>
                                <td>{row.reference || row.ref_male || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => window.print()}
                      >
                        Imprimer le résumé de validation
                      </button>
                    </section>
                  )}
                  {validationSummary && (
                    <div className="lab-his-validation-summary-print" aria-hidden="true">
                      <PrintClinicHeader documentTitle="Résumé de validation laboratoire" compact />
                      <dl className="lab-his-summary-grid">
                        <div><dt>Patient</dt><dd>{validationSummary.patient} · N° {validationSummary.patientNumber}</dd></div>
                        <div><dt>Examen</dt><dd>{validationSummary.exam}</dd></div>
                        <div><dt>Technicien</dt><dd>{validationSummary.technician}</dd></div>
                        <div><dt>Date / heure</dt><dd>{validationSummary.date} {validationSummary.time}</dd></div>
                        <div><dt>Statut</dt><dd>{validationSummary.status}</dd></div>
                      </dl>
                      {validationSummary.observations ? <p><strong>Observations :</strong> {validationSummary.observations}</p> : null}
                      <table className="lab-his-results-table">
                        <thead><tr><th>Paramètre</th><th>Résultat</th><th>Référence</th></tr></thead>
                        <tbody>
                          {validationSummary.rows.map((row, idx) => (
                            <tr key={idx}>
                              <td>{row.parameter}</td>
                              <td>{row.result}</td>
                              <td>{row.reference || row.ref_male || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <PrintDocumentFooter printedBy={user?.email || ''} department="Laboratoire" />
                    </div>
                  )}
                </section>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
