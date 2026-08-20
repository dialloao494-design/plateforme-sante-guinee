import { useEffect, useRef } from 'react';
import ClinicalStatGrid from '../../ClinicalStatGrid.jsx';
import { DASHBOARD_BUCKET_TITLES } from '../constants.js';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';
import { refundStatusLabel } from '../utils.js';
import ClinicalSectionToolbar from '../../../../components/clinical/ClinicalSectionToolbar.jsx';

export default function DashboardTab({
  activeStatBucket,
  loadQueueBucket,
  loading,
  refresh,
  renderQueueTable,
  statCards,
  stats,
  dashboardUpdatedAt,
  openPatient,
}) {
  const queueHeadingRef = useRef(null);

  useEffect(() => {
    if (activeStatBucket && !loading) queueHeadingRef.current?.focus();
  }, [activeStatBucket, loading]);

  return (
        <section className="reception-his-panel">
          <ClinicalSectionToolbar
            title="Vue d’ensemble"
            description="Activité de la réception et situation financière de la clinique."
            updatedAt={dashboardUpdatedAt}
            onRefresh={refresh}
            refreshing={loading}
          />
          <ClinicalStatGrid stats={statCards} onStatClick={loadQueueBucket} activeKey={activeStatBucket} />
          {activeStatBucket && (
            <section className="lab-his-queue-panel reception-his-queue-panel" aria-live="polite">
              <h3 ref={queueHeadingRef} tabIndex="-1">{DASHBOARD_BUCKET_TITLES[activeStatBucket] || 'Liste détaillée'}</h3>
              <div className="lab-his-results-wrap">{renderQueueTable(openPatient)}</div>
            </section>
          )}
          <div className="clinical-grid">
            <article className="clinical-card">
              <h3>Répartition H/F/Autre</h3>
              <ul className="reception-his-list">
                <li>H : {stats?.gender_distribution?.male ?? 0}</li>
                <li>F : {stats?.gender_distribution?.female ?? 0}</li>
                <li>Autre : {stats?.gender_distribution?.other ?? 0}</li>
              </ul>
            </article>
            <article className="clinical-card">
              <h3>Répartition par service</h3>
              <ul className="reception-his-list">
                {Object.entries(stats?.department_distribution || {}).map(([k, v]) => <li key={k}>{k} : {v}</li>)}
              </ul>
            </article>
          </div>
          <div className="clinical-grid">
            <article className="clinical-card">
              <h3>Inscriptions récentes</h3>
              <ul className="reception-his-list">
                {(stats?.recent_registrations || []).map((r, idx) => (
                  <li key={`${r.patient_id}-${idx}`}>{r.patient_name} · ID patient {r.patient_id}</li>
                ))}
              </ul>
            </article>
            <article className="clinical-card">
              <h3>Admissions récentes</h3>
              <ul className="reception-his-list">
                {(stats?.recent_admissions || []).map((r, idx) => (
                  <li key={`${r.admission_number}-${idx}`}>N° admission {r.admission_number} · {r.patient_id} · {r.department || '—'}</li>
                ))}
              </ul>
            </article>
          </div>
          <div className="clinical-grid">
            <article className="clinical-card">
              <h3>Paiements récents</h3>
              <ul className="reception-his-list">
                {(stats?.recent_payments || []).map((r, idx) => (
                  <li key={`${r.invoice_number}-${idx}`}>N° facture {r.invoice_number} · {formatGNF(r.amount_gnf || 0)} · {r.payment_method}</li>
                ))}
              </ul>
            </article>
            <article className="clinical-card">
              <h3>Remboursements récents</h3>
              <ul className="reception-his-list">
                {(stats?.recent_refunds || []).map((r, idx) => (
                  <li key={`${r.refund_number}-${idx}`}>{r.refund_number} · {r.patient_id} · {formatGNF(r.refund_amount_gnf || 0)} · {refundStatusLabel(r.status)}</li>
                ))}
              </ul>
            </article>
          </div>
        </section>
  );
}
