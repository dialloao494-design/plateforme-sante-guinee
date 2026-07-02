import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatApiError } from '../../utils/apiError.js';
import { detectLabTemplateId, LAB_TEMPLATES, LAB_TEMPLATE_OPTIONS, templateRowsForExam, templateRowsForTemplateId } from '../../data/labReportTemplates.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import './clinical.css';

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

const SAMPLE_TYPES = [
  { code: 'blood', label: 'Sang' },
  { code: 'urine', label: 'Urine' },
  { code: 'stool', label: 'Selles' },
  { code: 'lcr', label: 'LCR' },
  { code: 'pus', label: 'Pus' },
  { code: 'other', label: 'Autre' },
];
const VALIDATION_STATUSES = [
  { value: 'pending', label: 'En attente' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'validated', label: 'Validé' },
  { value: 'rejected', label: 'Rejeté' },
];

const ORDER_STATUS_MAP = {
  pending: 'ordered',
  in_progress: 'in_analysis',
  validated: 'completed',
  rejected: 'cancelled',
};

const EMPTY_RESULT_ROW = { parameter: '', result: '', reference: '', unit: '' };

const todayStr = () => new Date().toISOString().slice(0, 10);
const nowTimeStr = () => new Date().toTimeString().slice(0, 5);

const calcAge = (dob) => {
  if (!dob) return '';
  const b = new Date(dob);
  if (Number.isNaN(b.getTime())) return '';
  const n = new Date();
  let age = n.getFullYear() - b.getFullYear();
  const m = n.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && n.getDate() < b.getDate())) age -= 1;
  return age >= 0 ? String(age) : '';
};

const qrImageUrl = (token) =>
  token ? `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(token)}` : '';

const genderLabel = (gender) => {
  if (gender === 'F') return 'Féminin';
  if (gender === 'M') return 'Masculin';
  if (gender === 'Autre') return 'Autre';
  return gender || '';
};

const patientFullName = (p) => (p ? `${p.last_name || ''} ${p.first_name || ''}`.trim() : '');
const patientAge = (p) => {
  if (!p) return '';
  if (p.date_of_birth) return calcAge(p.date_of_birth);
  if (p.age != null && p.age !== '') return String(p.age);
  return '';
};

const formatDob = (dob) => {
  if (!dob) return '';
  try {
    return new Date(dob).toLocaleDateString('fr-FR');
  } catch {
    return String(dob);
  }
};

const formatDateTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return String(value);
  }
};

const ReadOnlyDisplay = ({ value }) => (
  <div
    className={`reception-his-auto-display${value ? ' reception-his-auto-display--filled' : ' reception-his-auto-display--empty'}`}
    aria-live="polite"
  >
    {value || ''}
  </div>
);

const DisplayField = ({ label, value }) => (
  <label>
    {label}
    <ReadOnlyDisplay value={value} />
  </label>
);

const FormNotice = ({ children }) =>
  children ? <p className="reception-his-form-notice">{children}</p> : null;

