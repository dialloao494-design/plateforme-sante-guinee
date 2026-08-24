/**
 * Clinic-scoped administration — clinic_admin / admin only.
 * No clinic creation, no platform-wide user management.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import ClinicalFeedback from '../../components/clinical/ClinicalFeedback.jsx';
import AdminReadinessPanel from './admin/AdminReadinessPanel.jsx';
import { ROLE_LABELS, buildAttentionItems } from './admin/adminDomain.js';
import './clinical.css';
import './admin.css';

const STAFF_ROLE_OPTIONS = [
  { value: 'receptionist', label: 'Réceptionniste' },
  { value: 'cashier', label: 'Caissier' },
  { value: 'doctor', label: 'Médecin' },
  { value: 'lab_technician', label: 'Laborantin' },
  { value: 'pharmacist', label: 'Pharmacien' },
  { value: 'nutritionist', label: 'Nutritionniste' },
  { value: 'pev_agent', label: 'Agent PEV' },
  { value: 'nurse', label: 'Infirmier(ère)' },
  { value: 'midwife', label: 'Sage-femme (legacy)' },
];

export default function ClinicAdminDashboard() {
  const { user } = useAuth();
  const clinicId = user?.clinic_id;

  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [auditLogs, setAuditLogs] = useState([]);
  const [backupStatus, setBackupStatus] = useState(null);
  const [activity, setActivity] = useState(null);
  const [clinicStaff, setClinicStaff] = useState([]);
  const [onboarding, setOnboarding] = useState(null);
  const [setupBusy, setSetupBusy] = useState(false);
  const [staffForm, setStaffForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    role: 'receptionist',
  });
  const [resetBusyId, setResetBusyId] = useState(null);
  const [resetTarget, setResetTarget] = useState(null);
  const [temporaryPassword, setTemporaryPassword] = useState('');

  const loadClinicStaff = async (id) => {
    if (!id) return;
    try {
      const { data } = await clinicalApi.listStaff(Number(id));
      setClinicStaff(data || []);
    } catch {
      setClinicStaff([]);
    }
  };

  const loadCompliance = async () => {
    try {
      const [logs, backup, reception, doctor, lab, pharmacy, charges, revenue] = await Promise.all([
        clinicalApi.auditLogs({ limit: 30 }),
        clinicalApi.backupStatus(),
        clinicalApi.receptionQueue().catch(() => ({ data: [] })),
        clinicalApi.doctorQueue().catch(() => ({ data: [] })),
        clinicalApi.labQueue().catch(() => ({ data: [] })),
        clinicalApi.pharmacyQueue().catch(() => ({ data: [] })),
        clinicalApi.pendingCharges().catch(() => ({ data: [] })),
        clinicalApi.dailyRevenue().catch(() => ({ data: null })),
      ]);

      setAuditLogs(logs.data || []);
      setBackupStatus(backup.data || null);
      setActivity({
        reception: (reception.data || []).length,
        doctor: (doctor.data || []).length,
        lab: (lab.data || []).length,
        pharmacy: (pharmacy.data || []).length,
        pendingCharges: (charges.data || []).length,
        revenue: revenue.data,
      });
    } catch {
      /* clinic may not be ready */
    }
  };

  const loadOnboarding = async () => {
    try {
      const { data } = await clinicalApi.clinicOnboarding();
      setOnboarding(data);
    } catch (err) {
      setError(formatApiError(err, 'Impossible de charger la préparation de la clinique.'));
    }
  };

  useEffect(() => {
    loadCompliance();
    loadOnboarding();
    if (clinicId) {
      loadClinicStaff(clinicId);
    }
  }, [clinicId]);

  const saveOnboarding = async (changes) => {
    setSetupBusy(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.updateClinicOnboarding(changes);
      setOnboarding(data);
      setMessage(data.is_operational ? 'Configuration enregistrée. La clinique est prête.' : 'Étape enregistrée. Vous pourrez reprendre ici plus tard.');
    } catch (err) {
      setError(formatApiError(err, "L'étape n'a pas pu être enregistrée."));
    } finally {
      setSetupBusy(false);
    }
  };

  const resetStaffPassword = async (event) => {
    event.preventDefault();
    const staffUser = resetTarget;
    if (!clinicId || !staffUser?.id) return;
    setError('');
    setMessage('');
    setResetBusyId(staffUser.id);
    try {
      await clinicalApi.resetStaffPassword(staffUser.id, {
        clinic_id: Number(clinicId),
        new_password: temporaryPassword,
      });
      setMessage(
        `Mot de passe réinitialisé pour ${staffUser.email}. L’utilisateur devra le changer à la prochaine connexion.`,
      );
      setResetTarget(null);
      setTemporaryPassword('');
    } catch (err) {
      setError(formatApiError(err) || 'Réinitialisation impossible.');
    } finally {
      setResetBusyId(null);
    }
  };

  const createStaff = async (e) => {
    e.preventDefault();
    setError('');
    if (!clinicId) {
      setError('Aucune clinique assignée à votre compte.');
      return;
    }
    const chosenPassword = staffForm.password;
    try {
      const { data } = await clinicalApi.createStaff({
        ...staffForm,
        clinic_id: Number(clinicId),
      });
      setMessage(
        `Compte ${data.role} créé : ${data.email} — mot de passe : ${chosenPassword}`
      );
      setStaffForm((prev) => ({ ...prev, first_name: '', last_name: '', email: '', password: '' }));
      loadCompliance();
      loadClinicStaff(clinicId);
      loadOnboarding();
    } catch (err) {
      setError(formatApiError(err, 'Création compte impossible'));
    }
  };

  const stats = useMemo(() => {
    if (!activity) return [];
    return [
      { label: 'Réception (RDV)', value: activity.reception, variant: 'accent' },
      { label: 'File médecin', value: activity.doctor },
      { label: 'Examens labo', value: activity.lab, variant: 'warning' },
      { label: 'Ordonnances pharma', value: activity.pharmacy },
      { label: 'Personnel clinique', value: clinicStaff.length, variant: 'success' },
      {
        label: "Encaissé aujourd'hui",
        value: formatGNF(activity.revenue?.total_collected_gnf || 0),
      },
    ];
  }, [activity, clinicStaff.length]);

  const attentionItems = useMemo(() => buildAttentionItems(onboarding, activity), [onboarding, activity]);

  return (
    <div className="clinical-page clinical-page--clinic-admin" data-testid="admin-dashboard">
      <header className="clinical-page-header">
        <p className="clinical-eyebrow">Pilotage clinique</p>
        <h1>Administration — {user?.clinic_name || 'Ma clinique'}</h1>
        <p className="clinical-lead">
          Gestion du personnel et suivi d&apos;activité pour votre établissement uniquement.
          La création de nouvelles cliniques est réservée au propriétaire plateforme.
        </p>
      </header>

      <ClinicalFeedback error={error} message={message} />

      <AdminReadinessPanel onboarding={onboarding} busy={setupBusy} onSave={saveOnboarding} />

      <section className="admin-handoff" aria-labelledby="admin-attention-title">
        <div className="admin-handoff__heading">
          <p className="clinical-eyebrow">Relève administrative</p>
          <h2 id="admin-attention-title">À traiter aujourd’hui</h2>
        </div>
        {attentionItems.length === 0 ? (
          <p className="admin-handoff__clear"><span aria-hidden="true">✓</span> Aucun blocage administratif détecté.</p>
        ) : (
          <ul>{attentionItems.slice(0, 6).map((item) => (
            <li key={item.key}>
              <div><strong>{item.label}</strong><span>{item.detail}</span></div>
              {item.href ? <Link to={item.href}>Ouvrir</Link> : <button type="button" onClick={() => document.getElementById('readiness-title')?.scrollIntoView({ behavior: 'smooth' })}>Configurer</button>}
            </li>
          ))}</ul>
        )}
      </section>

      <ClinicalStatGrid stats={stats} />

      <nav className="clinical-section-nav" aria-label="Sections admin clinique">
        <a href="#clinic-activity">Activité</a>
        <a href="#clinic-audit">Audit</a>
        <a href="#clinic-staff">Personnel</a>
        <a href="#create-user">Créer un compte</a>
        <Link to="/clinical/billing">Facturation →</Link>
      </nav>

      {activity && (
        <section id="clinic-activity" className="clinical-card">
          <h2>Activité clinique en direct</h2>
          <div className="clinical-activity-grid">
            <div className="clinical-activity-item">
              <span className="clinical-stat-label">Réception</span>
              <strong>{activity.reception}</strong>
            </div>
            <div className="clinical-activity-item">
              <span className="clinical-stat-label">Médecin</span>
              <strong>{activity.doctor}</strong>
            </div>
            <div className="clinical-activity-item">
              <span className="clinical-stat-label">Laboratoire</span>
              <strong>{activity.lab}</strong>
            </div>
            <div className="clinical-activity-item">
              <span className="clinical-stat-label">Pharmacie</span>
              <strong>{activity.pharmacy}</strong>
            </div>
            <div className="clinical-activity-item">
              <span className="clinical-stat-label">Factures impayées</span>
              <strong>{activity.pendingCharges}</strong>
            </div>
            <div className="clinical-activity-item">
              <span className="clinical-stat-label">Caisse du jour</span>
              <strong>{formatGNF(activity.revenue?.total_collected_gnf || 0)}</strong>
            </div>
          </div>
        </section>
      )}

      {backupStatus && (
        <section className="clinical-card admin-section admin-backup-status">
          <h2>Sauvegarde quotidienne</h2>
          <p className={backupStatus.status === 'ok' ? 'clinical-success' : 'clinical-error'}>
            {backupStatus.message}
          </p>
        </section>
      )}

      <section id="clinic-audit" className="clinical-card admin-section">
        <h2>Journal d&apos;audit</h2>
        <ul className="clinical-list clinical-audit-list">
          {auditLogs.length === 0 && <li>Aucune entrée récente.</li>}
          {auditLogs.map((log) => (
            <li key={log.id}>
              <strong>{log.action}</strong> · {log.resource_type}
              {log.resource_id != null && ` #${log.resource_id}`}
            </li>
          ))}
        </ul>
      </section>

      <section id="clinic-staff" className="clinical-card admin-section">
        <h2>Personnel ({clinicStaff.length})</h2>
        {clinicStaff.length === 0 ? (
          <p className="clinical-muted">Aucun membre — créez un compte ci-dessous.</p>
        ) : (
          <div className="admin-table-scroll" tabIndex="0" role="region" aria-label="Liste du personnel de la clinique">
          <table className="clinical-stock-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Email</th>
                <th>Rôle</th>
                <th>Actif</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clinicStaff.map((u) => (
                <tr key={u.id}>
                  <td>{[u.first_name, u.last_name].filter(Boolean).join(' ') || 'Nom à compléter'}</td>
                  <td>{u.email}</td>
                  <td><span className="clinical-badge">{ROLE_LABELS[u.role] || u.role}</span></td>
                  <td>{u.is_active ? 'Oui' : 'Non'}</td>
                  <td>
                    {u.id !== user?.id && u.is_active ? (
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        disabled={resetBusyId === u.id}
                        onClick={() => { setResetTarget(u); setTemporaryPassword(''); }}
                      >
                        {resetBusyId === u.id ? '…' : 'Réinit. MDP'}
                      </button>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>

      {resetTarget && (
        <div className="admin-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setResetTarget(null); }}>
          <section className="admin-dialog" role="dialog" aria-modal="true" aria-labelledby="reset-password-title">
            <p className="clinical-eyebrow">Accès du personnel</p>
            <h2 id="reset-password-title">Réinitialiser le mot de passe</h2>
            <p>Compte : <strong>{[resetTarget.first_name, resetTarget.last_name].filter(Boolean).join(' ') || resetTarget.email}</strong></p>
            <form onSubmit={resetStaffPassword}>
              <label htmlFor="reset-temporary-password">Nouveau mot de passe temporaire</label>
              <input id="reset-temporary-password" type="password" minLength="8" autoComplete="new-password" value={temporaryPassword} onChange={(event) => setTemporaryPassword(event.target.value)} autoFocus required />
              <p className="clinical-muted">L’utilisateur devra choisir son propre mot de passe à la prochaine connexion.</p>
              <div className="admin-dialog__actions">
                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => setResetTarget(null)}>Annuler</button>
                <button type="submit" className="clinical-btn" disabled={resetBusyId === resetTarget.id}>{resetBusyId === resetTarget.id ? 'Réinitialisation…' : 'Réinitialiser'}</button>
              </div>
            </form>
          </section>
        </div>
      )}

      <section className="clinical-card admin-section admin-create-staff" id="create-user">
        <h2>Créer un compte personnel</h2>
        <p className="clinical-lead">
          Comptes pour votre clinique : réception, médecin, laboratoire, pharmacie, caisse, nutrition, sage-femme.
        </p>
        <form className="admin-create-staff__form" onSubmit={createStaff}>
          <div className="clinical-field">
            <label htmlFor="staff-first-name">Prénom</label>
            <input id="staff-first-name" value={staffForm.first_name} onChange={(e) => setStaffForm({ ...staffForm, first_name: e.target.value })} required />
          </div>
          <div className="clinical-field">
            <label htmlFor="staff-last-name">Nom</label>
            <input id="staff-last-name" value={staffForm.last_name} onChange={(e) => setStaffForm({ ...staffForm, last_name: e.target.value })} required />
          </div>
          <div className="clinical-field">
            <label htmlFor="staff-clinic">Clinique</label>
            <input
              id="staff-clinic"
              name="clinic"
              value={user?.clinic_name ? `${user.clinic_name} (#${clinicId})` : `#${clinicId || '—'}`}
              readOnly
              disabled
            />
          </div>
          <div className="clinical-field">
            <label htmlFor="staff-email">Email professionnel</label>
            <input
              id="staff-email"
              name="email"
              type="email"
              inputMode="email"
              autoComplete="email"
              spellCheck="false"
              value={staffForm.email}
              onChange={(e) => setStaffForm({ ...staffForm, email: e.target.value })}
              required
            />
          </div>
          <div className="clinical-field">
            <label htmlFor="staff-password">Mot de passe temporaire</label>
            <input
              id="staff-password"
              name="new-password"
              type="password"
              autoComplete="new-password"
              value={staffForm.password}
              onChange={(e) => setStaffForm({ ...staffForm, password: e.target.value })}
              required
            />
          </div>
          <div className="clinical-field">
            <label htmlFor="staff-role">Rôle clinique</label>
            <select
              id="staff-role"
              name="role"
              autoComplete="off"
              value={staffForm.role}
              onChange={(e) => setStaffForm({ ...staffForm, role: e.target.value })}
            >
              {STAFF_ROLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <button type="submit" className="clinical-btn admin-create-staff__submit">Créer le compte</button>
        </form>
      </section>
    </div>
  );
}
