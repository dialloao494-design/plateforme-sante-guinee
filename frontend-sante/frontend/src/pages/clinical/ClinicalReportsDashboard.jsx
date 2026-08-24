import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import clinicalApi from '../../services/clinicalApi';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { AASMA_CLINIC_ID, clinicHasExtendedModules } from '../../utils/clinicModuleConfig.js';
import { formatClinicalDate, formatGNF } from '../../utils/clinicalPresentation.js';

import './clinical.css';
import './reports.css';

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const SERVICE_LABELS = { consultation: 'Consultations', laboratory: 'Laboratoire', imaging: 'Imagerie', pharmacy: 'Pharmacie', hospitalization: 'Hospitalisation', nursing: 'Soins infirmiers' };

function toInputDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function rangeEndingToday(days) {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - (days - 1));
  return { start: toInputDate(start), end: toInputDate(end) };
}

function initialRange(searchParams) {
  const start = searchParams.get('start');
  const end = searchParams.get('end');
  return ISO_DATE.test(start || '') && ISO_DATE.test(end || '') ? { start, end } : rangeEndingToday(30);
}

function reportDate(value) { return formatClinicalDate(value ? `${value}T12:00:00` : null); }
function percent(part, total) { return total ? Math.min(100, Math.round((Number(part || 0) / Number(total)) * 100)) : 0; }

