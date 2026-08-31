/**
 * Clinic-scoped administration — clinic_admin / admin only.
 * No clinic creation, no platform-wide user management.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { useConfirm } from '../../contexts/ConfirmContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import ClinicalFeedback from '../../components/clinical/ClinicalFeedback.jsx';
import AdminReadinessPanel from './admin/AdminReadinessPanel.jsx';
import AdminShiftHandoff from './admin/AdminShiftHandoff.jsx';
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
  const confirm = useConfirm();
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
    role: 'receptionist',
  });
  const [invitationBusyId, setInvitationBusyId] = useState(null);
  const [resetBusyId, setResetBusyId] = useState(null);
  const [lifecycleBusyId, setLifecycleBusyId] = useState(null);
  const [staffSearch, setStaffSearch] = useState('');
  const [staffRoleFilter, setStaffRoleFilter] = useState('');
  const [staffStatusFilter, setStaffStatusFilter] = useState('');
  const [auditFilters, setAuditFilters] = useState({ action: '', date_from: '', date_to: '' });

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

  const resetStaffPassword = async (staffUser) => {
    if (!clinicId || !staffUser?.id) return;
    setError('');
    setMessage('');
    setResetBusyId(staffUser.id);
    try {
      const { data } = await clinicalApi.sendStaffPasswordReset(staffUser.id, Number(clinicId));
      setMessage(data.delivery_status === 'sent'
        ? `Lien de réinitialisation envoyé à ${staffUser.email}. Les liens précédents ont été annulés.`
        : `Le lien a été préparé mais l’email n’a pas pu être livré à ${staffUser.email}.`);
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
    try {
      const { data } = await clinicalApi.inviteStaff({
        ...staffForm,
        clinic_id: Number(clinicId),
      });
      setMessage(data.delivery_status === 'sent'
        ? `Invitation envoyée à ${data.staff.email}. Le compte restera inactif jusqu’au choix du mot de passe.`
        : `Compte préparé pour ${data.staff.email}, mais l’email n’a pas pu être livré. Utilisez « Renvoyer » après vérification du service email.`);
      setStaffForm((prev) => ({ ...prev, first_name: '', last_name: '', email: '' }));
      loadCompliance();
      loadClinicStaff(clinicId);
      loadOnboarding();
    } catch (err) {
      setError(formatApiError(err, 'Création compte impossible'));
    }
  };

  const resendInvitation = async (staffUser) => {
    setInvitationBusyId(staffUser.id); setError(''); setMessage('');
    try {
      const { data } = await clinicalApi.resendStaffInvitation(staffUser.id, Number(clinicId));
      setMessage(data.delivery_status === 'sent' ? `Nouvelle invitation envoyée à ${staffUser.email}. L’ancien lien a été annulé.` : `L’invitation n’a pas pu être livrée à ${staffUser.email}.`);
      await loadClinicStaff(clinicId);
    } catch (err) { setError(formatApiError(err, 'Renvoi impossible.')); }
    finally { setInvitationBusyId(null); }
  };

  const changeStaffAccess = async (staffUser, nextActive) => {
    const accepted = await confirm({
      title: nextActive ? 'Réactiver cet accès ?' : 'Désactiver cet accès ?',
      message: nextActive
        ? `${staffUser.email} pourra de nouveau se connecter à la clinique.`
        : `${staffUser.email} sera immédiatement déconnecté et ne pourra plus accéder aux données. Son historique sera conservé.`,
      confirmLabel: nextActive ? 'Réactiver l’accès' : 'Désactiver l’accès',
      tone: nextActive ? 'default' : 'danger',
    });
    if (!accepted) return;
    setLifecycleBusyId(staffUser.id); setError(''); setMessage('');
    try {
      if (nextActive) await clinicalApi.reactivateStaff(staffUser.id, Number(clinicId), 'Réactivation validée par l’administration clinique');
      else await clinicalApi.deactivateStaff(staffUser.id, Number(clinicId), 'Accès retiré par l’administration clinique');
      await loadClinicStaff(clinicId);
      setMessage(nextActive ? `Accès réactivé pour ${staffUser.email}.` : `Accès désactivé pour ${staffUser.email}.`);
    } catch (err) { setError(formatApiError(err, 'Modification de l’accès impossible.')); }
    finally { setLifecycleBusyId(null); }
  };

  const deleteStaff = async (staffUser) => {
    const accepted = await confirm({
      title: 'Supprimer définitivement ce compte ?',
      message: `${staffUser.email} sera supprimé. Cette action est réservée aux invitations jamais utilisées et ne peut pas être annulée.`,
      confirmLabel: 'Supprimer le compte',
      tone: 'danger',
    });
    if (!accepted) return;
    setLifecycleBusyId(staffUser.id); setError(''); setMessage('');
    try {
      await clinicalApi.deleteStaff(staffUser.id, Number(clinicId), 'Invitation inutilisée supprimée par l’administration clinique');
      await loadClinicStaff(clinicId);
      setMessage(`Compte ${staffUser.email} supprimé.`);
    } catch (err) { setError(formatApiError(err, 'Suppression impossible.')); }
    finally { setLifecycleBusyId(null); }
  };

  const revokeStaffSessions = async (staffUser) => {
    const accepted = await confirm({
      title: 'Déconnecter tous les appareils ?',
      message: `${staffUser.email} devra se reconnecter sur chaque appareil.`,
      confirmLabel: 'Déconnecter les sessions',
      tone: 'danger',
    });
    if (!accepted) return;
    setLifecycleBusyId(staffUser.id); setError(''); setMessage('');
    try {
      const { data } = await clinicalApi.revokeStaffSessions(staffUser.id, Number(clinicId), 'Sessions révoquées par l’administration clinique');
      setMessage(`${data.revoked_sessions} session(s) révoquée(s) pour ${staffUser.email}.`);
      await loadClinicStaff(clinicId);
    } catch (err) { setError(formatApiError(err, 'Déconnexion impossible.')); }
    finally { setLifecycleBusyId(null); }
  };

  const filterAudit = async () => {
    setError('');
    try {
      const { data } = await clinicalApi.auditLogs({ limit: 200, ...Object.fromEntries(Object.entries(auditFilters).filter(([, value]) => value)) });
      setAuditLogs(data || []);
    } catch (err) { setError(formatApiError(err, 'Journal d’audit indisponible.')); }
  };

  const shiftFeedback = (kind, text) => { setError(kind === 'error' ? text : ''); setMessage(kind === 'message' ? text : ''); };

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
  const filteredStaff = useMemo(() => {
    const q = staffSearch.trim().toLowerCase();
    return clinicStaff.filter((member) => (
      (!q || `${member.first_name || ''} ${member.last_name || ''} ${member.email}`.toLowerCase().includes(q))
      && (!staffRoleFilter || member.role === staffRoleFilter)
      && (!staffStatusFilter || (staffStatusFilter === 'active') === member.is_active)
    ));
  }, [clinicStaff, staffSearch, staffRoleFilter, staffStatusFilter]);

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

      <AdminShiftHandoff onFeedback={shiftFeedback} />

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
        <div className="admin-section-heading"><div><p className="clinical-eyebrow">Traçabilité</p><h2>Journal d&apos;audit</h2></div><span>{auditLogs.length} entrée(s)</span></div>
        <div className="admin-directory-filters">
          <label>Action<input value={auditFilters.action} onChange={(e) => setAuditFilters({ ...auditFilters, action: e.target.value })} placeholder="Ex. deactivate…" /></label>
          <label>Du<input type="date" value={auditFilters.date_from} onChange={(e) => setAuditFilters({ ...auditFilters, date_from: e.target.value })} /></label>
          <label>Au<input type="date" value={auditFilters.date_to} onChange={(e) => setAuditFilters({ ...auditFilters, date_to: e.target.value })} /></label>
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={filterAudit}>Appliquer</button>
        </div>
        <ul className="clinical-list clinical-audit-list admin-audit-ledger" tabIndex="0" aria-label="Journal d’activité, défilement possible">
          {auditLogs.length === 0 && <li>Aucune entrée récente.</li>}
          {auditLogs.map((log) => (
            <li key={log.id}>
              <time>{new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(log.timestamp))}</time>
              <span><strong>{log.action}</strong> · {log.resource_type}{log.resource_id != null && ` #${log.resource_id}`}</span>
              <span>{log.actor_email || `Utilisateur #${log.actor_id}`}</span>
              <small>{log.reason || 'Entrée historique sans motif'}</small>
            </li>
          ))}
        </ul>
      </section>

      <section id="clinic-staff" className="clinical-card admin-section">
        <div className="admin-section-heading"><div><p className="clinical-eyebrow">Annuaire opérationnel</p><h2>Personnel</h2></div><span>{filteredStaff.length} / {clinicStaff.length}</span></div>
        <div className="admin-directory-filters"><label>Recherche<input type="search" autoComplete="off" placeholder="Nom ou e-mail…" value={staffSearch} onChange={(e) => setStaffSearch(e.target.value)} /></label><label>Rôle<select value={staffRoleFilter} onChange={(e) => setStaffRoleFilter(e.target.value)}><option value="">Tous</option>{STAFF_ROLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><label>Accès<select value={staffStatusFilter} onChange={(e) => setStaffStatusFilter(e.target.value)}><option value="">Tous</option><option value="active">Actifs</option><option value="inactive">Inactifs</option></select></label></div>
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
                <th>Accès</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStaff.map((u) => (
                <tr key={u.id}>
                  <td>{[u.first_name, u.last_name].filter(Boolean).join(' ') || 'Nom à compléter'}</td>
                  <td>{u.email}</td>
                  <td><span className="clinical-badge">{ROLE_LABELS[u.role] || u.role}</span></td>
                  <td><strong>{u.is_active ? 'Actif' : u.invitation_status === 'sent' ? 'Invitation envoyée' : 'Inactif'}</strong><span className="admin-cell-meta">Dernière connexion : {u.last_login_at ? new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(u.last_login_at)) : 'jamais'} · MFA {u.mfa_enabled ? 'active' : 'inactive'} · {u.active_sessions || 0} session(s)</span></td>
                  <td>
                    {u.id === user?.id ? <span className="clinical-muted">Votre compte</span> : (
                      <div className="admin-staff-actions">
                        {u.is_active ? <>
                          <button type="button" className="clinical-btn clinical-btn--secondary" disabled={resetBusyId === u.id || lifecycleBusyId === u.id} onClick={() => resetStaffPassword(u)}>{resetBusyId === u.id ? 'Envoi…' : 'Réinitialiser le mot de passe'}</button>
                          <button type="button" className="clinical-btn clinical-btn--secondary" disabled={lifecycleBusyId === u.id} onClick={() => revokeStaffSessions(u)}>Déconnecter</button>
                          <button type="button" className="clinical-btn clinical-btn--secondary admin-staff-actions__warning" disabled={lifecycleBusyId === u.id} onClick={() => changeStaffAccess(u, false)}>{lifecycleBusyId === u.id ? 'Désactivation…' : 'Désactiver'}</button>
                        </> : <>
                          {u.invitation_status ? <button type="button" className="clinical-btn clinical-btn--secondary" disabled={invitationBusyId === u.id || lifecycleBusyId === u.id} onClick={() => resendInvitation(u)}>{invitationBusyId === u.id ? 'Envoi…' : 'Renvoyer l’invitation'}</button> : <button type="button" className="clinical-btn" disabled={lifecycleBusyId === u.id} onClick={() => changeStaffAccess(u, true)}>{lifecycleBusyId === u.id ? 'Réactivation…' : 'Réactiver'}</button>}
                          {u.invitation_status && <button type="button" className="clinical-btn clinical-btn--danger" disabled={lifecycleBusyId === u.id} onClick={() => deleteStaff(u)}>{lifecycleBusyId === u.id ? 'Suppression…' : 'Supprimer'}</button>}
                        </>}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>

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
          <div className="admin-create-staff__delivery"><strong>Aucun mot de passe à transmettre</strong><span>Le personnel recevra un lien personnel valable 48 heures.</span></div>
          <button type="submit" className="clinical-btn admin-create-staff__submit">Envoyer l’invitation</button>
        </form>
      </section>
    </div>
  );
}
