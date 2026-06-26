import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import './clinical.css';

const TABS = [
  { id: 'workflow', label: 'Tableau de bord Labo', shortcut: '1' },
  { id: 'catalog', label: 'Catalogue tarifaire', shortcut: '2' },
];

const SAMPLE_TYPES = ['Sang', 'Urine', 'Selles', 'LCR', 'Écouvillon', 'Autre'];
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

const AmountDisplay = ({ amountGnf }) => {
  const has = amountGnf != null && amountGnf !== '' && !Number.isNaN(Number(amountGnf));
  return <ReadOnlyDisplay value={has ? formatGNF(Number(amountGnf)) : ''} />;
};

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
  const [catalogCategories, setCatalogCategories] = useState([]);
  const [catalogMeta, setCatalogMeta] = useState({ total_categories: 0, total_tests: 0 });
  const [priceEdits, setPriceEdits] = useState({});
  const [savingPrices, setSavingPrices] = useState(false);

  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);

  const [testSearchQ, setTestSearchQ] = useState('');
  const [selectedTests, setSelectedTests] = useState({});
  const [sampleForm, setSampleForm] = useState({
    collection_date: todayStr(),
    collection_time: nowTimeStr(),
    collector: '',
    sample_type: 'Sang',
  });
  const [paymentStatus, setPaymentStatus] = useState('pending');

  const [activeOrderId, setActiveOrderId] = useState(null);
  const [resultRows, setResultRows] = useState([{ ...EMPTY_RESULT_ROW }]);
  const [validationForm, setValidationForm] = useState({
    technician: '',
    validation_date: todayStr(),
    validation_time: nowTimeStr(),
    status: 'pending',
    observations: '',
  });

  const [catalogSearchQ, setCatalogSearchQ] = useState('');

  const load = useCallback(async () => {
    const [queueRes, dashRes, catalogRes] = await Promise.allSettled([
      clinicalApi.labQueue(),
      clinicalApi.labDashboardStats(),
      clinicalApi.labCatalog(),
    ]);
    if (queueRes.status === 'fulfilled') setOrders(queueRes.value.data || []);
    if (dashRes.status === 'fulfilled') setLabStats(dashRes.value.data || null);
    if (catalogRes.status === 'fulfilled') {
      const payload = catalogRes.value.data || {};
      setCatalogCategories(payload.categories || []);
      setCatalogMeta({
        total_categories: payload.total_categories || 0,
        total_tests: payload.total_tests || 0,
      });
      const prices = {};
      (payload.tests || []).forEach((t) => {
        prices[t.code] = t.price_gnf ?? '';
      });
      setPriceEdits(prices);
    }
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
    if (user?.full_name && !validationForm.technician) {
      setValidationForm((p) => ({ ...p, technician: user.full_name }));
    }
    if (user?.full_name && !sampleForm.collector) {
      setSampleForm((p) => ({ ...p, collector: user.full_name }));
    }
  }, [user?.full_name, validationForm.technician, sampleForm.collector]);

  const catalog = useMemo(
    () => catalogCategories.flatMap((c) => (c.tests || []).map((t) => ({ ...t, category_label: c.label }))),
    [catalogCategories]
  );

  const filteredCatalogTests = useMemo(() => {
    const q = testSearchQ.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter(
      (t) =>
        t.name?.toLowerCase().includes(q) ||
        t.code?.toLowerCase().includes(q) ||
        t.category_label?.toLowerCase().includes(q)
    );
  }, [catalog, testSearchQ]);

  const selectedTestsList = useMemo(
    () => catalog.filter((t) => selectedTests[t.code]),
    [catalog, selectedTests]
  );

  const subtotalGnf = useMemo(
    () =>
      selectedTestsList.reduce((sum, t) => {
        const raw = priceEdits[t.code];
        const price = raw === '' || raw == null ? 0 : Number(raw);
        return sum + (Number.isFinite(price) ? price : 0);
      }, 0),
    [selectedTestsList, priceEdits]
  );

  const patientOrders = useMemo(() => {
    if (!selectedPatient?.id) return [];
    return orders.filter((o) => o.patient_id === selectedPatient.id);
  }, [orders, selectedPatient?.id]);

  const activeOrder = useMemo(
    () => patientOrders.find((o) => o.id === activeOrderId) || null,
    [patientOrders, activeOrderId]
  );

  const catalogTableRows = useMemo(() => {
    const q = catalogSearchQ.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter(
      (t) =>
        t.name?.toLowerCase().includes(q) ||
        t.code?.toLowerCase().includes(q) ||
        t.category_label?.toLowerCase().includes(q)
    );
  }, [catalog, catalogSearchQ]);

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
    setSelectedTests({});
    setActiveOrderId(null);
    setResultRows([{ ...EMPTY_RESULT_ROW }]);
  };

  const toggleTest = (code) => {
    setSelectedTests((prev) => ({ ...prev, [code]: !prev[code] }));
  };

  const removeTest = (code) => {
    setSelectedTests((prev) => {
      const next = { ...prev };
      delete next[code];
      return next;
    });
  };

  const addResultRow = () => setResultRows((rows) => [...rows, { ...EMPTY_RESULT_ROW }]);
  const updateResultRow = (idx, field, value) => {
    setResultRows((rows) => rows.map((r, i) => (i === idx ? { ...r, [field]: value } : r)));
  };
  const removeResultRow = (idx) => {
    setResultRows((rows) => (rows.length <= 1 ? rows : rows.filter((_, i) => i !== idx)));
  };

  const selectOrder = (order) => {
    setActiveOrderId(order.id);
    setResultRows([{ ...EMPTY_RESULT_ROW, parameter: order.test_name || '' }]);
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
      status,
      validation_date: todayStr(),
      validation_time: nowTimeStr(),
    }));
  };

  const submitRequest = async (e) => {
    e.preventDefault();
    if (!selectedPatient?.id) {
      setError('Recherchez et sélectionnez un patient enregistré à la réception.');
      return;
    }
    if (selectedTestsList.length === 0) {
      setError('Sélectionnez au moins un examen.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const sampleMeta = JSON.stringify({
        collection_date: sampleForm.collection_date,
        collection_time: sampleForm.collection_time,
        collector: sampleForm.collector,
        sample_type: sampleForm.sample_type,
      });
      const { data } = await clinicalApi.createWalkInLabOrders({
        patient_id: selectedPatient.id,
        payment_status: paymentStatus,
        clinical_notes: sampleMeta,
        tests: selectedTestsList.map((t) => {
          const raw = priceEdits[t.code];
          const parsed = raw === '' || raw == null ? null : Number(raw);
          return {
            test_code: t.code,
            test_name: t.name,
            price_gnf: Number.isFinite(parsed) ? parsed : null,
          };
        }),
      });
      setMessage(
        `${data?.length || selectedTestsList.length} examen(s) enregistré(s) — total ${formatGNF(subtotalGnf)}`
      );
      setSelectedTests({});
      if (data?.[0]?.id) setActiveOrderId(data[0].id);
      await load();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement de la demande impossible'));
    } finally {
      setLoading(false);
    }
  };

  const submitResults = async (e) => {
    e.preventDefault();
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
        result_data: JSON.stringify({ rows: filledRows, validation: validationForm }),
        reference_range: refs || null,
        interpretation: validationForm.observations || null,
      };
      const orderStatus = ORDER_STATUS_MAP[validationForm.status] || 'in_analysis';
      if (orderStatus !== activeOrder.status) {
        await clinicalApi.updateLabOrder(activeOrder.id, { status: orderStatus });
      }
      if (validationForm.status === 'validated') {
        const { data: result } = await clinicalApi.recordLabResult(activeOrder.id, payload);
        await clinicalApi.validateLabResult(result.id);
        setMessage(`Résultats validés pour ${activeOrder.test_name}`);
      } else if (validationForm.status === 'rejected') {
        await clinicalApi.updateLabOrder(activeOrder.id, { status: 'cancelled' });
        setMessage(`Examen rejeté : ${activeOrder.test_name}`);
      } else {
        await clinicalApi.recordLabResult(activeOrder.id, payload);
        setMessage(`Résultats enregistrés pour ${activeOrder.test_name}`);
      }
      setResultRows([{ ...EMPTY_RESULT_ROW }]);
      setActiveOrderId(null);
      await load();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement des résultats impossible'));
    } finally {
      setLoading(false);
    }
  };

  const saveCatalogPrices = async () => {
    setSavingPrices(true);
    try {
      const items = catalog.map((test) => {
        const raw = priceEdits[test.code];
        if (raw === '' || raw == null) return { code: test.code, price_gnf: null };
        const parsed = Number(raw);
        return { code: test.code, price_gnf: Number.isFinite(parsed) ? parsed : null };
      });
      const { data } = await clinicalApi.updateLabCatalogPrices(items);
      setCatalogCategories(data.categories || []);
      setCatalogMeta({
        total_categories: data.total_categories || 0,
        total_tests: data.total_tests || 0,
      });
      const prices = {};
      (data.tests || []).forEach((t) => {
        prices[t.code] = t.price_gnf ?? '';
      });
      setPriceEdits(prices);
      setMessage(`Catalogue mis à jour — ${data.total_tests} examens`);
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement des tarifs impossible'));
    } finally {
      setSavingPrices(false);
    }
  };

  const stats = labStats
    ? [
        { label: 'En attente', value: labStats.pending_exams ?? labStats.pending_results ?? 0, variant: 'warning' },
        { label: 'En prélèvement', value: labStats.in_sampling ?? 0, variant: 'accent' },
        { label: 'En analyse', value: labStats.in_analysis ?? 0, variant: 'accent' },
        { label: 'Validés aujourd\'hui', value: labStats.validated_today ?? 0, variant: 'success' },
        { label: 'Recettes du jour', value: formatGNF(labStats.daily_revenue_gnf || 0), variant: 'success' },
        { label: 'Recettes du mois', value: formatGNF(labStats.monthly_revenue_gnf || 0) },
      ]
    : [{ label: 'Examens en cours', value: orders.length, variant: 'accent' }];

  return (
    <div className="clinical-page reception-his lab-his-page">
      <header className="reception-his-header">
        <div>
          <p className="reception-his-eyebrow">Plateforme Santé · Guinée</p>
          <h1>Tableau de bord — Laboratoire</h1>
          <p className="clinical-lead">
            Examens biologiques, prélèvement, résultats et catalogue tarifaire — {user?.clinic_name || 'Clinique'}
          </p>
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
          <ClinicalStatGrid stats={stats} />

          <section className="reception-his-form-sheet">
            <h2>Examens biologiques</h2>
            {!selectedPatient ? (
              <FormNotice>Recherchez un patient par numéro de dossier ou code QR (enregistré à la réception).</FormNotice>
            ) : (
              <>
                <div className="reception-his-patient-context">
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
                </div>

                <h3>Examens demandés</h3>
                <div className="reception-his-form-row">
                  <label className="clinical-field">
                    Rechercher un examen
                    <input
                      value={testSearchQ}
                      onChange={(e) => setTestSearchQ(e.target.value)}
                      placeholder="Nom ou catégorie (ex. NFS, Glycémie…)"
                    />
                  </label>
                </div>
                <div className="lab-catalog-scroll" style={{ maxHeight: '220px', marginBottom: '0.75rem' }}>
                  <ul className="lab-catalog-list">
                    {filteredCatalogTests.slice(0, 40).map((test) => (
                      <li key={test.code} className="lab-catalog-row">
                        <label className="lab-catalog-check">
                          <input
                            type="checkbox"
                            checked={!!selectedTests[test.code]}
                            onChange={() => toggleTest(test.code)}
                          />
                          <span>{test.name}</span>
                          <small style={{ color: '#64748b' }}>{test.category_label}</small>
                        </label>
                        <span className="lab-catalog-price-label">{formatGNF(priceEdits[test.code] || 0)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                {selectedTestsList.length > 0 && (
                  <ul className="lab-his-selected-tests">
                    {selectedTestsList.map((t) => (
                      <li key={t.code}>
                        <span>{t.name}</span>
                        <span>{formatGNF(priceEdits[t.code] || 0)}</span>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removeTest(t.code)}>
                          Retirer
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

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
                  <label>
                    Type d&apos;échantillon
                    <select
                      value={sampleForm.sample_type}
                      onChange={(e) => setSampleForm((p) => ({ ...p, sample_type: e.target.value }))}
                    >
                      {SAMPLE_TYPES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="lab-his-billing-totals">
                  <label>
                    Sous-total
                    <AmountDisplay amountGnf={subtotalGnf} />
                  </label>
                  <label>
                    Total
                    <AmountDisplay amountGnf={subtotalGnf} />
                  </label>
                  <label>
                    Statut paiement
                    <select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)}>
                      <option value="pending">En attente</option>
                      <option value="paid">Payé</option>
                    </select>
                  </label>
                </div>

                <button
                  type="button"
                  className="clinical-btn"
                  onClick={submitRequest}
                  disabled={loading || selectedTestsList.length === 0}
                  style={{ marginTop: '1rem' }}
                >
                  {loading ? 'Enregistrement…' : 'Enregistrer la demande'}
                </button>

                {patientOrders.length > 0 && (
                  <div className="lab-his-worklist">
                    <h3>Commandes du patient</h3>
                    {patientOrders.map((order) => (
                      <div
                        key={order.id}
                        className={`lab-his-worklist-item${activeOrderId === order.id ? ' lab-his-worklist-item--active' : ''}`}
                      >
                        <span>
                          <strong>{order.test_name}</strong> — {order.status}
                          {order.price_gnf != null && <> · {formatGNF(order.price_gnf)}</>}
                        </span>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => selectOrder(order)}>
                          Saisir résultats
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <h3 style={{ marginTop: '1.5rem' }}>Résultats</h3>
                {activeOrder && (
                  <p className="clinical-lead">Examen actif : <strong>{activeOrder.test_name}</strong></p>
                )}
                <table className="lab-his-results-table">
                  <thead>
                    <tr>
                      <th>Paramètre</th>
                      <th>Résultat</th>
                      <th>Valeurs de référence</th>
                      <th>Unité</th>
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
                          />
                        </td>
                        <td>
                          <input
                            value={row.result}
                            onChange={(e) => updateResultRow(idx, 'result', e.target.value)}
                            placeholder="Valeur"
                          />
                        </td>
                        <td>
                          <input
                            value={row.reference}
                            onChange={(e) => updateResultRow(idx, 'reference', e.target.value)}
                            placeholder="0,7 – 1,1 g/L"
                          />
                        </td>
                        <td>
                          <input
                            value={row.unit}
                            onChange={(e) => updateResultRow(idx, 'unit', e.target.value)}
                            placeholder="g/L"
                          />
                        </td>
                        <td>
                          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removeResultRow(idx)}>
                            ×
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addResultRow} style={{ marginTop: '0.5rem' }}>
                  + Ajouter une ligne
                </button>

                <h3 style={{ marginTop: '1.5rem' }}>Validation</h3>
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
                <label style={{ display: 'block', marginTop: '0.75rem' }}>
                  Observations / notes
                  <textarea
                    rows={3}
                    value={validationForm.observations}
                    onChange={(e) => setValidationForm((p) => ({ ...p, observations: e.target.value }))}
                    placeholder="Notes cliniques, commentaires…"
                  />
                </label>
                <button
                  type="button"
                  className="clinical-btn"
                  onClick={submitResults}
                  disabled={loading || !activeOrder}
                  style={{ marginTop: '1rem' }}
                >
                  {loading ? 'Enregistrement…' : 'Enregistrer les résultats'}
                </button>
              </>
            )}
          </section>
        </>
      )}

      {tab === 'catalog' && (
        <section className="reception-his-form-sheet">
          <div className="lab-catalog-toolbar">
            <div>
              <h2>Catalogue tarifaire laboratoire</h2>
              <p className="clinical-lead">
                {catalogMeta.total_categories} catégories · {catalogMeta.total_tests} analyses (GNF)
              </p>
            </div>
            <button
              type="button"
              className="clinical-btn"
              onClick={saveCatalogPrices}
              disabled={savingPrices || catalog.length === 0}
            >
              {savingPrices ? 'Enregistrement…' : 'Enregistrer les tarifs'}
            </button>
          </div>
          <label className="clinical-field">
            Rechercher une analyse
            <input
              value={catalogSearchQ}
              onChange={(e) => setCatalogSearchQ(e.target.value)}
              placeholder="Nom, code ou catégorie…"
            />
          </label>
          <div className="lab-his-catalog-scroll">
            <table className="lab-his-catalog-table">
              <thead>
                <tr>
                  <th>Analyse</th>
                  <th>Catégorie</th>
                  <th>Prix (GNF)</th>
                </tr>
              </thead>
              <tbody>
                {catalogTableRows.map((test) => (
                  <tr key={test.code}>
                    <td>{test.name}</td>
                    <td>{test.category_label}</td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="500"
                        value={priceEdits[test.code] ?? ''}
                        onChange={(e) => setPriceEdits((p) => ({ ...p, [test.code]: e.target.value }))}
                        style={{ width: '120px' }}
                      />
                    </td>
                  </tr>
                ))}
                {catalogTableRows.length === 0 && (
                  <tr>
                    <td colSpan={3} className="reception-his-empty-row">Aucune analyse trouvée.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
