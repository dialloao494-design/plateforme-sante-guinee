import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import clinicalApi from '../../services/clinicalApi';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import './clinical.css';

const PIPELINE = [
  {
    id: 'reception',
    step: 1,
    label: 'Réception',
    path: '/clinical/reception',
    hint: 'Accueil, caisse & file',
  },
  {
    id: 'doctor',
    step: 2,
    label: 'Médecin',
    path: '/clinical/doctor',
    hint: 'Consultations',
  },
  {
    id: 'lab',
    step: 3,
    label: 'Laboratoire',
    path: '/clinical/lab',
    hint: 'Examens',
  },
  {
    id: 'pharmacy',
    step: 4,
    label: 'Pharmacie',
    path: '/clinical/pharmacy',
    hint: 'Ordonnances',
  },
  {
    id: 'admin',
    step: 5,
    label: 'Administration',
    path: '/clinical/admin',
    hint: 'Gestion clinique',
  },
];

function stageMetrics(id, data) {
  if (!data) return { primary: '—', secondary: '' };
  switch (id) {
    case 'reception':
      return {
        primary: `${data.reception_waiting + data.reception_scheduled}`,
        secondary: `${data.cashier_pending_charges} factures · ${formatGNF(data.cashier_pending_gnf)}`,
      };
    case 'doctor':
      return {
        primary: `${data.doctor_waiting + data.doctor_in_consultation}`,
        secondary: `${data.doctor_in_consultation} en consultation`,
      };
    case 'lab':
      return {
        primary: `${data.lab_active_orders}`,
        secondary: 'examens actifs',
      };
    case 'pharmacy':
      return {
        primary: `${data.pharmacy_active_orders}`,
        secondary: 'ordonnances en cours',
      };
    case 'admin':
      return {
        primary: `${data.staff_count}`,
        secondary: 'personnel actif',
      };
    default:
      return { primary: '—', secondary: '' };
  }
}

export default function ClinicOperationsDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const { data: summary } = await clinicalApi.operationsSummary();
      setData(summary || null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Impossible de charger les opérations clinique');
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [load]);

  const totalPatients =
    data == null
      ? 0
      : data.reception_waiting +
        data.reception_scheduled +
        data.doctor_waiting +
        data.doctor_in_consultation;

  return (
    <div className="clinical-page clinical-ops-page">
      <h1>Opérations clinique</h1>
      <p className="clinical-lead">
        {data?.clinic_name
          ? `${data.clinic_name} — pilotage du parcours patient`
          : 'Tableau de bord manager — vue opérationnelle'}
      </p>
      {error && <p className="clinical-error">{String(error)}</p>}

      <section className="clinical-ops-banner">
        <div className="clinical-ops-banner-stat">
          <span className="clinical-ops-banner-label">Patients en parcours</span>
          <strong>{totalPatients}</strong>
        </div>
        <div className="clinical-ops-banner-stat">
          <span className="clinical-ops-banner-label">Factures ouvertes</span>
          <strong>{data?.cashier_pending_charges ?? '—'}</strong>
        </div>
        <div className="clinical-ops-banner-stat">
          <span className="clinical-ops-banner-label">Encaissé aujourd&apos;hui</span>
          <strong>{data ? formatGNF(data.revenue_collected_gnf) : '—'}</strong>
        </div>
        <div className="clinical-ops-banner-stat">
          <span className="clinical-ops-banner-label">Personnel</span>
          <strong>{data?.staff_count ?? '—'}</strong>
        </div>
      </section>

      <section className="clinical-ops-pipeline" aria-label="Parcours opérationnel clinique">
        <h2 className="clinical-ops-pipeline-title">Parcours opérationnel</h2>
        <div className="clinical-ops-flow">
          {PIPELINE.map((stage, index) => {
            const metrics = stageMetrics(stage.id, data);
            const isActive =
              data &&
              ((stage.id === 'reception' &&
                (data.reception_waiting + data.reception_scheduled > 0 || data.cashier_pending_charges > 0)) ||
                (stage.id === 'doctor' &&
                  data.doctor_waiting + data.doctor_in_consultation > 0) ||
                (stage.id === 'lab' && data.lab_active_orders > 0) ||
                (stage.id === 'pharmacy' && data.pharmacy_active_orders > 0));
            return (
              <div key={stage.id} className="clinical-ops-flow-item">
                {index > 0 && <span className="clinical-ops-arrow" aria-hidden="true" />}
                <Link
                  to={stage.path}
                  className={`clinical-ops-stage ${isActive ? 'clinical-ops-stage--active' : ''}`}
                >
                  <span className="clinical-ops-stage-step">{stage.step}</span>
                  <span className="clinical-ops-stage-label">{stage.label}</span>
                  <strong className="clinical-ops-stage-value">{metrics.primary}</strong>
                  <span className="clinical-ops-stage-hint">{metrics.secondary}</span>
                  <span className="clinical-ops-stage-action">Voir le poste →</span>
                </Link>
              </div>
            );
          })}
        </div>
      </section>

      <section className="clinical-card clinical-ops-guide">
        <h2>Parcours patient</h2>
        <p>
          Rendez-vous en ligne → réception (accueil &amp; encaissement) → consultation médicale →
          laboratoire → pharmacie → terminé.
        </p>
      </section>
    </div>
  );
}
