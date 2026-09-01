import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../../services/clinicalApi.js';
import { formatApiError } from '../../../utils/apiError.js';
import { formatGNF } from '../../../utils/clinicalPresentation.js';

const now = new Date();

export default function PharmacyReportTab() {
  const [period, setPeriod] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { const { data } = await clinicalApi.pharmacyMonthlyReport(period.year, period.month); setReport(data); }
    catch (err) { setError(formatApiError(err, 'Chargement du rapport impossible')); }
    finally { setLoading(false); }
  }, [period.month, period.year]);
  useEffect(() => { void load(); }, [load]);
  const monthValue = `${period.year}-${String(period.month).padStart(2, '0')}`;
  return <section className="pharmacy-report" aria-labelledby="pharmacy-report-title">
    <div className="pharmacy-report-command"><div><p className="pharmacy-section-kicker">Pilotage mensuel</p><h2 id="pharmacy-report-title">Rapport pharmacie</h2><p>Patients servis, activité, encaissements et médicaments délivrés.</p></div><label>Mois<input type="month" value={monthValue} onChange={(event) => { const [year, month] = event.target.value.split('-').map(Number); setPeriod({ year, month }); }} /></label></div>
    {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
    {loading && !report ? <p role="status">Chargement du rapport…</p> : report && <>
      <div className="pharmacy-report-scorecard" aria-label="Indicateurs pharmacie">
        <article><span>Patients servis</span><strong>{report.unique_patients}</strong><small>patients distincts</small></article>
        <article><span>Dispensations</span><strong>{report.total_dispensed}</strong><small>commandes délivrées</small></article>
        <article className="pharmacy-report-scorecard__money"><span>Recettes encaissées</span><strong>{formatGNF(report.collected_revenue_gnf)}</strong><small>{report.collection_rate_percent}% des ventes</small></article>
        <article><span>Reste à encaisser</span><strong>{formatGNF(report.pending_revenue_gnf)}</strong><small>sur {formatGNF(report.generated_revenue_gnf)}</small></article>
      </div>
      <div className="pharmacy-report-grid">
        <article className="pharmacy-report-card"><h3>Médicaments les plus délivrés</h3>{report.top_medications?.length ? <ol>{report.top_medications.map((item) => <li key={item.medication_name}><span>{item.medication_name}<small>{item.quantity} unité(s)</small></span><strong>{formatGNF(item.revenue_gnf)}</strong></li>)}</ol> : <p className="pharmacy-empty">Aucun médicament délivré pour ce mois.</p>}</article>
        <article className="pharmacy-report-card"><h3>Registre du mois</h3><p className="pharmacy-report-callout"><strong>{report.requests_created}</strong> demande(s) créée(s)</p><p>Ce registre conserve le N° de demande, le patient, la date et la dispensation pour faciliter les contrôles.</p></article>
      </div>
    </>}
  </section>;
}
