import { useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import PrintClinicHeader from '../../components/print/PrintClinicHeader.jsx';
import PharmacyMedicationAutocomplete from './PharmacyMedicationAutocomplete.jsx';
import PharmacyStockTab from './PharmacyStockTab.jsx';
import './clinical.css';
import './pharmacy.css';

const TABS = [
  { id: 'workflow', label: 'Dispensation' },
  { id: 'stock', label: 'Stock' },
];

const PAYMENT_METHODS = [
  { value: 'cash', label: 'Espèces' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'bank_transfer', label: 'Virement' },
  { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance', label: 'Assurance' },
];

const PATIENT_NOTICE = 'Recherchez et sélectionnez un patient enregistré à la réception.';
const BILLING_NOTICE = 'Enregistrez la demande de service pour activer la facturation.';
const INITIAL_ROW_COUNT = 4;
const EMPTY_PAYMENT = { amount_gnf: '', payment_method: 'orange_money', reference: '' };
const newPaymentLineId = () => `pay-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
const emptyPaymentLine = () => ({ id: newPaymentLineId(), amount_gnf: '', payment_method: 'orange_money', reference: '' });

const newLineId = () => `line-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

const emptyLine = () => ({
  id: newLineId(),
  designation: '',
  quantity: '',
  unit_price_gnf: '',
  inventory_item_id: null,
});

const initialLines = () => Array.from({ length: INITIAL_ROW_COUNT }, () => emptyLine());

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

const genderLabel = (g) => {
  if (g === 'F') return 'Féminin';
  if (g === 'M') return 'Masculin';
  return g || '';
};

const patientAge = (patient) => {
  if (!patient) return '';
  if (patient.date_of_birth) return calcAge(patient.date_of_birth);
  if (patient.age != null && patient.age !== '') return String(patient.age);
  return '';
};

const patientAddress = (patient) => {
  if (!patient) return '';
  return [patient.address || patient.quartier, patient.city, patient.region].filter(Boolean).join(', ');
};

const methodLabel = (value) => PAYMENT_METHODS.find((m) => m.value === value)?.label || value || '—';

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

const PaymentMethodRadios = ({ name, value, onChange, methods, disabled }) => (
  <div className="reception-his-payment-methods" role="radiogroup" aria-label="Mode de paiement">
    {methods.map((m) => (
      <label key={m.value} className="reception-his-payment-option">
        <input
          type="radio"
          name={name}
          checked={value === m.value}
          onChange={() => onChange(m.value)}
          disabled={disabled}
        />
        {m.label}
      </label>
    ))}
  </div>
);

// legacy single-payment radios kept for print preview only

const lineTotal = (line) => {
  const qty = Number(line.quantity);
  const unit = Number(line.unit_price_gnf);
  if (!Number.isFinite(qty) || !Number.isFinite(unit) || qty < 1 || unit < 0) return 0;
  return qty * unit;
};

const formatPrintDate = (d = new Date()) => d.toLocaleDateString('fr-FR');
const formatPrintTime = (d = new Date()) => d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

export default function PharmacyDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);
  const receiptRef = useRef(null);

  const [tab, setTab] = useState('workflow');
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [selectedPatient, setSelectedPatient] = useState(null);

  const [lines, setLines] = useState(initialLines);
  const [savedRequest, setSavedRequest] = useState(null);
  const [paymentLines, setPaymentLines] = useState([emptyPaymentLine()]);
  const [exemptionPercent, setExemptionPercent] = useState('0');

  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    clinicalApi.pharmacyInventory().then((r) => setInventory(r.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!searchQ.trim()) {
      setSearchResults([]);
      setSearchError('');
      return undefined;
    }
    const t = setTimeout(async () => {
      setSearching(true);
      setSearchError('');
      try {
        const { data } = await clinicalApi.pharmacyPatientSearch(searchQ.trim());
        setSearchResults(data || []);
        if (!(data || []).length) {
          setSearchError('Aucun patient trouvé.');
        }
      } catch (err) {
        setSearchResults([]);
        setSearchError(formatApiError(err, 'Recherche patient impossible'));
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [searchQ]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'F3') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const updatePaymentLine = (id, patch) =>
    setPaymentLines((rows) => rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  const addPaymentLine = () => setPaymentLines((rows) => [...rows, emptyPaymentLine()]);
  const removePaymentLine = (id) =>
    setPaymentLines((rows) => (rows.length <= 1 ? rows : rows.filter((r) => r.id !== id)));
  const prefillPharmacyPayments = (amount) => {
    const n = Number(amount) || 0;
    setPaymentLines([{ ...emptyPaymentLine(), amount_gnf: n > 0 ? String(n) : '' }]);
  };

  const requestTotal = useMemo(
    () => lines.reduce((sum, line) => sum + lineTotal(line), 0),
    [lines]
  );

  const billingSubtotal = savedRequest?.subtotal_gnf ?? savedRequest?.total_gnf ?? requestTotal;
  const appliedExemptionPercent = savedRequest?.payment_status === 'paid'
    ? Number(savedRequest.exemption_percent || 0)
    : Number(exemptionPercent || 0);
  const billingExemptionAmount = savedRequest?.payment_status === 'paid'
    ? Number(savedRequest.exemption_amount_gnf || 0)
    : Math.round(billingSubtotal * appliedExemptionPercent / 100);
  const billingTotal = savedRequest?.payment_status === 'paid'
    ? Number(savedRequest.total_gnf || 0)
    : Math.max(0, billingSubtotal - billingExemptionAmount);
  const billingReady = Boolean(savedRequest?.charge_id);
  const paymentRows = savedRequest?.payments || [];
  const totalPaid = savedRequest?.paid_amount_gnf ?? paymentRows.reduce((s, p) => s + Number(p.amount_gnf || 0), 0);
  const remaining = billingReady ? Math.max(0, billingTotal - totalPaid) : '';

  const selectPatient = async (p) => {
    if (!p?.id) return;
    let patient = p;
    try {
      const { data } = await clinicalApi.pharmacyGetPatient(p.id);
      if (data?.id) patient = data;
    } catch {
      try {
        const { data } = await clinicalApi.pharmacyPatientSearch(String(p.patient_number || p.id));
        const hit = (data || []).find((row) => row.id === p.id) || data?.[0];
        if (hit?.id) patient = hit;
      } catch {
        /* keep search hit */
      }
    }
    setSelectedPatient(patient);
    setSearchQ('');
    setSearchResults([]);
    setSearchError('');
    setSavedRequest(null);
    prefillPharmacyPayments('');
    setLines(initialLines());
    setError('');
    setMessage(`Patient sélectionné : ${patient.last_name} ${patient.first_name} · N° ${patient.patient_number || patient.id}`);
  };

  const clearPatient = () => {
    setSelectedPatient(null);
    setSavedRequest(null);
    prefillPharmacyPayments('');
    setLines(initialLines());
    setMessage('');
    setError('');
  };

  const updateLine = (id, patch) => {
    setLines((rows) => rows.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  };

  const selectStockItem = (lineId, item) => {
    updateLine(lineId, {
      designation: item.medication_name,
      unit_price_gnf: String(item.unit_price_gnf ?? ''),
      inventory_item_id: item.id,
    });
  };

  const addLine = () => setLines((rows) => [...rows, emptyLine()]);
  const removeLine = (id) => {
    setLines((rows) => (rows.length <= 1 ? rows : rows.filter((r) => r.id !== id)));
  };

  const submitRequest = async () => {
    if (!selectedPatient?.id) {
      setError('Sélectionnez un patient.');
      return;
    }
    const items = lines
      .filter((l) => l.designation.trim())
      .map((l) => ({
        product_name: l.designation.trim(),
        quantity: Number(l.quantity) || 1,
        unit_price_gnf: Number(l.unit_price_gnf) || 0,
        inventory_item_id: l.inventory_item_id || undefined,
      }));
    if (items.length === 0) {
      setError('Ajoutez au moins un produit.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const { data } = await clinicalApi.createPharmacyServiceRequest({
        patient_id: selectedPatient.id,
        items,
      });
      setSavedRequest(data);
      prefillPharmacyPayments(Math.max(0, billingTotal - totalPaid) || data.total_gnf || 0);
      setMessage('Demande de service enregistrée.');
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const draftPaymentTotal = useMemo(
    () => paymentLines.reduce((s, l) => s + (Number(l.amount_gnf) || 0), 0),
    [paymentLines]
  );

  const addPayment = async (e) => {
    e?.preventDefault?.();
    if (!savedRequest?.charge_id) {
      setError('Enregistrez d\'abord la demande de service.');
      return;
    }
    const lines = paymentLines.filter((l) => Number(l.amount_gnf) > 0);
    if (lines.length === 0) {
      setError('Ajoutez au moins une ligne de paiement avec un montant.');
      return;
    }
    const rem = Number(remaining) || 0;
    const draftTotal = lines.reduce((s, l) => s + Number(l.amount_gnf), 0);
    if (draftTotal > rem) {
      setError(`Le total des paiements (${formatGNF(draftTotal)}) dépasse le reste à payer (${formatGNF(rem)}).`);
      return;
    }
    setLoading(true);
    setError('');
    try {
      let lastData = savedRequest;
      for (let i = 0; i < lines.length; i += 1) {
        const line = lines[i];
        const payload = {
          payment_method: line.payment_method,
          amount_gnf: Number(line.amount_gnf),
          reference: line.reference || undefined,
        };
        if (i === 0 && (savedRequest.payments || []).length === 0) {
          payload.exemption_percent = Number(exemptionPercent || 0);
        }
        const { data } = await clinicalApi.addPharmacyChargePayment(savedRequest.charge_id, payload);
        lastData = data || lastData;
      }
      setSavedRequest(lastData);
      const newRem = Math.max(0, billingTotal - (lastData?.paid_amount_gnf ?? 0));
      prefillPharmacyPayments(newRem);
      setMessage(lastData.payment_status === 'paid' ? 'Paiement complet — stock mis à jour.' : 'Paiement(s) enregistré(s).');
      clinicalApi.pharmacyInventory().then((r) => setInventory(r.data || [])).catch(() => {});
    } catch (err) {
      setError(formatApiError(err, 'Paiement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const printReceipt = async () => {
    if (!savedRequest) return;
    if (savedRequest.charge_id) {
      try {
        await printReceiptPdf();
        return;
      } catch {
        /* fall through to browser print */
      }
    }
    window.print();
  };

  const printReceiptPdf = async () => {
    if (!savedRequest?.charge_id) return;
    try {
      const { downloadAuthenticatedPdf } = await import('../../utils/downloadPdf.js');
      await downloadAuthenticatedPdf(
        `/clinical/pharmacy/charges/${savedRequest.charge_id}/receipt`,
        `recu-pharmacie-${savedRequest.charge_id}.pdf`
      );
    } catch {
      setError('Impossible d\'imprimer le reçu PDF.');
    }
  };

  const billingLines = savedRequest?.items?.length
    ? savedRequest.items
    : lines
        .filter((l) => l.designation.trim())
        .map((l) => ({
          product_name: l.designation.trim(),
          quantity: Number(l.quantity) || 0,
          unit_price_gnf: Number(l.unit_price_gnf) || 0,
          total_gnf: lineTotal(l),
        }));

  const printNow = new Date();

  return (
    <div className="clinical-page reception-his pharmacy-his-page" data-testid="pharmacy-dashboard">
      <header className="reception-his-header">
        <div>
          <p className="reception-his-eyebrow">Plateforme Santé · Guinée</p>
          <h1>Tableau de bord Pharmacie</h1>
          <p className="clinical-lead">
            Dispensation · Stock · Facturation — {user?.clinic_name || 'Clinique'}
          </p>
          <p className="reception-his-session">Session : {user?.full_name || user?.email || 'Utilisateur'}</p>
        </div>
      </header>

      <nav className="pharmacy-tabs" role="tablist" aria-label="Sections pharmacie">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            data-testid={`pharmacy-tab-${t.id}`}
            aria-selected={tab === t.id}
            className={`pharmacy-tab${tab === t.id ? ' active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
      {message && <p className="clinical-message clinical-message--ok" role="status">{message}</p>}

      {tab === 'stock' && (
        <PharmacyStockTab onInventoryChange={setInventory} />
      )}

      {tab === 'workflow' && (
        <>
          {selectedPatient && (
            <div className="reception-his-selected">
              Patient actif : <strong>{selectedPatient.last_name} {selectedPatient.first_name}</strong> · N° dossier{' '}
              <strong>{selectedPatient.patient_number || selectedPatient.id}</strong>
              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={clearPatient}>
                Effacer
              </button>
            </div>
          )}

          <div className="pharmacy-his-workflow">
            <section className="pharmacy-his-workflow-card">
              <h3>Recherche patient</h3>
              <label htmlFor="pharmacy-patient-search">
                N° dossier, nom, téléphone ou code QR <span className="reception-his-optional-shortcut">(F3)</span>
              </label>
              <div className="pharmacy-his-search-row pharmacy-his-search-row--auto">
                <input
                  id="pharmacy-patient-search"
                  ref={searchRef}
                  type="text"
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  autoComplete="off"
                  placeholder="N° dossier, nom, téléphone ou code QR…"
                />
                {searching && <span className="reception-his-optional-shortcut">Recherche…</span>}
              </div>
              {searchResults.length > 0 && (
                <ul className="reception-his-search-results reception-his-search-results--inline" role="listbox">
                  {searchResults.map((p) => (
                    <li key={p.id}>
                      <button type="button" onClick={() => selectPatient(p)}>
                        <strong>{p.last_name} {p.first_name}</strong>
                        <span>N° {p.patient_number || p.id}{p.phone ? ` · ${p.phone}` : ''}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {searchError && !searching && (
                <p className="reception-his-no-results">{searchError}</p>
              )}
            </section>

            <section
              className={`pharmacy-his-workflow-card pharmacy-his-workflow-card--patient reception-his-patient-context${selectedPatient ? ' reception-his-patient-context--active' : ''}`}
            >
              <h3>Informations patient</h3>
              {!selectedPatient && <FormNotice>{PATIENT_NOTICE}</FormNotice>}
              <div className="reception-his-form-row reception-his-form-row--4">
                <DisplayField label="N° dossier" value={selectedPatient?.patient_number || (selectedPatient ? String(selectedPatient.id) : '')} />
                <DisplayField label="Nom" value={selectedPatient?.last_name} />
                <DisplayField label="Prénom" value={selectedPatient?.first_name} />
                <DisplayField label="Âge" value={patientAge(selectedPatient)} />
              </div>
              <div className="reception-his-form-row reception-his-form-row--3">
                <DisplayField label="Sexe" value={genderLabel(selectedPatient?.gender)} />
                <DisplayField label="Téléphone" value={selectedPatient?.phone} />
                <DisplayField label="Adresse" value={patientAddress(selectedPatient)} />
              </div>
            </section>

            <section className="pharmacy-his-workflow-card">
              <h3>Demande de service</h3>
              {!selectedPatient && <FormNotice>{PATIENT_NOTICE}</FormNotice>}
              <div className="pharmacy-his-table-wrap">
                <table className="pharmacy-his-table">
                  <thead>
                    <tr>
                      <th>Produit / Désignation</th>
                      <th>Quantité</th>
                      <th>Prix unitaire</th>
                      <th>Total</th>
                      <th aria-label="Actions" />
                    </tr>
                  </thead>
                  <tbody>
                    {lines.map((line) => (
                      <tr key={line.id}>
                        <td>
                          <PharmacyMedicationAutocomplete
                            value={line.designation}
                            onChange={(v) => updateLine(line.id, { designation: v, inventory_item_id: null })}
                            onSelectItem={(item) => selectStockItem(line.id, item)}
                            disabled={!selectedPatient}
                            inventory={inventory}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min="1"
                            value={line.quantity}
                            onChange={(e) => updateLine(line.id, { quantity: e.target.value })}
                            disabled={!selectedPatient}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min="0"
                            step="500"
                            value={line.unit_price_gnf}
                            onChange={(e) => updateLine(line.id, { unit_price_gnf: e.target.value })}
                            disabled={!selectedPatient}
                          />
                        </td>
                        <td className="pharmacy-his-total-cell">{formatGNF(lineTotal(line))}</td>
                        <td>
                          <button
                            type="button"
                            className="clinical-btn clinical-btn--secondary pharmacy-his-row-remove"
                            onClick={() => removeLine(line.id)}
                            disabled={!selectedPatient}
                            aria-label="Supprimer la ligne"
                          >
                            ×
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={3} className="pharmacy-his-foot-label">Total</td>
                      <td colSpan={2} className="pharmacy-his-total-cell">{formatGNF(requestTotal)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div className="pharmacy-his-actions">
                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addLine} disabled={!selectedPatient}>
                  + Ligne
                </button>
                <button
                  type="button"
                  className="clinical-btn pharmacy-his-primary-action"
                  onClick={submitRequest}
                  disabled={loading || !selectedPatient}
                >
                  {loading ? 'Enregistrement…' : 'Enregistrer la demande de service'}
                </button>
              </div>
            </section>

            <section className="pharmacy-his-workflow-card pharmacy-his-workflow-card--billing">
              <h3>Facturation</h3>
              {!billingReady && <FormNotice>{BILLING_NOTICE}</FormNotice>}
              <div className="pharmacy-his-table-wrap">
                <table className="pharmacy-his-table pharmacy-his-table--billing">
                  <thead>
                    <tr>
                      <th>Produit</th>
                      <th>Description</th>
                      <th>Qté</th>
                      <th>Prix U</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {billingLines.length > 0 ? (
                      billingLines.map((row, idx) => (
                        <tr key={`${row.product_name}-${idx}`}>
                          <td>{row.product_name}</td>
                          <td>{row.product_name}</td>
                          <td>{row.quantity}</td>
                          <td>{formatGNF(row.unit_price_gnf)}</td>
                          <td className="pharmacy-his-total-cell">{formatGNF(row.total_gnf ?? row.quantity * row.unit_price_gnf)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="pharmacy-his-table-empty" />
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <fieldset className="reception-his-nested-fieldset">
                <legend>Récapitulatif paiement</legend>
                <div className="pharmacy-his-billing-summary">
                  <label>
                    Montant total
                    <AmountDisplay amountGnf={billingReady ? billingSubtotal : ''} />
                  </label>
                  <label>
                    Exemption (%)
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={savedRequest?.payment_status === 'paid' ? String(savedRequest.exemption_percent || 0) : exemptionPercent}
                      onChange={(e) => setExemptionPercent(e.target.value)}
                      disabled={!billingReady || savedRequest?.payment_status === 'paid' || paymentRows.length > 0}
                    />
                  </label>
                  <label>
                    Montant exemption
                    <AmountDisplay amountGnf={billingReady ? billingExemptionAmount : ''} />
                  </label>
                  <label>
                    Nouveau total
                    <AmountDisplay amountGnf={billingReady ? billingTotal : ''} />
                  </label>
                  <label>
                    Total payé
                    <AmountDisplay amountGnf={billingReady ? totalPaid : ''} />
                  </label>
                  <label>
                    Reste à payer
                    <AmountDisplay amountGnf={billingReady ? remaining : ''} />
                  </label>
                </div>
              </fieldset>

              {billingReady && savedRequest?.payment_status !== 'paid' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Paiements</legend>
                  <p className="clinical-hint">Ajoutez une ou plusieurs lignes de paiement.</p>
                  <table className="reception-his-billing-lines">
                    <thead>
                      <tr>
                        <th>Mode de paiement</th>
                        <th>Montant (GNF)</th>
                        <th>Référence</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {paymentLines.map((line) => (
                        <tr key={line.id}>
                          <td>
                            <select
                              value={line.payment_method}
                              onChange={(e) => updatePaymentLine(line.id, { payment_method: e.target.value })}
                            >
                              {PAYMENT_METHODS.map((m) => (
                                <option key={m.value} value={m.value}>{m.label}</option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              type="number"
                              min="0"
                              value={line.amount_gnf}
                              onChange={(e) => updatePaymentLine(line.id, { amount_gnf: e.target.value })}
                            />
                          </td>
                          <td>
                            <input
                              value={line.reference}
                              onChange={(e) => updatePaymentLine(line.id, { reference: e.target.value })}
                            />
                          </td>
                          <td>
                            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removePaymentLine(line.id)}>×</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {draftPaymentTotal > 0 && (
                    <p className="clinical-hint">Total saisi : {formatGNF(draftPaymentTotal)} · Reste après saisie : {formatGNF(Math.max(0, Number(remaining) - draftPaymentTotal))}</p>
                  )}
                  <div className="pharmacy-his-actions">
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addPaymentLine}>+ Ligne de paiement</button>
                    <button type="button" className="clinical-btn pharmacy-his-primary-action" onClick={addPayment} disabled={loading}>
                      {loading ? 'Enregistrement…' : 'Enregistrer le(s) paiement(s)'}
                    </button>
                  </div>
                </fieldset>
              )}

              {paymentRows.length > 0 && (
                <fieldset className="reception-his-payment-history">
                  <legend>Paiements enregistrés</legend>
                  <table className="pharmacy-his-table">
                    <thead>
                      <tr>
                        <th>Mode</th>
                        <th>Montant</th>
                        <th>Référence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paymentRows.map((p) => (
                        <tr key={p.id}>
                          <td>{methodLabel(p.payment_method)}</td>
                          <td>{formatGNF(p.amount_gnf)}</td>
                          <td>{p.reference || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </fieldset>
              )}

              <div className="pharmacy-his-actions">
                <button
                  type="button"
                  className="clinical-btn clinical-btn--secondary"
                  onClick={printReceipt}
                  disabled={!billingReady}
                >
                  Imprimer reçu
                </button>
                <button
                  type="button"
                  className="clinical-btn clinical-btn--secondary"
                  onClick={printReceiptPdf}
                  disabled={!billingReady}
                >
                  Imprimer PDF (AASMA)
                </button>
              </div>
            </section>
          </div>
        </>
      )}

      <div className="pharmacy-his-receipt-print" ref={receiptRef}>
        <PrintClinicHeader />
        <h2>Reçu pharmacie</h2>
        {selectedPatient && (
          <p className="pharmacy-his-print-patient">
            {selectedPatient.last_name} {selectedPatient.first_name} · N°{' '}
            {selectedPatient.patient_number || selectedPatient.id}
          </p>
        )}
        <table className="pharmacy-his-print-table">
          <thead>
            <tr>
              <th>Produit</th>
              <th>Description</th>
              <th>Qté</th>
              <th>Prix U</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {billingLines.map((row, idx) => (
              <tr key={idx}>
                <td>{row.product_name}</td>
                <td>{row.product_name}</td>
                <td>{row.quantity}</td>
                <td>{formatGNF(row.unit_price_gnf)}</td>
                <td>{formatGNF(row.total_gnf ?? row.quantity * row.unit_price_gnf)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pharmacy-his-print-totals">
          <p><strong>Montant total :</strong> {formatGNF(billingSubtotal)}</p>
          <p><strong>Exemption :</strong> {appliedExemptionPercent}% · {formatGNF(billingExemptionAmount)}</p>
          <p><strong>Nouveau total :</strong> {formatGNF(billingTotal)}</p>
          <p><strong>Montant reçu :</strong> {formatGNF(totalPaid)}</p>
          <p><strong>Reste à payer :</strong> {formatGNF(remaining || 0)}</p>
        </div>
        {paymentRows.length > 0 && (
          <div className="pharmacy-his-print-payments">
            <p><strong>Modes de paiement</strong></p>
            <ul>
              {paymentRows.map((p) => (
                <li key={p.id}>
                  {methodLabel(p.payment_method)} … {formatGNF(p.amount_gnf)}
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="pharmacy-his-print-footer">
          Imprimé par :
          <br />
          {user?.full_name || user?.email || '—'}
          <br />
          {formatPrintDate(printNow)}
          <br />
          {formatPrintTime(printNow)}
          <br />
          Page 1 sur 1
        </p>
      </div>
    </div>
  );
}