export default function LabDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);

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
    collection_date: todayStr(),
    collection_time: nowTimeStr(),
    collector: '',
  });
  const [sampleTypes, setSampleTypes] = useState([]);
  const [sampleOther, setSampleOther] = useState('');

  const [activeOrderId, setActiveOrderId] = useState(null);
  const [resultRows, setResultRows] = useState([{ ...EMPTY_RESULT_ROW }]);
  const [validationForm, setValidationForm] = useState({
    technician: '',
    validation_date: todayStr(),
    validation_time: nowTimeStr(),
    status: 'pending',
    observations: '',
  });
  const [activeTemplateId, setActiveTemplateId] = useState(null);
  const [lastResultId, setLastResultId] = useState(null);

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
  }, [selectedPatient?.id]);

  const patientOrders = useMemo(() => {
    if (!selectedPatient?.id) return [];
    return orders.filter((o) => o.patient_id === selectedPatient.id);
  }, [orders, selectedPatient?.id]);

  const activeOrder = useMemo(() => {
    if (!activeOrderId) return null;
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
  }, [orders, activeOrderId, serviceRequests, selectedPatient?.id]);

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

  const selectPatient = async (p) => {
    if (!p?.id) return;
    let patient = p;
    try {
      const { data } = await clinicalApi.labGetPatient(p.id);
      if (data?.id) patient = data;
    } catch {
      /* keep search payload */
    }
    setSelectedPatient(patient);
    setSearchQ('');
    setSearchResults([]);
    setActiveOrderId(null);
    setMessage(`Patient sélectionné : ${patientFullName(patient)} · N° ${patient.patient_number || patient.id}`);
    setError('');
  };

  const clearPatient = () => {
    setSelectedPatient(null);
    setServiceRequests([]);
    setActiveOrderId(null);
    setResultRows([{ ...EMPTY_RESULT_ROW }]);
  };

  const selectOrderById = async (orderId) => {
    let order = orders.find((o) => o.id === orderId) || patientOrders.find((o) => o.id === orderId);
    if (!order) {
      await load();
      order = orders.find((o) => o.id === orderId);
    }
    if (!order) {
      const req = serviceRequests.find((r) => r.lab_order_id === orderId);
      if (req) {
        order = { id: orderId, test_name: req.exam_name, status: 'ordered', patient_id: selectedPatient?.id };
      }
    }
    if (order) {
      selectOrder(order);
    } else {
      setError('Commande laboratoire introuvable. Réessayez après actualisation.');
    }
  };

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
    if (!activeOrder?.id) {
      setError('Sélectionnez une commande avant d\'enregistrer le prélèvement.');
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
      await clinicalApi.updateLabOrder(activeOrder.id, {
        status: 'sample_collected',
        clinical_notes: buildSampleNotes(),
      });
      setMessage('Prélèvement enregistré.');
      await load();
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
    setActiveTemplateId(templateId);
    setResultRows(templateRowsForTemplateId(templateId));
    setMessage(`Modèle chargé : ${LAB_TEMPLATES[templateId]?.title || templateId}`);
    setError('');
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

  const selectOrder = (order) => {
    setActiveOrderId(order.id);
    setLastResultId(null);
    const templateId = detectLabTemplateId(order.test_name);
    setActiveTemplateId(templateId);
    setResultRows(templateRowsForExam(order.test_name));
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
      technician: '',
      status,
      validation_date: todayStr(),
      validation_time: nowTimeStr(),
    }));
  };

  const submitResults = async (e) => {
    e?.preventDefault?.();
    if (!activeOrder) {
      setError('Sélectionnez une commande en cours pour saisir les résultats.');
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
      const payload = {
        result_summary: summary,
        result_data: JSON.stringify({
          rows: filledRows,
          validation: validationForm,
          template_id: activeTemplateId || detectLabTemplateId(activeOrder.test_name),
        }),
        reference_range: refs || null,
        interpretation: validationForm.observations || null,
      };
      const orderStatus = ORDER_STATUS_MAP[validationForm.status] || 'in_analysis';
      const patch = {};
      if (validationForm.status === 'validated') {
        if (activeOrder.status === 'ordered' || activeOrder.status === 'sample_collected') {
          patch.status = 'in_analysis';
        }
      } else if (orderStatus !== activeOrder.status) {
        patch.status = orderStatus;
      }
      if (sampleTypes.length > 0) {
        patch.clinical_notes = buildSampleNotes();
      }
      if (Object.keys(patch).length) {
        await clinicalApi.updateLabOrder(activeOrder.id, patch);
      }
      if (validationForm.status === 'validated') {
        const { data: result } = await clinicalApi.recordLabResult(activeOrder.id, payload);
        await clinicalApi.validateLabResult(result.id);
        setLastResultId(result.id);
        setMessage(`Résultats validés pour ${activeOrder.test_name} — vous pouvez imprimer le rapport.`);
      } else if (validationForm.status === 'rejected') {
        await clinicalApi.updateLabOrder(activeOrder.id, { status: 'cancelled' });
        setMessage(`Examen rejeté : ${activeOrder.test_name}`);
        setActiveOrderId(null);
        setResultRows([{ ...EMPTY_RESULT_ROW }]);
      } else {
        await clinicalApi.recordLabResult(activeOrder.id, payload);
        setMessage(`Résultats enregistrés pour ${activeOrder.test_name}`);
      }
      if (validationForm.status !== 'validated') {
        setResultRows([{ ...EMPTY_RESULT_ROW }]);
        setActiveOrderId(null);
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
    <div className="clinical-page reception-his lab-his-page">
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
                          <td>{row.status}</td>
                          <td>{formatDateTime(row.date_time)}</td>
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
                <section className="lab-his-workflow-card lab-his-workflow-card--patient reception-his-patient-context reception-his-patient-context--active">
                  <h3>Informations patient</h3>
                  <div className="reception-his-form-row reception-his-form-row--4">
                    <DisplayField label="N° dossier" value={selectedPatient.patient_number || String(selectedPatient.id)} />
                    <DisplayField label="Nom" value={selectedPatient.last_name} />
                    <DisplayField label="Prénom" value={selectedPatient.first_name} />
                    <DisplayField label="Date de naissance" value={formatDob(selectedPatient.date_of_birth)} />
                  </div>
                  <div className="reception-his-form-row reception-his-form-row--4">
                    <DisplayField label="Âge" value={patientAge(selectedPatient)} />
                    <DisplayField label="Sexe" value={genderLabel(selectedPatient.gender)} />
                    <DisplayField label="Profession" value={selectedPatient.profession} />
                    <DisplayField label="Téléphone" value={selectedPatient.phone} />
                  </div>
                  <div className="reception-his-form-row reception-his-form-row--4">
                    <DisplayField label="Adresse" value={selectedPatient.address || selectedPatient.quartier} />
                    <DisplayField label="Ville" value={selectedPatient.city} />
                    <DisplayField label="Région" value={selectedPatient.region} />
                    <DisplayField label="Pays" value={selectedPatient.country} />
                  </div>
                  {selectedPatient.qr_token && (
                    <div className="reception-his-qr-block">
                      <img src={qrImageUrl(selectedPatient.qr_token)} alt="QR patient" width={120} height={120} />
                      <DisplayField label="Code QR" value={selectedPatient.qr_token} />
                    </div>
                  )}
                  <button type="button" className="clinical-btn clinical-btn--secondary" onClick={clearPatient}>
                    Changer de patient
                  </button>
                </section>

                <section className="lab-his-workflow-card lab-his-workflow-card--exams">
                  <h3>Demandes de service</h3>
                  <p className="clinical-hint">
                    Examens facturés et validés par la Réception — le laboratoire ne crée ni ne modifie les tarifs.
                  </p>
                  {serviceRequests.length === 0 ? (
                    <FormNotice>Aucune demande de service laboratoire pour ce patient.</FormNotice>
                  ) : (
                    <div className="lab-his-results-wrap">
                      <table className="lab-his-service-table">
                        <thead>
                          <tr>
                            <th>Examen demandé</th>
                            <th>Date de demande</th>
                            <th>Demandé par</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {serviceRequests.map((req) => (
                            <tr key={req.id}>
                              <td>{req.exam_name}</td>
                              <td>{formatDateTime(req.requested_at)}</td>
                              <td>{req.requested_by || 'Réception'}</td>
                              <td>
                                {req.lab_order_id ? (
                                  <button
                                    type="button"
                                    className="clinical-btn clinical-btn--secondary"
                                    onClick={() => selectOrderById(req.lab_order_id)}
                                  >
                                    Saisir résultats
                                  </button>
                                ) : (
                                  <span className="clinical-hint">En attente de paiement</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {patientOrders.length > 0 && (
                    <div className="lab-his-worklist">
                      <h4>Commandes en cours</h4>
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
                  <button
                    type="button"
                    className="clinical-btn clinical-btn--secondary"
                    onClick={saveSampleCollection}
                    disabled={loading || !activeOrder}
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
                        disabled={!activeOrder}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  {!activeOrder && (
                    <FormNotice>Sélectionnez d&apos;abord une demande de service pour activer un modèle.</FormNotice>
                  )}
                  {activeTemplateId === 'ecbu' && LAB_TEMPLATES.ecbu?.macro && (
                    <p className="lab-his-ecbu-macro"><strong>{LAB_TEMPLATES.ecbu.macro}</strong></p>
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
                          ) : (
                            <>
                              <th>Valeurs de référence</th>
                              <th>Unité</th>
                            </>
                          )}
                          <th />
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
                                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removeResultRow(idx)}>
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
                      disabled={loading || !activeOrder}
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
                </section>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
