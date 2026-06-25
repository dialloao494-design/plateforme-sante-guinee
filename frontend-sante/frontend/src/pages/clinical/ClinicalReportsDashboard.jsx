import { useCallback, useEffect, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { AASMA_CLINIC_ID, clinicHasExtendedModules } from '../../utils/clinicModuleConfig.js';

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
  const { user } = useAuth();
  const clinicId = user?.clinic_id;
  const isKoloma = clinicHasExtendedModules(clinicId);
  const isAasma = Number(clinicId) === AASMA_CLINIC_ID;

  const [range, setRange] = useState(defaultRange);
  const [summary, setSummary] = useState(null);
  const [receptionReport, setReceptionReport] = useState(null);
  const [kolomaMonthly, setKolomaMonthly] = useState(null);
  const [reportMonth, setReportMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
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

  const loadReceptionReport = useCallback(async (start, end) => {
    if (!isAasma) {
      setReceptionReport(null);
      return;
    }
    try {
      const { data } = await clinicalApi.receptionHisReport({ start, end });
      setReceptionReport(data);
    } catch {
      setReceptionReport(null);
    }
  }, [isAasma]);

  const loadKolomaMonthly = useCallback(async (year, month) => {
    if (!isKoloma) {
      setKolomaMonthly(null);
      return;
    }
    try {
      const { data } = await clinicalApi.kolomaMonthlyReports(year, month);
      setKolomaMonthly(data);
    } catch {
      setKolomaMonthly(null);
    }
  }, [isKoloma]);

  useEffect(() => {
    load();
    loadReceptionReport(range.start, range.end);
  }, [load, loadReceptionReport, range.start, range.end]);

  useEffect(() => {
    loadKolomaMonthly(reportMonth.year, reportMonth.month);
  }, [reportMonth, loadKolomaMonthly]);

  const exportCsv = async () => {
    try {
      if (isAasma) {
        const { data } = await clinicalApi.receptionHisReportCsv({ start: range.start, end: range.end });
        const url = window.URL.createObjectURL(new Blob([data], { type: 'text/csv' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `rapport-reception-aasma-${range.start}-${range.end}.csv`;
        link.click();
        window.URL.revokeObjectURL(url);
        return;
      }
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
      if (isAasma) {
        const { data } = await clinicalApi.receptionHisReportPdf({ start: range.start, end: range.end });
        const url = window.URL.createObjectURL(data);
        window.open(url, '_blank');
        return;
      }
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
        <p>
          {isAasma
            ? 'Rapports CLINIQUE AASMA — réception, admissions, facturation et remboursements.'
            : 'Synthèse opérationnelle et financière — export CSV/PDF.'}
        </p>
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

      {isAasma && (
        <section className="clinical-panel">
          <h2>Rapport réception — CLINIQUE AASMA</h2>
          <p>Patients enregistrés, admissions, hospitalisations, factures, paiements et remboursements.</p>
          {receptionReport ? (
            <ul className="clinical-list">
              <li>Patients enregistrés: {receptionReport.patients_registered}</li>
              <li>Admissions: {receptionReport.admissions}</li>
              <li>Hospitalisations: {receptionReport.hospitalizations}</li>
              <li>Factures payées: {receptionReport.invoices_paid}</li>
              <li>Factures impayées: {receptionReport.invoices_unpaid}</li>
              <li>Paiements reçus: {formatGNF(receptionReport.payments_received_gnf)}</li>
              <li>Remboursements: {formatGNF(receptionReport.refunds_gnf)}</li>
              <li>Recettes nettes: {formatGNF(receptionReport.net_revenue_gnf)}</li>
              {Object.entries(receptionReport.revenue_by_service || {}).map(([svc, amt]) => (
                <li key={svc}>Recettes {svc}: {formatGNF(amt)}</li>
              ))}
            </ul>
          ) : (
            <p>Chargement du rapport réception…</p>
          )}
        </section>
      )}

      {isKoloma && (
        <section className="clinical-panel">
          <h2>Rapports mensuels Koloma</h2>
          <p>Synthèse PEV, soins, hospitalisation, nutrition, laboratoire et pharmacie.</p>
          <label>
            Mois
            <input
              type="month"
              value={`${reportMonth.year}-${String(reportMonth.month).padStart(2, '0')}`}
              onChange={(e) => {
                const [y, m] = e.target.value.split('-').map(Number);
                setReportMonth({ year: y, month: m });
              }}
            />
          </label>
          {kolomaMonthly && (
            <ul className="clinical-list">
              <li>PEV — vaccinations: {kolomaMonthly.pev?.total_vaccinations ?? '—'}</li>
              <li>Soins infirmiers — procédures: {kolomaMonthly.nursing?.total_procedures ?? '—'}</li>
              <li>Hospitalisation — admissions: {kolomaMonthly.hospitalization?.total_admissions ?? '—'}</li>
              <li>Nutrition — consultations: {kolomaMonthly.nutrition?.total_consultations ?? '—'}</li>
              <li>Laboratoire — examens: {kolomaMonthly.laboratory?.total_tests ?? '—'}</li>
              <li>Pharmacie — délivrances: {kolomaMonthly.pharmacy?.total_dispensed ?? '—'}</li>
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