function Metric({ label, value, detail, tone = 'neutral' }) {
  return <article className={`reports-metric reports-metric--${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

function LedgerRow({ label, value, emphasis = false }) {
  return <div className={`reports-ledger-row${emphasis ? ' reports-ledger-row--emphasis' : ''}`}><span>{label}</span><strong>{value}</strong></div>;
}

export default function ClinicalReportsDashboard() {
  const { user } = useAuth();
  const clinicId = user?.clinic_id;
  const isKoloma = clinicHasExtendedModules(clinicId);
  const isAasma = Number(clinicId) === AASMA_CLINIC_ID;
  const [searchParams, setSearchParams] = useSearchParams();
  const [range, setRange] = useState(() => initialRange(searchParams));
  const [draftRange, setDraftRange] = useState(() => initialRange(searchParams));
  const [summary, setSummary] = useState(null);
  const [receptionReport, setReceptionReport] = useState(null);
  const [kolomaMonthly, setKolomaMonthly] = useState(null);
  const [reportMonth, setReportMonth] = useState(() => { const now = new Date(); return { year: now.getFullYear(), month: now.getMonth() + 1 }; });
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  const loadReports = useCallback(async (selectedRange) => {
    setLoading(true);
    setError('');
    const requests = [clinicalApi.clinicalReportSummary(selectedRange)];
    if (isAasma) requests.push(clinicalApi.receptionHisReport(selectedRange));
    const results = await Promise.allSettled(requests);
    const summaryResult = results[0];
    if (summaryResult.status === 'fulfilled') setSummary(summaryResult.value.data);
    else setError(summaryResult.reason?.response?.data?.detail || 'Impossible de charger les indicateurs. Vérifiez la connexion puis réessayez.');
    if (isAasma) {
      const receptionResult = results[1];
      if (receptionResult?.status === 'fulfilled') setReceptionReport(receptionResult.value.data);
      else {
        setReceptionReport(null);
        if (summaryResult.status === 'fulfilled') setError('Le rapport de réception est indisponible. Actualisez les données dans quelques instants.');
      }
    }
    if (results.some((result) => result.status === 'fulfilled')) setLastUpdated(new Date());
    setLoading(false);
  }, [isAasma]);

  useEffect(() => { loadReports(range); }, [loadReports, range]);
  useEffect(() => {
    if (!isKoloma) return;
    clinicalApi.kolomaMonthlyReports(reportMonth.year, reportMonth.month).then(({ data }) => setKolomaMonthly(data)).catch(() => setKolomaMonthly(null));
  }, [reportMonth, isKoloma]);

  const applyRange = (nextRange = draftRange) => {
    if (!ISO_DATE.test(nextRange.start) || !ISO_DATE.test(nextRange.end)) return setError('Choisissez une date de début et une date de fin valides.');
    if (nextRange.start > nextRange.end) return setError('La date de début doit précéder la date de fin.');
    setDraftRange(nextRange);
    setSearchParams({ start: nextRange.start, end: nextRange.end }, { replace: true });
    setRange(nextRange);
    setNotice('Période appliquée.');
  };

  const exportReport = async (type) => {
    setExporting(type);
    setError('');
    setNotice('');
    try {
      if (type === 'csv') {
        const response = isAasma ? await clinicalApi.receptionHisReportCsv(range) : await clinicalApi.downloadClinicalReportCsv(range);
        const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `${isAasma ? 'rapport-reception-aasma' : 'rapport-clinique'}-${range.start}-${range.end}.csv`;
        link.click();
        window.URL.revokeObjectURL(url);
      } else if (isAasma) {
        const { data } = await clinicalApi.receptionHisReportPdf(range);
        const url = window.URL.createObjectURL(data);
        window.open(url, '_blank', 'noopener,noreferrer');
        window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
      } else {
        await clinicalApi.downloadClinicalReportPdf(range, `rapport-clinique-${range.start}-${range.end}.pdf`);
      }
      setNotice(`Rapport ${type.toUpperCase()} généré.`);
    } catch (err) {
      setError(err?.response?.data?.detail || `Impossible de générer le rapport ${type.toUpperCase()}. Réessayez.`);
    } finally { setExporting(''); }
  };

  const rev = summary?.revenue;
  const financial = isAasma && receptionReport
    ? { collected: receptionReport.payments_received_gnf, refunds: receptionReport.refunds_gnf, net: receptionReport.net_revenue_gnf, unpaid: receptionReport.invoices_unpaid, paid: receptionReport.invoices_paid }
    : { collected: rev?.total_collected_gnf, refunds: 0, net: rev?.total_collected_gnf, unpaid: rev?.pending_charges_count, paid: rev?.paid_invoices_count };
  const serviceRevenue = useMemo(() => Object.entries(receptionReport?.revenue_by_service || rev?.by_charge_type || {}).sort((a, b) => Number(b[1]) - Number(a[1])), [receptionReport, rev]);
  const maxServiceRevenue = Math.max(1, ...serviceRevenue.map(([, amount]) => Number(amount || 0)));
  const appointmentCompletion = percent(summary?.appointments_completed, summary?.appointments_total);

  return (
    <div className="clinical-page clinical-reports" data-testid="clinical-reports-dashboard" aria-busy={loading}>
      <header className="reports-hero">
        <div><p className="reports-eyebrow">Pilotage de la clinique</p><h1>Rapports cliniques</h1><p>Activité des services, encaissements et points d’attention sur une période donnée.</p></div>
        <div className="reports-period-summary" aria-label="Période du rapport"><span>Période analysée</span><strong>{reportDate(range.start)} – {reportDate(range.end)}</strong><small>{lastUpdated ? `Actualisé à ${lastUpdated.toLocaleTimeString('fr-GN', { hour: '2-digit', minute: '2-digit' })}` : 'Chargement des données…'}</small></div>
      </header>

      <form className="reports-command" onSubmit={(event) => { event.preventDefault(); applyRange(); }}>
        <fieldset>
          <legend>Période du rapport</legend>
          <div className="reports-presets" aria-label="Périodes rapides">
            <button type="button" onClick={() => applyRange(rangeEndingToday(1))}>Aujourd’hui</button>
            <button type="button" onClick={() => applyRange(rangeEndingToday(7))}>7 jours</button>
            <button type="button" onClick={() => applyRange(rangeEndingToday(30))}>30 jours</button>
          </div>
          <label htmlFor="report-start">Du<input id="report-start" name="report_start" autoComplete="off" type="date" value={draftRange.start} onChange={(event) => setDraftRange((current) => ({ ...current, start: event.target.value }))} /></label>
          <label htmlFor="report-end">Au<input id="report-end" name="report_end" autoComplete="off" type="date" value={draftRange.end} onChange={(event) => setDraftRange((current) => ({ ...current, end: event.target.value }))} /></label>
          <button className="clinical-btn" type="submit" disabled={loading}>{loading ? 'Actualisation…' : 'Appliquer'}</button>
        </fieldset>
        <div className="reports-export-actions" aria-label="Exporter le rapport"><span>Exporter</span><button type="button" disabled={Boolean(exporting)} onClick={() => exportReport('pdf')}>{exporting === 'pdf' ? 'PDF en préparation…' : 'PDF'}</button><button type="button" disabled={Boolean(exporting)} onClick={() => exportReport('csv')}>{exporting === 'csv' ? 'CSV en préparation…' : 'CSV'}</button></div>
      </form>

      <div className="reports-feedback" aria-live="polite">{error && <div className="clinical-alert clinical-alert--error" role="alert">{String(error)}</div>}{!error && notice && <div className="clinical-success" role="status">{notice}</div>}</div>

      {loading && !summary ? <section className="reports-loading" role="status"><strong>Préparation du rapport…</strong><span>Calcul des indicateurs cliniques et financiers.</span></section> : summary ? <>
        <section aria-labelledby="reports-overview-title">
          <div className="reports-section-heading"><div><p>Vue d’ensemble</p><h2 id="reports-overview-title">Les chiffres à retenir</h2></div><span>Données correspondant uniquement à la période sélectionnée.</span></div>
          <div className="reports-metric-grid">
            <Metric label="Encaissements nets" value={formatGNF(financial.net)} detail={`${financial.paid || 0} facture(s) payée(s)`} tone="primary" />
            <Metric label="Patients enregistrés" value={receptionReport?.patients_registered ?? summary.appointments_total} detail={isAasma ? 'Nouveaux dossiers' : 'Rendez-vous enregistrés'} />
            <Metric label="Admissions" value={receptionReport?.admissions ?? summary.admissions} detail={`${receptionReport?.hospitalizations ?? 0} hospitalisation(s)`} />
            <Metric label="À encaisser" value={financial.unpaid || 0} detail={isAasma ? 'Factures impayées' : 'Charges en attente'} tone={(financial.unpaid || 0) > 0 ? 'warning' : 'success'} />
            <Metric label="Remboursements" value={formatGNF(financial.refunds)} detail="Montant remboursé" />
          </div>
        </section>

        <div className="reports-decision-grid">
          <section className="reports-card" aria-labelledby="reports-activity-title">
            <div className="reports-card-heading"><div><p>Parcours patient</p><h2 id="reports-activity-title">Activité clinique</h2></div><Link to="/clinical/reception">Ouvrir la réception</Link></div>
            <div className="reports-activity-grid"><LedgerRow label="Consultations" value={summary.consultations} /><LedgerRow label="Laboratoire" value={summary.lab_orders} /><LedgerRow label="Imagerie" value={summary.imaging_orders} /><LedgerRow label="Pharmacie délivrée" value={summary.pharmacy_dispensed} /><LedgerRow label="Admissions" value={summary.admissions} /><LedgerRow label="Sorties" value={summary.discharges} /></div>
            <div className="reports-progress-copy"><span>Rendez-vous complétés</span><strong>{summary.appointments_completed} / {summary.appointments_total}</strong></div>
            <div className="reports-progress" role="progressbar" aria-label="Rendez-vous complétés" aria-valuemin="0" aria-valuemax="100" aria-valuenow={appointmentCompletion}><span style={{ width: `${appointmentCompletion}%` }} /></div>
            <small>{summary.appointments_cancelled} rendez-vous annulé(s) · {appointmentCompletion}% complétés</small>
          </section>

          <section className="reports-card reports-card--finance" aria-labelledby="reports-finance-title">
            <div className="reports-card-heading"><div><p>Situation financière</p><h2 id="reports-finance-title">Encaissements</h2></div><Link to="/clinical/billing">Voir la facturation</Link></div>
            <div className="reports-ledger"><LedgerRow label="Paiements reçus" value={formatGNF(financial.collected)} />{isAasma && <LedgerRow label="Remboursements effectués" value={`− ${formatGNF(financial.refunds)}`} />}<LedgerRow label="Recettes nettes" value={formatGNF(financial.net)} emphasis /></div>
            <div className={`reports-attention${financial.unpaid ? ' reports-attention--warning' : ''}`}><strong>{financial.unpaid || 0}</strong><span>{isAasma ? 'facture(s) restent à encaisser' : 'charge(s) restent à traiter'}</span></div>
          </section>
        </div>

        <section className="reports-card" aria-labelledby="reports-services-title">
          <div className="reports-card-heading"><div><p>Origine des recettes</p><h2 id="reports-services-title">Répartition par service</h2></div><span>{serviceRevenue.length ? `${serviceRevenue.length} service(s)` : 'Aucune recette ventilée'}</span></div>
          {serviceRevenue.length ? <div className="reports-service-bars">{serviceRevenue.map(([service, amount]) => <div className="reports-service-row" key={service}><div><span>{SERVICE_LABELS[service] || service}</span><strong>{formatGNF(amount)}</strong></div><div className="reports-service-track"><span style={{ width: `${Math.max(3, Math.round((Number(amount) / maxServiceRevenue) * 100))}%` }} /></div></div>)}</div> : <p className="reports-empty">Aucune recette ventilée sur cette période. Les paiements apparaîtront ici après encaissement.</p>}
        </section>
      </> : !error ? <p className="reports-empty">Aucune donnée disponible pour cette période.</p> : null}

      {isKoloma && <section className="reports-card" aria-labelledby="reports-monthly-title">
        <div className="reports-card-heading"><div><p>Programmes cliniques</p><h2 id="reports-monthly-title">Synthèse mensuelle</h2></div><label htmlFor="report-month">Mois<input id="report-month" name="report_month" autoComplete="off" type="month" value={`${reportMonth.year}-${String(reportMonth.month).padStart(2, '0')}`} onChange={(event) => { const [year, month] = event.target.value.split('-').map(Number); setReportMonth({ year, month }); }} /></label></div>
        {kolomaMonthly ? <div className="reports-program-grid"><Metric label="PEV" value={kolomaMonthly.pev?.total_vaccinations ?? '—'} detail="Vaccinations" /><Metric label="Soins infirmiers" value={kolomaMonthly.nursing?.total_procedures ?? '—'} detail="Procédures" /><Metric label="Hospitalisation" value={kolomaMonthly.hospitalization?.total_admissions ?? '—'} detail="Admissions" /><Metric label="Nutrition" value={kolomaMonthly.nutrition?.total_consultations ?? '—'} detail="Consultations" /><Metric label="Laboratoire" value={kolomaMonthly.laboratory?.total_tests ?? '—'} detail="Examens" /><Metric label="Pharmacie" value={kolomaMonthly.pharmacy?.total_dispensed ?? '—'} detail="Délivrances" /></div> : <p className="reports-empty">Aucune synthèse mensuelle disponible.</p>}
      </section>}
    </div>
  );
}
