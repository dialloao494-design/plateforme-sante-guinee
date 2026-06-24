import { useCallback, useEffect, useMemo, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

const STATUS_LABELS = {
  ordered: 'En attente',
  sample_collected: 'Prélèvement',
  in_analysis: 'En analyse',
  completed: 'Terminé',
};

export default function LabDashboard() {
  const [orders, setOrders] = useState([]);
  const [validated, setValidated] = useState([]);
  const [catalogCategories, setCatalogCategories] = useState([]);
  const [catalogMeta, setCatalogMeta] = useState({ total_categories: 0, total_tests: 0 });
  const [priceEdits, setPriceEdits] = useState({});
  const [savingPrices, setSavingPrices] = useState(false);
  const [tab, setTab] = useState('pending');
  const [selected, setSelected] = useState(null);
  const [resultForm, setResultForm] = useState({
    result_summary: '',
    reference_range: '',
    interpretation: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [labStats, setLabStats] = useState(null);
  const [monthlyReport, setMonthlyReport] = useState(null);
  const [reportMonth, setReportMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [patientPanel, setPatientPanel] = useState(null);
  const [requestForm, setRequestForm] = useState({
    patient_id: '',
    payment_status: 'pending',
    selectedTests: {},
  });

  const load = useCallback(async () => {
    const errors = [];
    const [queueRes, dashRes, catalogRes, validatedRes] = await Promise.allSettled([
      clinicalApi.labQueue(),
      clinicalApi.labDashboardStats(),
      clinicalApi.labCatalog(),
      clinicalApi.labValidatedResults(50),
    ]);
    if (queueRes.status === 'fulfilled') {
      setOrders(queueRes.value.data || []);
    } else {
      errors.push('examens en cours');
    }
    if (dashRes.status === 'fulfilled') setLabStats(dashRes.value.data || null);
    else errors.push('statistiques');

    if (catalogRes.status === 'fulfilled') {
      const payload = catalogRes.value.data || {};
      const categories = payload.categories || [];
      const tests = payload.tests || [];
      setCatalogCategories(categories);
      setCatalogMeta({
        total_categories: payload.total_categories || categories.length || 0,
        total_tests: payload.total_tests || tests.length || 0,
      });
      const prices = {};
      tests.forEach((test) => {
        prices[test.code] = test.price_gnf ?? '';
      });
      setPriceEdits(prices);
    } else {
      errors.push('catalogue');
      try {
        const retry = await clinicalApi.labCatalog();
        const payload = retry.data || {};
        const categories = payload.categories || [];
        const tests = payload.tests || [];
        if (categories.length) {
          setCatalogCategories(categories);
          setCatalogMeta({
            total_categories: payload.total_categories || categories.length,
            total_tests: payload.total_tests || tests.length,
          });
          const prices = {};
          tests.forEach((test) => {
            prices[test.code] = test.price_gnf ?? '';
          });
          setPriceEdits(prices);
          errors.splice(errors.indexOf('catalogue'), 1);
        }
      } catch {
        /* keep catalogue error */
      }
    }

    if (validatedRes.status === 'fulfilled') setValidated(validatedRes.value.data || []);
    else errors.push('résultats validés');

    if (errors.length) {
      const firstReject = [queueRes, dashRes, catalogRes, validatedRes].find((r) => r.status === 'rejected');
      setError(formatApiError(firstReject?.reason, `Chargement partiel : ${errors.join(', ')}`));
    } else {
      setError('');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadMonthlyReport = async () => {
    const [year, month] = reportMonth.split('-').map(Number);
    try {
      const { data } = await clinicalApi.labMonthlyReport(year, month);
      setMonthlyReport(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Rapport mensuel indisponible');
    }
  };

  useEffect(() => {
    if (tab === 'report') {
      loadMonthlyReport();
    }
  }, [tab, reportMonth]);

  const catalog = useMemo(
    () => catalogCategories.flatMap((cat) => cat.tests || []),
    [catalogCategories]
  );

  const selectedTestsList = useMemo(
    () => catalog.filter((t) => requestForm.selectedTests[t.code]),
    [catalog, requestForm.selectedTests]
  );

  const totalSelectedPrice = useMemo(
    () => selectedTestsList.reduce((sum, t) => {
      const raw = priceEdits[t.code];
      const price = raw === '' || raw == null ? 0 : Number(raw);
      return sum + (Number.isFinite(price) ? price : 0);
    }, 0),
    [selectedTestsList, priceEdits]
  );

  const applyPatient = (patient) => {
    if (!patient) return;
    setPatientPanel(patient);
    setRequestForm((prev) => ({ ...prev, patient_id: String(patient.id) }));
  };

  const loadPatientById = async (rawId) => {
    const id = String(rawId || '').trim();
    if (!id) {
      setPatientPanel(null);
      return;
    }
    try {
      const { data } = await clinicalApi.searchPatients(id);
      const match = (data || []).find((p) => String(p.id) === id) || (data || [])[0];
      if (match) {
        applyPatient(match);
      } else {
        setPatientPanel(null);
        setError('Patient introuvable pour cet ID');
      }
    } catch (err) {
      setError(formatApiError(err, 'Chargement patient impossible'));
    }
  };

  const searchPatients = async () => {
    if (patientSearch.trim().length < 1) return;
    try {
      const { data } = await clinicalApi.searchPatients(patientSearch.trim());
      setPatientMatches(data || []);
      if ((data || []).length === 1) {
        applyPatient(data[0]);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Recherche impossible');
    }
  };

  const setPriceForTest = (code, value) => {
    setPriceEdits((prev) => ({ ...prev, [code]: value }));
  };

  const saveCatalogPrices = async () => {
    const items = catalog.map((test) => {
      const raw = priceEdits[test.code];
      if (raw === '' || raw == null) {
        return { code: test.code, price_gnf: null };
      }
      const parsed = Number(raw);
      return { code: test.code, price_gnf: Number.isFinite(parsed) ? parsed : null };
    });
    setSavingPrices(true);
    try {
      const { data } = await clinicalApi.updateLabCatalogPrices(items);
      setCatalogCategories(data.categories || []);
      setCatalogMeta({
        total_categories: data.total_categories || 0,
        total_tests: data.total_tests || 0,
      });
      const prices = {};
      (data.tests || []).forEach((test) => {
        prices[test.code] = test.price_gnf ?? '';
      });
      setPriceEdits(prices);
      setMessage(`Tarifs enregistrés — ${data.total_tests} examens · ${data.total_categories} catégories`);
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement des tarifs impossible'));
    } finally {
      setSavingPrices(false);
    }
  };

  const toggleTest = (code) => {
    setRequestForm((prev) => ({
      ...prev,
      selectedTests: { ...prev.selectedTests, [code]: !prev.selectedTests[code] },
    }));
  };

  const submitWalkIn = async (e) => {
    e.preventDefault();
    if (!requestForm.patient_id) {
      setError('Sélectionnez un patient');
      return;
    }
    if (selectedTestsList.length === 0) {
      setError('Sélectionnez au moins un examen du catalogue');
      return;
    }
    try {
      await clinicalApi.createWalkInLabOrders({
        patient_id: Number(requestForm.patient_id),
        payment_status: requestForm.payment_status,
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
      setMessage(`${selectedTestsList.length} examen(s) enregistré(s) — total ${formatGNF(totalSelectedPrice)}`);
      setRequestForm({ patient_id: '', payment_status: 'pending', selectedTests: {} });
      setPatientPanel(null);
      setPatientMatches([]);
      setPatientSearch('');
      load();
      setTab('pending');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Création demande impossible');
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await clinicalApi.updateLabOrder(id, { status });
      setMessage(`Commande #${id} → ${STATUS_LABELS[status] || status}`);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Mise à jour impossible');
    }
  };

  const submitResult = async () => {
    if (!selected) return;
    try {
      const { data } = await clinicalApi.recordLabResult(selected.id, resultForm);
      await clinicalApi.validateLabResult(data.id);
      setMessage(`Résultat validé pour ${selected.test_name}`);
      setSelected(null);
      setResultForm({ result_summary: '', reference_range: '', interpretation: '' });
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Saisie résultat impossible');
    }
  };

  const stats = labStats
    ? [
        { label: 'Examens en attente', value: labStats.pending_exams ?? labStats.pending_results, variant: 'warning' },
        { label: 'En prélèvement', value: labStats.in_sampling ?? 0, variant: 'accent' },
        { label: 'En analyse', value: labStats.in_analysis ?? 0, variant: 'accent' },
        { label: 'Validés aujourd\'hui', value: labStats.validated_today ?? 0, variant: 'success' },
        { label: 'Recettes du jour', value: formatGNF(labStats.daily_revenue_gnf || 0), variant: 'success' },
        { label: 'Recettes du mois', value: formatGNF(labStats.monthly_revenue_gnf || 0) },
      ]
    : [
        { label: 'Examens en cours', value: orders.length, variant: 'accent' },
        { label: 'En prélèvement', value: orders.filter((o) => o.status === 'sample_collected').length },
        { label: 'En analyse', value: orders.filter((o) => o.status === 'in_analysis').length, variant: 'warning' },
        { label: 'Résultats validés', value: validated.length, variant: 'success' },
      ];

  const renderOrderRow = (order) => (
    <li key={order.id}>
      <strong>{order.test_name}</strong> ({order.test_code})
      <br />
      {order.patient_first_name} {order.patient_last_name} · {order.patient_age} ans · {order.patient_gender}
      {order.patient_profession && <> · {order.patient_profession}</>}
      {order.patient_quartier && <> · {order.patient_quartier}</>}
      {order.patient_phone && <> · {order.patient_phone}</>}
      <br />
      {order.price_gnf != null && <>Prix : {formatGNF(order.price_gnf)} · </>}
      Paiement : <span className="clinical-badge">{order.payment_status || '—'}</span>
      {' · '}
      Prélèvement : <span className="clinical-badge">{STATUS_LABELS[order.status] || order.status}</span>
      {order.result_status && (
        <> · Résultat : <span className="clinical-badge">{order.result_status}</span></>
      )}
      {order.validated_at && (
        <> · Validé {new Date(order.validated_at).toLocaleString('fr-FR')}</>
      )}
      {order.technician_name && <> · Tech. {order.technician_name}</>}
      <div className="clinical-actions">
        {order.status === 'ordered' && (
          <button type="button" className="clinical-btn secondary" onClick={() => updateStatus(order.id, 'sample_collected')}>Prélèvement</button>
        )}
        {order.status === 'sample_collected' && (
          <button type="button" className="clinical-btn secondary" onClick={() => updateStatus(order.id, 'in_analysis')}>En analyse</button>
        )}
        <button type="button" className="clinical-btn" onClick={() => setSelected(order)}>Saisir résultat</button>
      </div>
    </li>
  );

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Laboratoire</h1>
      <p className="clinical-lead">Demandes d&apos;examens, catalogue tarifé, prélèvement, résultats et rapports.</p>
      {error && (
        <div className="clinical-retry-bar">
          <p>{String(error)}</p>
          <button type="button" className="clinical-btn" onClick={load}>Réessayer</button>
        </div>
      )}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <DepartmentQueuePanel department="lab" title="File de visite — Laboratoire" />

      <div className="clinical-tabs" role="tablist">
        {[
          ['pending', `En cours (${orders.length})`],
          ['new', 'Nouvelle demande'],
          ['validated', `Validés (${validated.length})`],
          ['report', 'Rapport mensuel'],
        ].map(([key, label]) => (
          <button key={key} type="button" className={`clinical-tab${tab === key ? ' active' : ''}`} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'pending' && (
        <div className="clinical-grid">
          <section className="clinical-card">
            <h2>Examens en cours</h2>
            <ul className="clinical-list">
              {orders.map(renderOrderRow)}
              {orders.length === 0 && <li>Aucun examen en cours.</li>}
            </ul>
          </section>
          {selected && (
            <section className="clinical-card">
              <h2>Saisie résultat — {selected.test_name}</h2>
              <p>{selected.patient_name}</p>
              <div className="clinical-field">
                <label>Résumé</label>
                <textarea rows={3} value={resultForm.result_summary} onChange={(e) => setResultForm({ ...resultForm, result_summary: e.target.value })} required />
              </div>
              <div className="clinical-field">
                <label>Valeurs de référence</label>
                <input value={resultForm.reference_range} onChange={(e) => setResultForm({ ...resultForm, reference_range: e.target.value })} />
              </div>
              <div className="clinical-field">
                <label>Interprétation</label>
                <textarea rows={2} value={resultForm.interpretation} onChange={(e) => setResultForm({ ...resultForm, interpretation: e.target.value })} />
              </div>
              <button type="button" className="clinical-btn" onClick={submitResult}>Valider le résultat</button>
            </section>
          )}
        </div>
      )}

      {tab === 'new' && (
        <section className="clinical-card lab-request-card">
          <h2>Nouvelle demande laboratoire</h2>
          <p className="clinical-lead">
            Catalogue AASMA — {catalogMeta.total_categories} catégories · {catalogMeta.total_tests} examens
          </p>
          <form onSubmit={submitWalkIn}>
            <div className="clinical-card lab-patient-panel">
              <h3>Informations patient</h3>
              <div className="clinical-form-row">
                <div className="clinical-field">
                  <label>Rechercher patient</label>
                  <div className="lab-inline-actions">
                    <input value={patientSearch} onChange={(e) => setPatientSearch(e.target.value)} placeholder="Nom, téléphone ou ID" />
                    <button type="button" className="clinical-btn secondary" onClick={searchPatients}>Rechercher</button>
                  </div>
                  {patientMatches.length > 1 && (
                    <ul className="clinical-list">
                      {patientMatches.map((p) => (
                        <li key={p.id}>
                          <button type="button" className="clinical-btn secondary" onClick={() => applyPatient(p)}>
                            {p.first_name} {p.last_name} #{p.id} {p.phone ? `· ${p.phone}` : ''}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              <div className="clinical-form-row lab-patient-grid">
                <div className="clinical-field">
                  <label>ID Patient</label>
                  <input
                    value={requestForm.patient_id}
                    onChange={(e) => {
                      const value = e.target.value;
                      setRequestForm((prev) => ({ ...prev, patient_id: value }));
                    }}
                    onBlur={() => loadPatientById(requestForm.patient_id)}
                    required
                  />
                </div>
                <div className="clinical-field">
                  <label>Nom</label>
                  <input value={patientPanel?.last_name || ''} readOnly placeholder="—" />
                </div>
                <div className="clinical-field">
                  <label>Prénom</label>
                  <input value={patientPanel?.first_name || ''} readOnly placeholder="—" />
                </div>
                <div className="clinical-field">
                  <label>Âge</label>
                  <input value={patientPanel?.age ?? ''} readOnly placeholder="—" />
                </div>
                <div className="clinical-field">
                  <label>Sexe</label>
                  <input
                    value={patientPanel?.gender === 'F' ? 'Féminin' : patientPanel?.gender === 'M' ? 'Masculin' : patientPanel?.gender || ''}
                    readOnly
                    placeholder="—"
                  />
                </div>
                <div className="clinical-field">
                  <label>Profession</label>
                  <input value={patientPanel?.profession || ''} readOnly placeholder="—" />
                </div>
                <div className="clinical-field">
                  <label>Quartier</label>
                  <input value={patientPanel?.quartier || patientPanel?.address || ''} readOnly placeholder="—" />
                </div>
                <div className="clinical-field">
                  <label>Téléphone</label>
                  <input value={patientPanel?.phone || ''} readOnly placeholder="—" />
                </div>
              </div>
            </div>

            <div className="clinical-field">
              <label>Statut paiement</label>
              <select value={requestForm.payment_status} onChange={(e) => setRequestForm({ ...requestForm, payment_status: e.target.value })}>
                <option value="pending">En attente</option>
                <option value="paid">Payé</option>
              </select>
            </div>

            <div className="lab-catalog-toolbar">
              <h3>Examens par catégorie</h3>
              <button type="button" className="clinical-btn secondary" onClick={saveCatalogPrices} disabled={savingPrices || catalog.length === 0}>
                {savingPrices ? 'Enregistrement…' : 'Enregistrer les tarifs'}
              </button>
            </div>

            {catalogCategories.map((category) => (
              <section key={category.key} className="lab-catalog-category">
                <h4>{category.label}</h4>
                <ul className="lab-catalog-list">
                  {(category.tests || []).map((test) => (
                    <li key={test.code} className="lab-catalog-row">
                      <label className="lab-catalog-check">
                        <input
                          type="checkbox"
                          checked={!!requestForm.selectedTests[test.code]}
                          onChange={() => toggleTest(test.code)}
                        />
                        <span>{test.name}</span>
                      </label>
                      <div className="lab-catalog-price">
                        <input
                          type="number"
                          min="0"
                          step="500"
                          placeholder="Prix GNF"
                          value={priceEdits[test.code] ?? ''}
                          onChange={(e) => setPriceForTest(test.code, e.target.value)}
                        />
                        <span className="lab-catalog-price-label">GNF</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))}

            <p><strong>Total sélectionné : {formatGNF(totalSelectedPrice)}</strong></p>
            <button type="submit" className="clinical-btn">Enregistrer la demande</button>
          </form>
        </section>
      )}

      {tab === 'validated' && (
        <section className="clinical-card">
          <h2>Résultats validés</h2>
          <ul className="clinical-list">
            {validated.length === 0 && <li>Aucun résultat validé.</li>}
            {validated.map((item) => (
              <li key={item.id}>
                <strong>{item.test_name}</strong> ({item.test_code})
                <br />
                {item.patient_name}
                {item.price_gnf != null && <> · {formatGNF(item.price_gnf)}</>}
                {item.payment_status && <> · Paiement {item.payment_status}</>}
                <br />
                {item.result_summary && <span className="clinical-lead">{item.result_summary}</span>}
                <br />
                {item.validated_at && new Date(item.validated_at).toLocaleString('fr-FR')}
                {item.technician_name && <> · {item.technician_name}</>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === 'report' && (
        <section className="clinical-card">
          <div className="clinical-revenue-header">
            <h2>Rapport mensuel laboratoire</h2>
            <input type="month" value={reportMonth} onChange={(e) => setReportMonth(e.target.value)} />
          </div>
          {monthlyReport && (
            <>
              <p>
                {monthlyReport.total_tests} examens · {monthlyReport.completed} terminés · Recettes {formatGNF(monthlyReport.total_revenue_gnf || 0)}
              </p>
              <ul className="clinical-list">
                {(monthlyReport.register_entries || []).map((row) => (
                  <li key={row.order_id}>
                    <strong>{row.test_name}</strong> — {row.patient?.first_name} {row.patient?.last_name}
                    {row.price_gnf != null && <> · {formatGNF(row.price_gnf)}</>}
                    {' · '}{row.payment_status || '—'}
                    {row.validated_at && <> · Validé {new Date(row.validated_at).toLocaleString('fr-FR')}</>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </div>
  );
}
