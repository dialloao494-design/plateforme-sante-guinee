import { useCallback, useEffect, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';

import './clinical.css';

export default function DischargeDashboard() {
  const [summaries, setSummaries] = useState([]);
  const [openVisits, setOpenVisits] = useState([]);
  const [visitId, setVisitId] = useState('');
  const [checklist, setChecklist] = useState(null);
  const [followUp, setFollowUp] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [summariesRes, visitsRes] = await Promise.all([
        clinicalApi.dischargeSummaries(),
        clinicalApi.dischargeOpenVisits(),
      ]);
      setSummaries(summariesRes.data || []);
      setOpenVisits(visitsRes.data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Sortie indisponible');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadChecklist = async (id = visitId) => {
    if (!id) return;
    try {
      const { data } = await clinicalApi.dischargeChecklist(Number(id));
      setChecklist(data);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Checklist indisponible');
    }
  };

  const onSelectVisit = (id) => {
    setVisitId(String(id));
    loadChecklist(id);
  };

  const discharge = async (force = false) => {
    if (!visitId) return;
    try {
      await clinicalApi.executeDischarge({
        visit_id: Number(visitId),
        follow_up_instructions: followUp || undefined,
        force,
      });
      setMessage('Patient sorti — dossier archivé');
      setChecklist(null);
      setVisitId('');
      setFollowUp('');
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Sortie impossible');
    }
  };

  const stats = [
    { label: 'Sorties', value: summaries.length, hint: 'Archivées EMR' },
    { label: 'Visites ouvertes', value: openVisits.length, hint: 'En attente de sortie' },
    {
      label: 'Prêt',
      value: checklist?.ready_for_discharge ? 'Oui' : '—',
      hint: checklist ? `Visite #${checklist.visit_id}` : 'Checklist',
    },
  ];

  return (
    <div className="clinical-page">
      <header className="clinical-header">
        <h1>Sortie patient</h1>
        <p>Validation facture, bon de sortie et archivage dossier médical.</p>
      </header>
      {error && <div className="clinical-alert clinical-alert--error">{error}</div>}
      {message && <div className="clinical-alert clinical-alert--success">{message}</div>}
      <ClinicalStatGrid stats={stats} />

      <section className="clinical-panel">
        <h2>Visites en cours</h2>
        <ul className="clinical-queue">
          {openVisits.length === 0 && <li>Aucune visite ouverte.</li>}
          {openVisits.map((v) => (
            <li key={v.id}>
              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => onSelectVisit(v.id)}>
                Visite #{v.id} — {v.patient_name || `Patient #${v.patient_id}`}
              </button>
              <span className="clinical-badge">{v.status}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="clinical-panel">
        <h2>Workflow sortie</h2>
        <div className="clinical-form">
          <label>
            Visite sélectionnée
            <input value={visitId} onChange={(e) => setVisitId(e.target.value)} placeholder="ID visite" />
          </label>
          <label>
            Consignes de suivi
            <textarea rows={2} value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
          </label>
          <div className="clinical-actions">
            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => loadChecklist()}>
              Vérifier checklist
            </button>
            <button type="button" className="clinical-btn" onClick={() => discharge(false)}>
              Sortir patient
            </button>
          </div>
          {checklist && (
            <ul className="clinical-list">
              <li>Charges en attente: {checklist.pending_charges}</li>
              <li>Factures impayées: {checklist.unpaid_invoices}</li>
              <li>Facture validée: {checklist.invoice_validated ? 'Oui' : 'Non'}</li>
              <li>Pharmacie en attente: {checklist.pending_pharmacy_orders}</li>
              <li>Prêt: {checklist.ready_for_discharge ? 'Oui' : 'Non'}</li>
            </ul>
          )}
        </div>
      </section>

      <section className="clinical-panel">
        <h2>Historique des sorties</h2>
        <ul className="clinical-queue">
          {summaries.map((s) => (
            <li key={s.id}>
              <strong>{s.patient_name}</strong>
              <span className="clinical-badge">{s.discharge_type}</span>
              <div>{s.diagnoses || '—'}</div>
              {s.archived_to_emr && <span className="clinical-badge">EMR</span>}
              <a href={clinicalApi.dischargePdfUrl(s.id)} target="_blank" rel="noreferrer">
                PDF sortie
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
