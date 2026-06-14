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

export default function RevenueDashboard() {
  const [revenueDate, setRevenueDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [revenue, setRevenue] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const { data } = await clinicalApi.dailyRevenue(revenueDate);
      setRevenue(data || null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Impossible de charger les recettes');
    }
  }, [revenueDate]);

  useEffect(() => {
    load();
  }, [load]);

  const byType = revenue?.by_charge_type || {};
  const byMethod = revenue?.by_payment_method || {};

  const stats = revenue
    ? [
        { label: 'Encaissé', value: formatGNF(revenue.total_collected_gnf), variant: 'success' },
        { label: 'En attente', value: formatGNF(revenue.total_pending_gnf), variant: 'warning' },
        { label: 'Paiements', value: `${revenue.paid_count} payés`, hint: `${revenue.pending_count} en attente` },
        { label: 'Date comptable', value: revenue.date, hint: 'Caisse du jour' },
      ]
    : [];

  return (
    <div className="clinical-page">
      <h1>Recettes &amp; caisse</h1>
      <p className="clinical-lead">
        Suivi des encaissements par service — consultations, laboratoire et pharmacie.
      </p>
      {error && <p className="clinical-error">{String(error)}</p>}

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

      <p className="clinical-lead" style={{ marginTop: '1.25rem' }}>
        Rapport de recettes pour la direction — lecture seule.
      </p>
    </div>
  );
}
