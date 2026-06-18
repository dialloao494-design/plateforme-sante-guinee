import { useCallback, useEffect, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';

import './clinical.css';

function formatGNF(n) {
  return `${Number(n || 0).toLocaleString('fr-GN')} GNF`;
}

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

export default function ClinicalReportsDashboard() {
  const [range, setRange] = useState(defaultRange);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await clinicalApi.clinicalReportSummary({ start: range.start, end: range.end });
      setSummary(data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Rapports indisponibles');
    }
  }, [range.start, range.end]);

  useEffect(() => {
    load();
  }, [load]);

  const exportCsv = async () => {
    try {
      const { data } = await clinicalApi.downloadClinicalReportCsv({ start: range.start, end: range.end });
      const url = window.URL.createObjectURL(new Blob([data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `rapport-clinique-${range.start}-${range.end}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Export impossible');
    }
  };

  const exportPdf = async () => {
    try {
      await clinicalApi.downloadClinicalReportPdf(
        { start: range.start, end: range.end },
        `rapport-clinique-${range.start}.pdf`
      );
    } catch (err) {
      setError(err?.response?.data?.detail || 'PDF impossible');
    }
  };

  const rev = summary?.revenue;
  const stats = summary
    ? [
        { label: 'Consultations', value: summary.consultations, hint: `${range.start} → ${range.end}` },
        { label: 'Labo', value: summary.lab_orders, hint: 'Commandes' },
        { label: 'Imagerie', value: summary.imaging_orders, hint: 'Examens' },
        { label: 'Recettes', value: formatGNF(rev?.total_collected_gnf), hint: 'Charges + factures', variant: 'success' },
      ]
    : [];

  return (
    <div className="clinical-page">
      <header className="clinical-header">
        <h1>Rapports cliniques</h1>
        <p>Synthèse opérationnelle et financière — export CSV/PDF.</p>
      </header>
      {error && <div className="clinical-alert clinical-alert--error">{String(error)}</div>}
      <ClinicalStatGrid stats={stats} />
      <section className="clinical-panel">
        <div className="clinical-form" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <label>
            Du
            <input type="date" value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} />
          </label>
          <label>
            Au
            <input type="date" value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} />
          </label>
        </div>
        <div className="clinical-actions">
          <button type="button" className="clinical-btn" onClick={exportCsv}>Exporter CSV</button>
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={exportPdf}>Exporter PDF</button>
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={load}>Actualiser</button>
        </div>
        {summary && (
          <ul className="clinical-list">
            <li>RDV: {summary.appointments_total} (complétés {summary.appointments_completed}, annulés {summary.appointments_cancelled})</li>
            <li>Pharmacie délivrée: {summary.pharmacy_dispensed}</li>
            <li>Admissions: {summary.admissions} · Sorties: {summary.discharges}</li>
            <li>Factures payées: {rev?.paid_invoices_count} — {formatGNF(rev?.invoices_paid_gnf)}</li>
            <li>Charges en attente: {rev?.pending_charges_count}</li>
          </ul>
        )}
      </section>
    </div>
  );
}
