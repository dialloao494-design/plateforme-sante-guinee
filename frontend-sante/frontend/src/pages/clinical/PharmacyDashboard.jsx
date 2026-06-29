import { useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import PrintClinicHeader from '../../components/print/PrintClinicHeader.jsx';
import './clinical.css';
import './pharmacy.css';

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

const newLineId = () => `line-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

const emptyLine = () => ({
  id: newLineId(),
  designation: '',
  quantity: '',
  unit_price_gnf: '',
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

const lineTotal = (line) => {
  const qty = Number(line.quantity);
  const unit = Number(line.unit_price_gnf);
  if (!Number.isFinite(qty) || !Number.isFinite(unit) || qty < 1 || unit < 0) return 0;
  return qty * unit;
};

const SearchIcon = () => (
  <svg className="pharmacy-his-search-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path
      fillRule="evenodd"
      d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
      clipRule="evenodd"
    />
  </svg>
);

export default function PharmacyDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);
  const receiptRef = useRef(null);

  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);

  const [lines, setLines] = useState(initialLines);
  const [savedRequest, setSavedRequest] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [amountReceived, setAmountReceived] = useState('');

  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const inventoryByName = useMemo(() => {
    const map = new Map();
    inventory.forEach((item) => {
      if (item.medication_name) map.set(item.medication_name.toLowerCase(), item);
    });
    return map;
  }, [inventory]);

  useEffect(() => {
    clinicalApi.pharmacyInventory().then((r) => setInventory(r.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!searchQ.trim()) {
      setSearchResults([]);
      return undefined;
    }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await clinicalApi.pharmacyPatientSearch(searchQ.trim());
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
      if (e.key === 'F3') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const requestTotal = useMemo(
    () => lines.reduce((sum, line) => sum + lineTotal(line), 0),
    [lines]
  );

  const billingTotal = savedRequest?.total_gnf ?? requestTotal;
  const billingReady = Boolean(savedRequest?.charge_id);
  const receivedNum = Number(amountReceived);
  const remaining = billingReady && Number.isFinite(receivedNum)
    ? Math.max(0, billingTotal - receivedNum)
    : billingReady
      ? billingTotal
      : '';

  const selectPatient = async (p) => {
    if (!p?.id) return;
    let patient = p;
    try {
      const { data } = await clinicalApi.pharmacyGetPatient(p.id);
      if (data?.id) patient = data;
    } catch {
      /* keep search hit */
    }
    setSelectedPatient(patient);
    setSearchQ('');
    setSearchResults([]);
    setSavedRequest(null);
    setAmountReceived('');
    setLines(initialLines());
    setError('');
    setMessage(`Patient sélectionné : ${patient.last_name} ${patient.first_name}`);
  };

  const clearPatient = () => {
    setSelectedPatient(null);
    setSavedRequest(null);
    setAmountReceived('');
    setLines(initialLines());
    setMessage('');
    setError('');
  };

  const runSearch = async () => {
    const q = searchQ.trim();
    if (!q) return;
    setSearching(true);
    try {
      const { data } = await clinicalApi.pharmacyPatientSearch(q);
      setSearchResults(data || []);
      if ((data || []).length === 1) selectPatient(data[0]);
    } catch (err) {
      setError(formatApiError(err, 'Recherche impossible'));
    } finally {
      setSearching(false);
    }
  };

  const updateLine = (id, field, value) => {
    setLines((rows) =>
      rows.map((row) => {
        if (row.id !== id) return row;
        const next = { ...row, [field]: value };
        if (field === 'designation') {
          const hit = inventoryByName.get(String(value).trim().toLowerCase());
          if (hit?.unit_price_gnf != null && hit.unit_price_gnf !== '') {
            next.unit_price_gnf = String(hit.unit_price_gnf);
          }
        }
        return next;
      })
    );
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
      setAmountReceived(String(data.total_gnf || requestTotal));
      setMessage('Demande de service enregistrée.');
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const billPatient = async () => {
    if (!savedRequest?.charge_id) {
      setError('Enregistrez d\'abord la demande de service.');
      return;
    }
    const received = Number(amountReceived);
    if (!Number.isFinite(received) || received < billingTotal) {
      setError('Montant reçu insuffisant.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const { data } = await clinicalApi.payPharmacyServiceCharge(savedRequest.charge_id, {
        payment_method: paymentMethod,
        amount_received_gnf: received,
      });
      setSavedRequest(data);
      setMessage('Paiement enregistré.');
    } catch (err) {
      setError(formatApiError(err, 'Facturation impossible'));
    } finally {
      setLoading(false);
    }
  };

  const printReceipt = () => {
    if (!savedRequest) return;
    window.print();
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

  return (
    <div className="clinical-page reception-his pharmacy-his-page">
      <header className="reception-his-header">
        <div>
          <p className="reception-his-eyebrow">Plateforme Santé · Guinée</p>
          <h1>Tableau de bord Pharmacie</h1>
          <p className="clinical-lead">
            Dispensation · Demande de service · Facturation — {user?.clinic_name || 'Clinique'}
          </p>
          <p className="reception-his-session">Session : {user?.full_name || user?.email || 'Utilisateur'}</p>
        </div>
      </header>

      {selectedPatient && (
        <div className="reception-his-selected">
          Patient actif : <strong>{selectedPatient.last_name} {selectedPatient.first_name}</strong> · N° dossier{' '}
          <strong>{selectedPatient.patient_number || selectedPatient.id}</strong>
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={clearPatient}>
            Effacer
          </button>
        </div>
      )}

      {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
      {message && <p className="clinical-message clinical-message--ok" role="status">{message}</p>}

      <div className="pharmacy-his-workflow">
        <section className="pharmacy-his-workflow-card">
          <h3>Recherche patient</h3>
          <label htmlFor="pharmacy-patient-search">
            Nom / ID / Téléphone / Code QR <span className="reception-his-optional-shortcut">(F3)</span>
          </label>
          <div className="pharmacy-his-search-row">
            <input
              id="pharmacy-patient-search"
              ref={searchRef}
              type="search"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), runSearch())}
              autoComplete="off"
            />
            <button
              type="button"
              className="clinical-btn pharmacy-his-search-btn"
              onClick={runSearch}
              disabled={searching || !searchQ.trim()}
              aria-label="Rechercher"
            >
              <SearchIcon />
              {searching ? '…' : 'Rechercher'}
            </button>
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
          {searchQ.trim() && !searching && searchResults.length === 0 && (
            <p className="reception-his-no-results">Aucun patient trouvé.</p>
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
                      <input
                        list="pharmacy-inventory-list"
                        value={line.designation}
                        onChange={(e) => updateLine(line.id, 'designation', e.target.value)}
                        disabled={!selectedPatient}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min="1"
                        value={line.quantity}
                        onChange={(e) => updateLine(line.id, 'quantity', e.target.value)}
                        disabled={!selectedPatient}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="500"
                        value={line.unit_price_gnf}
                        onChange={(e) => updateLine(line.id, 'unit_price_gnf', e.target.value)}
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
          <datalist id="pharmacy-inventory-list">
            {inventory.map((item) => (
              <option key={item.id} value={item.medication_name} />
            ))}
          </datalist>
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
                  <th>Désignation</th>
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
                      <td>{row.quantity}</td>
                      <td>{formatGNF(row.unit_price_gnf)}</td>
                      <td className="pharmacy-his-total-cell">{formatGNF(row.total_gnf)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="pharmacy-his-table-empty" />
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
                <AmountDisplay amountGnf={billingReady ? billingTotal : ''} />
              </label>
              <label>
                Montant reçu
                <input
                  type="number"
                  min="0"
                  value={amountReceived}
                  onChange={(e) => setAmountReceived(e.target.value)}
                  disabled={!billingReady || savedRequest?.payment_status === 'paid'}
                />
              </label>
              <label>
                Reste à payer
                <AmountDisplay amountGnf={billingReady ? remaining : ''} />
              </label>
            </div>
          </fieldset>

          <fieldset className="reception-his-nested-fieldset">
            <legend>Mode de paiement</legend>
            <PaymentMethodRadios
              name="pharmacy-payment"
              value={paymentMethod}
              onChange={setPaymentMethod}
              methods={PAYMENT_METHODS}
              disabled={!billingReady || savedRequest?.payment_status === 'paid'}
            />
          </fieldset>

          <div className="pharmacy-his-actions">
            <button
              type="button"
              className="clinical-btn pharmacy-his-primary-action"
              onClick={billPatient}
              disabled={loading || !billingReady || savedRequest?.payment_status === 'paid'}
            >
              Facturer le patient
            </button>
            <button
              type="button"
              className="clinical-btn clinical-btn--secondary"
              onClick={printReceipt}
              disabled={!billingReady}
            >
              Imprimer reçu
            </button>
          </div>
        </section>
      </div>

      <div className="pharmacy-his-receipt-print" ref={receiptRef}>
        <PrintClinicHeader />
        <h2>Reçu pharmacie</h2>
        <p>{user?.clinic_name || 'Clinique'}</p>
        {selectedPatient && (
          <p>
            {selectedPatient.last_name} {selectedPatient.first_name} · N°{' '}
            {selectedPatient.patient_number || selectedPatient.id}
          </p>
        )}
        <table>
          <thead>
            <tr>
              <th>Désignation</th>
              <th>Qté</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {billingLines.map((row, idx) => (
              <tr key={idx}>
                <td>{row.product_name}</td>
                <td>{row.quantity}</td>
                <td>{formatGNF(row.total_gnf)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p><strong>Total : {formatGNF(billingTotal)}</strong></p>
        {savedRequest?.payment_status === 'paid' && (
          <p>
            Payé · {PAYMENT_METHODS.find((m) => m.value === savedRequest.payment_method)?.label || savedRequest.payment_method}
          </p>
        )}
      </div>
    </div>
  );
}
