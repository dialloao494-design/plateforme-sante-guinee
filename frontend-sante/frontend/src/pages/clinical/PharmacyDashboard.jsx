import { useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import './clinical.css';
import './pharmacy.css';

const PAYMENT_METHODS = [
  { value: 'cash', label: 'Espèces' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'bank_transfer', label: 'Virement' },
  { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance', label: 'Assurance' },
];

const newLineId = () => `line-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

const emptyLine = () => ({
  id: newLineId(),
  designation: '',
  quantity: 1,
  unit_price_gnf: '',
});

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

const lineTotal = (line) => {
  const qty = Number(line.quantity);
  const unit = Number(line.unit_price_gnf);
  if (!Number.isFinite(qty) || !Number.isFinite(unit) || qty < 1 || unit < 0) return 0;
  return qty * unit;
};

export default function PharmacyDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);
  const receiptRef = useRef(null);

  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);

  const [lines, setLines] = useState([emptyLine()]);
  const [savedRequest, setSavedRequest] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [amountReceived, setAmountReceived] = useState('');

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

  const requestTotal = useMemo(
    () => lines.reduce((sum, line) => sum + lineTotal(line), 0),
    [lines]
  );

  const billingTotal = savedRequest?.total_gnf ?? requestTotal;
  const receivedNum = Number(amountReceived);
  const remaining = Number.isFinite(receivedNum)
    ? Math.max(0, billingTotal - receivedNum)
    : billingTotal;

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
    setError('');
    setMessage(`Patient sélectionné : ${patient.last_name} ${patient.first_name}`);
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
    setLines((rows) => rows.map((row) => (row.id === id ? { ...row, [field]: value } : row)));
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
          quantity: Number(l.quantity) || 1,
          unit_price_gnf: Number(l.unit_price_gnf) || 0,
          total_gnf: lineTotal(l),
        }));

  return (
    <div className="clinical-page reception-his pharmacy-his-page">
      <header className="reception-his-header pharmacy-his-header">
        <div>
          <p className="reception-his-eyebrow">Plateforme Santé · Guinée</p>
          <h1>Tableau de bord Pharmacie</h1>
          <p className="clinical-lead">{user?.clinic_name || 'Clinique'}</p>
        </div>
      </header>

      {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
      {message && <p className="clinical-message clinical-message--ok" role="status">{message}</p>}

      <section className="pharmacy-his-card">
        <h2>Recherche patient</h2>
        <label htmlFor="pharmacy-patient-search">Nom / ID / Téléphone / Code QR</label>
        <div className="pharmacy-his-search-row">
          <input
            id="pharmacy-patient-search"
            ref={searchRef}
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), runSearch())}
          />
          <button type="button" className="clinical-btn" onClick={runSearch} disabled={searching}>
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

      {selectedPatient && (
        <section className="pharmacy-his-card pharmacy-his-card--patient reception-his-patient-context reception-his-patient-context--active">
          <h2>Informations patient</h2>
          <div className="reception-his-form-row reception-his-form-row--4">
            <DisplayField label="N° dossier" value={selectedPatient.patient_number || String(selectedPatient.id)} />
            <DisplayField label="Nom" value={selectedPatient.last_name} />
            <DisplayField label="Prénom" value={selectedPatient.first_name} />
            <DisplayField label="Âge" value={calcAge(selectedPatient.date_of_birth) || String(selectedPatient.age || '')} />
          </div>
          <div className="reception-his-form-row reception-his-form-row--3">
            <DisplayField label="Sexe" value={genderLabel(selectedPatient.gender)} />
            <DisplayField label="Téléphone" value={selectedPatient.phone} />
            <DisplayField
              label="Adresse"
              value={[selectedPatient.address || selectedPatient.quartier, selectedPatient.city].filter(Boolean).join(', ')}
            />
          </div>
        </section>
      )}

      <section className="pharmacy-his-card">
        <h2>Demande de service</h2>
        <div className="pharmacy-his-table-wrap">
          <table className="pharmacy-his-table">
            <thead>
              <tr>
                <th>Produit / Désignation</th>
                <th>Quantité</th>
                <th>Prix unitaire</th>
                <th>Total</th>
                <th />
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
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="1"
                      value={line.quantity}
                      onChange={(e) => updateLine(line.id, 'quantity', e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      step="500"
                      value={line.unit_price_gnf}
                      onChange={(e) => updateLine(line.id, 'unit_price_gnf', e.target.value)}
                    />
                  </td>
                  <td className="pharmacy-his-total-cell">{formatGNF(lineTotal(line))}</td>
                  <td>
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removeLine(line.id)}>
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
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addLine}>
            + Ligne
          </button>
          <button
            type="button"
            className="clinical-btn"
            onClick={submitRequest}
            disabled={loading || !selectedPatient}
          >
            {loading ? 'Enregistrement…' : 'Enregistrer la demande de service'}
          </button>
        </div>
      </section>

      {savedRequest && (
        <section className="pharmacy-his-card pharmacy-his-card--billing">
          <h2>Facturation</h2>
          <div className="pharmacy-his-table-wrap">
            <table className="pharmacy-his-table">
              <thead>
                <tr>
                  <th>Désignation</th>
                  <th>Qté</th>
                  <th>Prix U</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {billingLines.map((row, idx) => (
                  <tr key={`${row.product_name}-${idx}`}>
                    <td>{row.product_name}</td>
                    <td>{row.quantity}</td>
                    <td>{formatGNF(row.unit_price_gnf)}</td>
                    <td className="pharmacy-his-total-cell">{formatGNF(row.total_gnf)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pharmacy-his-billing-summary">
            <label>
              Montant total
              <ReadOnlyDisplay value={formatGNF(billingTotal)} />
            </label>
            <label>
              Montant reçu
              <input
                type="number"
                min="0"
                value={amountReceived}
                onChange={(e) => setAmountReceived(e.target.value)}
              />
            </label>
            <label>
              Reste à payer
              <ReadOnlyDisplay value={formatGNF(remaining)} />
            </label>
          </div>
          <fieldset className="pharmacy-his-payment-fieldset">
            <legend>Mode de paiement</legend>
            <div className="reception-his-payment-methods">
              {PAYMENT_METHODS.map((m) => (
                <label key={m.value} className="reception-his-payment-option">
                  <input
                    type="radio"
                    name="pharmacy-payment"
                    checked={paymentMethod === m.value}
                    onChange={() => setPaymentMethod(m.value)}
                  />
                  {m.label}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="pharmacy-his-actions">
            <button type="button" className="clinical-btn" onClick={billPatient} disabled={loading || savedRequest.payment_status === 'paid'}>
              Facturer le patient
            </button>
            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={printReceipt}>
              Imprimer reçu
            </button>
          </div>
        </section>
      )}

      <div className="pharmacy-his-receipt-print" ref={receiptRef}>
        <h2>Reçu pharmacie</h2>
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
          <p>Payé · {PAYMENT_METHODS.find((m) => m.value === savedRequest.payment_method)?.label || savedRequest.payment_method}</p>
        )}
      </div>
    </div>
  );
}
