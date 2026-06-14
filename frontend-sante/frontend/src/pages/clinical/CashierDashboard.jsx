import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import './clinical.css';

const CHARGE_LABELS = {
  consultation: 'Consultations',
  laboratory: 'Laboratoire',
  pharmacy: 'Pharmacie',
};

const METHOD_LABELS = {
  cash: 'Espèces',
  orange_money: 'Orange Money',
  unknown: 'Autre',
};

function chargeTypeLabel(type) {
  if (type === 'consultation') return 'Consultation';
  if (type === 'laboratory') return 'Laboratoire';
  if (type === 'pharmacy') return 'Pharmacie';
  return type;
}

export default function CashierDashboard() {
  const [revenueDate, setRevenueDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [revenue, setRevenue] = useState(null);
  const [pendingCharges, setPendingCharges] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const [rev, charges] = await Promise.all([
        clinicalApi.dailyRevenue(revenueDate),
        clinicalApi.pendingCharges(),
      ]);
      setRevenue(rev.data || null);
      setPendingCharges(charges.data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Impossible de charger la caisse');
    }
  }, [revenueDate]);

  useEffect(() => {
    load();
  }, [load]);

  const handlePay = async (chargeId, method = 'cash') => {
    setError('');
    setMessage('');
    try {
      await clinicalApi.payCharge(chargeId, method);
      setMessage(`Paiement enregistré (#${chargeId})`);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Paiement impossible');
    }
  };

  const byType = revenue?.by_charge_type || {};
  const byMethod = revenue?.by_payment_method || {};

  const stats = revenue
    ? [
        { label: 'Encaissé', value: formatGNF(revenue.total_collected_gnf), variant: 'success' },
        { label: 'En attente', value: formatGNF(revenue.total_pending_gnf), variant: 'warning' },
        { label: 'Factures ouvertes', value: pendingCharges.length, hint: 'À encaisser' },
        { label: 'Date comptable', value: revenue.date, hint: 'Caisse du jour' },
      ]
    : [];

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Caisse</h1>
      <p className="clinical-lead">
        Encaissement des factures et suivi du registre journalier.
      </p>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <section className="clinical-card clinical-revenue-banner">
        <div className="clinical-revenue-header">
          <h2>Caisse du jour</h2>
          <label className="clinical-revenue-date">
            Date
            <input type="date" value={revenueDate} onChange={(e) => setRevenueDate(e.target.value)} />
          </label>
        </div>
        <ClinicalStatGrid stats={stats} />
      </section>

      <section className="clinical-card" style={{ marginTop: '1.25rem' }}>
        <h2>Encaissement — factures en attente</h2>
        <ul className="clinical-list">
          {pendingCharges.length === 0 && <li>Aucune facture en attente.</li>}
          {pendingCharges.map((charge) => (
            <li key={charge.id}>
              <strong>{charge.patient_name || `Patient #${charge.patient_id}`}</strong>
              {' — '}
              {chargeTypeLabel(charge.charge_type)} · {formatGNF(charge.amount_gnf)}
              <br />
              <span className="clinical-badge">{charge.description}</span>
              <div className="clinical-actions">
                <button type="button" className="clinical-btn" onClick={() => handlePay(charge.id, 'cash')}>
                  Encaisser (espèces)
                </button>
                <button
                  type="button"
                  className="clinical-btn clinical-btn--secondary"
                  onClick={() => handlePay(charge.id, 'orange_money')}
                >
                  Orange Money
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {revenue && (
        <div className="clinical-grid">
          <section className="clinical-card">
            <h2>Recettes par service</h2>
            <ul className="clinical-revenue-breakdown">
              {Object.entries(CHARGE_LABELS).map(([key, label]) => (
                <li key={key}>
                  <span>{label}</span>
                  <strong>{formatGNF(byType[key] || 0)}</strong>
                </li>
              ))}
            </ul>
          </section>

          <section className="clinical-card">
            <h2>Modes de paiement</h2>
            <ul className="clinical-revenue-breakdown">
              {Object.keys(byMethod).length === 0 && <li>Aucun paiement enregistré pour cette date.</li>}
              {Object.entries(byMethod).map(([key, amount]) => (
                <li key={key}>
                  <span>{METHOD_LABELS[key] || key}</span>
                  <strong>{formatGNF(amount)}</strong>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
