/** Clinic control room: staff, security, configuration, audit, health, and data governance. */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import clinicalApi from '../../services/clinicalApi.js';
import httpClient from '../../services/httpClient.js';
import platformApi from '../../services/platformApi.js';
import { loadClinicDetail, loadClinicStaff, ROLE_LABELS } from '../../services/platformClinicData.js';
import { formatApiError } from '../../utils/apiError.js';
import ClinicalFeedback from '../../components/clinical/ClinicalFeedback.jsx';
import PageSkeleton from '../../components/ui/PageSkeleton.jsx';
import '../clinical/clinical.css';
import './PlatformOwner.css';

const TABS = [['overview', 'Vue d’ensemble'], ['staff', 'Personnel'], ['security', 'Sécurité'], ['configuration', 'Configuration'], ['audit', 'Audit'], ['data', 'Données']];
const STAFF_ROLES = ['clinic_admin', 'receptionist', 'cashier', 'doctor', 'nurse', 'midwife', 'lab_technician', 'pharmacist', 'nutritionist', 'pev_agent'];
const MODULES = ['reception', 'billing', 'doctor', 'nursing', 'laboratory', 'pharmacy', 'hospitalization', 'reports'];
const PAYMENT_METHODS = ['cash', 'orange_money', 'bank_transfer', 'insurance'];

function formatDate(value) {
  if (!value) return 'Jamais';
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
}

export default function PlatformClinicDetail() {
  const { clinicId } = useParams(); const id = Number(clinicId);
  const [params, setParams] = useSearchParams(); const tab = params.get('tab') || 'overview';
  const [detail, setDetail] = useState(null); const [staff, setStaff] = useState([]);
  const [health, setHealth] = useState(null); const [governance, setGovernance] = useState(null);
  const [audit, setAudit] = useState([]); const [loading, setLoading] = useState(true);
  const [error, setError] = useState(''); const [message, setMessage] = useState('');
  const [staffQuery, setStaffQuery] = useState(''); const [staffRole, setStaffRole] = useState(''); const [staffStatus, setStaffStatus] = useState('');
  const [sort, setSort] = useState('email'); const [page, setPage] = useState(1); const [selectedStaff, setSelectedStaff] = useState(null);
  const [dialog, setDialog] = useState(null); const [reason, setReason] = useState(''); const [confirmation, setConfirmation] = useState(''); const [busy, setBusy] = useState(false);
  const [waiveBackup, setWaiveBackup] = useState(false); const [mergePreview, setMergePreview] = useState(null);
  const [invite, setInvite] = useState({ first_name: '', last_name: '', email: '', role: 'receptionist' });
  const [config, setConfig] = useState(null); const [auditFilter, setAuditFilter] = useState({ action: '', date_from: '', date_to: '' });

  const loadAll = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [clinic, members, healthData, governanceData, auditData] = await Promise.all([
        loadClinicDetail(id), loadClinicStaff(id), platformApi.clinicHealth(id).then((r) => r.data),
        platformApi.clinicDataGovernance(id).then((r) => r.data), platformApi.auditLogs({ clinic_id: id, limit: 100 }).then((r) => r.data),
      ]);
      setDetail(clinic); setStaff(members); setHealth(healthData); setGovernance(governanceData); setAudit(auditData);
      setConfig({ name: clinic.name, address: clinic.address || '', city: clinic.city || '', phone: clinic.phone || '', email: clinic.email || '', ...clinic.configuration });
    } catch (err) { setError(formatApiError(err, 'Impossible de charger l’administration de cette clinique.')); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { loadAll(); }, [loadAll]);

  const visibleStaff = useMemo(() => {
    const q = staffQuery.trim().toLowerCase();
    return staff.filter((u) => (!q || `${u.email} ${u.full_name || ''}`.toLowerCase().includes(q)) && (!staffRole || u.role === staffRole) && (!staffStatus || (staffStatus === 'active') === u.is_active)).sort((a, b) => String(a[sort] || '').localeCompare(String(b[sort] || ''), 'fr'));
  }, [staff, staffQuery, staffRole, staffStatus, sort]);
  const pageRows = visibleStaff.slice((page - 1) * 10, page * 10); const pages = Math.max(1, Math.ceil(visibleStaff.length / 10));

  const setTab = (value) => { const next = new URLSearchParams(params); next.set('tab', value); setParams(next); };
  const showDialog = (type, target = null) => { setDialog({ type, target }); setReason(''); setConfirmation(type === 'merge' ? (target?.target?.patient_number || String(target?.target?.id || '')) : ''); setWaiveBackup(false); setMergePreview(null); setError(''); setMessage(''); };

  const inviteStaff = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await clinicalApi.inviteStaff({ ...invite, clinic_id: id }); setMessage(`Invitation envoyée à ${invite.email}.`); setInvite({ first_name: '', last_name: '', email: '', role: 'receptionist' }); await loadAll(); }
    catch (err) { setError(formatApiError(err, 'Invitation impossible.')); } finally { setBusy(false); }
  };

  const runStaffAction = async () => {
    const member = dialog?.target; if (!member || reason.trim().length < 3) return; setBusy(true); setError('');
    try {
      if (dialog.type === 'deactivate') await platformApi.deactivateStaff(id, member.id, reason);
      else if (dialog.type === 'reactivate') await platformApi.reactivateStaff(id, member.id, reason);
      else if (dialog.type === 'delete') await platformApi.deleteStaff(id, member.id, reason);
      else await platformApi.revokeStaffSessions(id, member.id, reason);
      setMessage(`Action terminée pour ${member.email}.`); setDialog(null); setSelectedStaff(null); await loadAll();
    } catch (err) { setError(formatApiError(err, 'Action impossible.')); } finally { setBusy(false); }
  };

  const changeRole = async (member, role) => {
    setBusy(true); setError('');
    try { await clinicalApi.updateStaffRole(member.id, { clinic_id: id, role, reason: 'Rôle modifié depuis le centre de contrôle plateforme' }); setMessage(`Rôle de ${member.email} mis à jour.`); await loadAll(); }
    catch (err) { setError(formatApiError(err, 'Modification du rôle impossible.')); } finally { setBusy(false); }
  };

  const saveConfiguration = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await platformApi.updateClinicConfiguration(id, config); setMessage('Configuration de la clinique enregistrée et auditée.'); await loadAll(); }
    catch (err) { setError(formatApiError(err, 'Configuration non enregistrée.')); } finally { setBusy(false); }
  };

  const changeClinicState = async () => {
    if (confirmation !== detail.name || reason.trim().length < 5) return; setBusy(true); setError('');
    try { await platformApi.changeClinicState(id, { action: dialog.type, reason, confirmation }); setMessage('État de la clinique mis à jour. Les sessions concernées ont été révoquées.'); setDialog(null); await loadAll(); }
    catch (err) { setError(formatApiError(err, 'Changement d’état impossible.')); } finally { setBusy(false); }
  };

  const resetData = async () => {
    if (confirmation !== detail.name || reason.trim().length < 5) return; setBusy(true); setError('');
    try { const { data } = await platformApi.resetClinicData(id, { confirmation, reason, acknowledge_irreversible: true, waive_backup: waiveBackup }); setMessage(`Remise à zéro terminée et vérifiée. Nouvelle génération hors ligne : ${data.offline_data_epoch}.`); setDialog(null); await loadAll(); }
    catch (err) { setError(formatApiError(err, 'Remise à zéro annulée sans validation de suppression.')); } finally { setBusy(false); }
  };

  const filterAudit = async () => { setBusy(true); try { const { data } = await platformApi.auditLogs({ clinic_id: id, limit: 500, ...Object.fromEntries(Object.entries(auditFilter).filter(([, value]) => value)) }); setAudit(data); } catch (err) { setError(formatApiError(err, 'Journal indisponible.')); } finally { setBusy(false); } };
  const exportAudit = async (type) => { try { const { data } = await httpClient.get(`/platform/audit-logs/export.${type}`, { params: { clinic_id: id }, responseType: 'blob' }); downloadBlob(data, `audit-${detail.name}.${type}`); } catch (err) { setError(formatApiError(err, 'Export impossible.')); } };
  const exportPatients = async () => { try { const { data } = await httpClient.get(`/platform/clinics/${id}/patients/export.csv`, { responseType: 'blob' }); downloadBlob(data, `patients-${detail.name}.csv`); } catch (err) { setError(formatApiError(err, 'Export patients impossible.')); } };
  const mergePatients = async (execute = false) => { if (!dialog?.target) return; setBusy(true); try { const { data } = await platformApi.mergePatients(id, { source_patient_id: dialog.target.source.id, target_patient_id: dialog.target.target.id, confirmation, reason, execute }); if (execute) { setMessage('Doublon fusionné et journalisé.'); setDialog(null); await loadAll(); } else setMergePreview(data); } catch (err) { setError(formatApiError(err, 'La fusion a été annulée.')); } finally { setBusy(false); } };

  if (loading) return <main className="clinical-page"><PageSkeleton lines={8} /></main>;
  if (!detail) return <main className="clinical-page"><ClinicalFeedback error={error || 'Clinique introuvable.'} /><Link to="/platform/clinics">← Cliniques</Link></main>;

  return <main className="clinical-page platform-clinic-detail" id="main-content">
    <Link to="/platform/clinics" className="platform-back-link">← Cliniques</Link>
    <header className="platform-admin-heading"><div><p className="clinical-eyebrow">Centre de contrôle · Clinique #{detail.id}</p><h1>{detail.name}</h1><p>{detail.city || 'Ville non renseignée'} · <strong>{detail.is_active ? 'Opérationnelle' : detail.archived_at ? 'Archivée' : 'Suspendue'}</strong></p></div><div className={`platform-health-signal platform-health-signal--${health?.status || 'attention'}`}><span aria-hidden="true" />{health?.status === 'ok' ? 'Systèmes stables' : 'Attention requise'}</div></header>
    <ClinicalFeedback error={error} message={message} />
    <nav className="platform-control-tabs" aria-label="Administration de la clinique">{TABS.map(([value, label]) => <button key={value} type="button" aria-current={tab === value ? 'page' : undefined} onClick={() => setTab(value)}>{label}</button>)}</nav>

    {tab === 'overview' && <div className="platform-control-grid">
      <section className="clinical-card platform-control-card platform-control-card--wide"><p className="clinical-eyebrow">Signal opérationnel</p><h2>{health?.status === 'ok' ? 'La clinique peut travailler normalement' : 'Des éléments demandent une vérification'}</h2><div className="platform-health-grid"><div><span>Version</span><strong>{health?.application_version}</strong></div><div><span>Base</span><strong>{health?.database}</strong></div><div><span>Sync en attente</span><strong>{health?.sync?.pending || 0}</strong></div><div><span>Conflits</span><strong>{health?.sync?.conflicts || 0}</strong></div><div><span>Dernier poste vu</span><strong>{formatDate(health?.workstation?.last_seen_at)}</strong></div><div><span>Dernière sauvegarde</span><strong>{formatDate(health?.backup?.last_at)}</strong></div></div></section>
      <section className="clinical-card platform-control-card"><p className="clinical-eyebrow">Identités</p><h2>{staff.length} membres</h2><p>{staff.filter((u) => u.is_active).length} actifs · {staff.filter((u) => u.mfa_enabled).length} avec MFA</p><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => setTab('staff')}>Gérer le personnel</button></section>
      <section className="clinical-card platform-control-card"><p className="clinical-eyebrow">Données</p><h2>{governance?.counts?.patients || 0} patients</h2><p>{governance?.duplicate_groups || 0} groupe(s) de doublons potentiels</p><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => setTab('data')}>Ouvrir la gouvernance</button></section>
      <section className="clinical-card platform-control-card platform-control-card--danger"><p className="clinical-eyebrow">État de l’établissement</p><h2>{detail.is_active ? 'Active' : 'Accès suspendu'}</h2><p>{detail.suspension_reason || 'Aucune restriction active.'}</p><div className="platform-actions-cell">{detail.is_active ? <button type="button" onClick={() => showDialog('suspend')}>Suspendre</button> : <button type="button" onClick={() => showDialog('reactivate')}>Réactiver</button>}<button type="button" className="platform-danger-link" onClick={() => showDialog('archive')}>Archiver</button></div></section>
    </div>}

    {tab === 'staff' && <section className="clinical-card platform-control-card--wide"><div className="platform-section-heading"><div><p className="clinical-eyebrow">Annuaire opérationnel</p><h2>Personnel</h2></div><span>{visibleStaff.length} résultat(s)</span></div>
      <div className="platform-account-filters"><label>Recherche<input type="search" autoComplete="off" placeholder="Nom ou e-mail…" value={staffQuery} onChange={(e) => { setStaffQuery(e.target.value); setPage(1); }} /></label><label>Rôle<select value={staffRole} onChange={(e) => setStaffRole(e.target.value)}><option value="">Tous</option>{STAFF_ROLES.map((role) => <option key={role} value={role}>{ROLE_LABELS[role] || role}</option>)}</select></label><label>Accès<select value={staffStatus} onChange={(e) => setStaffStatus(e.target.value)}><option value="">Tous</option><option value="active">Actifs</option><option value="inactive">Inactifs</option></select></label><label>Trier<select value={sort} onChange={(e) => setSort(e.target.value)}><option value="email">E-mail</option><option value="role">Rôle</option><option value="last_login_at">Dernière connexion</option></select></label></div>
      <div className="platform-staff-layout"><div className="users-table-wrap"><table className="users-table"><thead><tr><th>Identité</th><th>Rôle</th><th>Accès</th><th>Dernière connexion</th><th>Actions</th></tr></thead><tbody>{pageRows.map((u) => <tr key={u.id} className={!u.is_active ? 'platform-row-inactive' : ''}><td><strong>{u.full_name || u.email}</strong><span className="platform-table-sub">{u.email}</span></td><td>{ROLE_LABELS[u.role] || u.role}</td><td>{u.is_active ? 'Actif' : u.invitation_status ? 'Invitation en attente' : 'Inactif'}</td><td>{formatDate(u.last_login_at)}</td><td><button type="button" onClick={() => setSelectedStaff(u)}>Examiner</button></td></tr>)}</tbody></table></div>{selectedStaff && <aside className="platform-staff-drawer"><button type="button" className="platform-drawer-close" aria-label="Fermer le détail" onClick={() => setSelectedStaff(null)}>×</button><p className="clinical-eyebrow">Compte #{selectedStaff.id}</p><h3>{selectedStaff.full_name || selectedStaff.email}</h3><dl><dt>E-mail</dt><dd>{selectedStaff.email}</dd><dt>Créé</dt><dd>{formatDate(selectedStaff.created_at)}</dd><dt>Dernière connexion</dt><dd>{formatDate(selectedStaff.last_login_at)}</dd><dt>Sessions actives</dt><dd>{selectedStaff.active_sessions}</dd><dt>MFA</dt><dd>{selectedStaff.mfa_enabled ? 'Activée' : 'Non activée'}</dd><dt>Verrouillage</dt><dd>{selectedStaff.locked_until ? `Jusqu’au ${formatDate(selectedStaff.locked_until)}` : 'Aucun'}</dd></dl><label>Rôle<select value={selectedStaff.role} disabled={busy} onChange={(e) => changeRole(selectedStaff, e.target.value)}>{STAFF_ROLES.map((role) => <option key={role} value={role}>{ROLE_LABELS[role] || role}</option>)}</select></label><div className="platform-drawer-actions"><button type="button" onClick={() => showDialog('sessions', selectedStaff)}>Déconnecter toutes les sessions</button><button type="button" onClick={() => showDialog(selectedStaff.is_active ? 'deactivate' : 'reactivate', selectedStaff)}>{selectedStaff.is_active ? 'Désactiver' : 'Réactiver'}</button>{selectedStaff.invitation_status && !selectedStaff.is_active && <button type="button" className="platform-danger-link" onClick={() => showDialog('delete', selectedStaff)}>Supprimer l’invitation</button>}</div></aside>}</div>
      <div className="platform-pagination"><button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Précédent</button><span>Page {page} / {pages}</span><button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)}>Suivant</button></div>
      <form className="platform-invite-panel" onSubmit={inviteStaff}><div><p className="clinical-eyebrow">Nouvel accès</p><h3>Inviter un membre</h3><p>Aucun mot de passe ne sera affiché ou transmis par un administrateur.</p></div><label>Prénom<input required value={invite.first_name} onChange={(e) => setInvite({ ...invite, first_name: e.target.value })} /></label><label>Nom<input required value={invite.last_name} onChange={(e) => setInvite({ ...invite, last_name: e.target.value })} /></label><label>E-mail<input required type="email" autoComplete="email" spellCheck="false" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} /></label><label>Rôle<select value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>{STAFF_ROLES.map((role) => <option key={role} value={role}>{ROLE_LABELS[role] || role}</option>)}</select></label><button type="submit" className="clinical-btn" disabled={busy}>{busy ? 'Envoi…' : 'Envoyer l’invitation'}</button></form>
    </section>}

    {tab === 'security' && <div className="platform-control-grid"><section className="clinical-card platform-control-card--wide"><p className="clinical-eyebrow">Posture d’accès</p><h2>Sécurité du personnel</h2><div className="platform-health-grid"><div><span>MFA activée</span><strong>{staff.filter((u) => u.mfa_enabled).length} / {staff.length}</strong></div><div><span>Sessions actives</span><strong>{staff.reduce((sum, u) => sum + (u.active_sessions || 0), 0)}</strong></div><div><span>Comptes verrouillés</span><strong>{staff.filter((u) => u.locked_until).length}</strong></div><div><span>Échecs de connexion</span><strong>{staff.reduce((sum, u) => sum + (u.failed_login_attempts || 0), 0)}</strong></div></div><p>Examinez un compte dans Personnel pour révoquer immédiatement toutes ses sessions. La politique MFA est appliquée par la configuration serveur des rôles privilégiés.</p></section></div>}

    {tab === 'configuration' && config && <form className="clinical-card platform-configuration-form" onSubmit={saveConfiguration}><p className="clinical-eyebrow">Paramètres contrôlés</p><h2>Configuration de la clinique</h2><div className="platform-form-grid"><label>Nom<input required value={config.name} onChange={(e) => setConfig({ ...config, name: e.target.value })} /></label><label>Ville<input value={config.city} onChange={(e) => setConfig({ ...config, city: e.target.value })} /></label><label>Téléphone<input type="tel" value={config.phone} onChange={(e) => setConfig({ ...config, phone: e.target.value })} /></label><label>E-mail<input type="email" value={config.email} onChange={(e) => setConfig({ ...config, email: e.target.value })} /></label><label className="platform-field-wide">Adresse<textarea rows="2" value={config.address} onChange={(e) => setConfig({ ...config, address: e.target.value })} /></label><label>Modèle de reçu<select value={config.receipt_template} onChange={(e) => setConfig({ ...config, receipt_template: e.target.value })}><option value="aasma_standard">Standard AASMA</option><option value="compact">Compact</option></select></label><label>Version catalogue<input value={config.catalogue_version} onChange={(e) => setConfig({ ...config, catalogue_version: e.target.value })} /></label></div><fieldset><legend>Modules activés</legend><div className="platform-checkbox-grid">{MODULES.map((module) => <label key={module}><input type="checkbox" checked={config.enabled_modules?.includes(module)} onChange={(e) => setConfig({ ...config, enabled_modules: e.target.checked ? [...config.enabled_modules, module] : config.enabled_modules.filter((v) => v !== module) })} />{module}</label>)}</div></fieldset><fieldset><legend>Modes de paiement</legend><div className="platform-checkbox-grid">{PAYMENT_METHODS.map((method) => <label key={method}><input type="checkbox" checked={config.payment_methods?.includes(method)} onChange={(e) => setConfig({ ...config, payment_methods: e.target.checked ? [...config.payment_methods, method] : config.payment_methods.filter((v) => v !== method) })} />{method}</label>)}</div></fieldset><label className="platform-switch"><input type="checkbox" checked={config.offline_workstations_enabled} onChange={(e) => setConfig({ ...config, offline_workstations_enabled: e.target.checked })} />Autoriser les postes hors ligne</label><button type="submit" className="clinical-btn" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer la configuration'}</button></form>}

    {tab === 'audit' && <section className="clinical-card platform-control-card--wide"><div className="platform-section-heading"><div><p className="clinical-eyebrow">Traçabilité</p><h2>Journal d’audit</h2></div><div className="platform-actions-cell"><button type="button" onClick={() => exportAudit('csv')}>Exporter CSV</button><button type="button" onClick={() => exportAudit('pdf')}>Exporter PDF</button></div></div><div className="platform-account-filters"><label>Action<input value={auditFilter.action} onChange={(e) => setAuditFilter({ ...auditFilter, action: e.target.value })} placeholder="Ex. deactivate…" /></label><label>Du<input type="date" value={auditFilter.date_from} onChange={(e) => setAuditFilter({ ...auditFilter, date_from: e.target.value })} /></label><label>Au<input type="date" value={auditFilter.date_to} onChange={(e) => setAuditFilter({ ...auditFilter, date_to: e.target.value })} /></label><button type="button" onClick={filterAudit}>Appliquer</button></div><div className="platform-audit-timeline">{audit.length === 0 ? <p>Aucune entrée pour ces critères.</p> : audit.map((row) => <details key={row.id}><summary><time>{formatDate(row.timestamp)}</time><strong>{row.actor_email || `Utilisateur #${row.actor_id}`}</strong><span>{row.action} · {row.resource_type}{row.resource_id ? ` #${row.resource_id}` : ''}</span></summary><dl><dt>Clinique</dt><dd>{row.clinic_name || detail.name}</dd><dt>Raison</dt><dd>{row.reason || 'Non renseignée (entrée historique)'}</dd><dt>Adresse IP</dt><dd>{row.ip || 'Non disponible'}</dd><dt>Appareil</dt><dd>{row.user_agent || 'Non disponible'}</dd><dt>Avant</dt><dd><code>{JSON.stringify(row.before) || '—'}</code></dd><dt>Après</dt><dd><code>{JSON.stringify(row.after) || '—'}</code></dd></dl></details>)}</div></section>}

    {tab === 'data' && <div className="platform-control-grid"><section className="clinical-card platform-control-card--wide"><div className="platform-section-heading"><div><p className="clinical-eyebrow">Inventaire contrôlé</p><h2>Données de la clinique</h2></div><button type="button" onClick={exportPatients}>Exporter les patients CSV</button></div><div className="platform-data-inventory">{Object.entries(governance?.counts || {}).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><strong>{value}</strong></div>)}</div><p><strong>{governance?.duplicate_groups || 0}</strong> groupe(s) de doublons potentiels détectés. Chaque fusion exige une revue et le numéro du dossier conservé.</p>{governance?.duplicate_candidates?.map((group, index) => <article key={`${group.match.phone}-${index}`} className="platform-duplicate-group"><div><strong>{group.patients[0]?.first_name} {group.patients[0]?.last_name}</strong><span>{group.match.phone || 'Téléphone non renseigné'} · {group.patients.map((p) => p.patient_number || `#${p.id}`).join(' / ')}</span></div>{group.patients.length === 2 && <button type="button" onClick={() => showDialog('merge', { target: group.patients[0], source: group.patients[1] })}>Examiner la fusion</button>}</article>)}</section><section className="clinical-card platform-control-card--danger platform-control-card--wide"><p className="clinical-eyebrow">Zone irréversible</p><h2>Remettre les données patient à zéro</h2><p>Supprime les patients et leurs dossiers associés dans une transaction unique, conserve le personnel et la configuration, puis change la génération hors ligne afin d’empêcher la réapparition d’anciennes files.</p><button type="button" className="clinical-btn clinical-btn--danger" onClick={() => showDialog('reset-data')}>Préparer la remise à zéro</button></section></div>}

    {dialog && <div className="platform-modal-backdrop" role="presentation"><section className="clinical-card platform-modal platform-governance-dialog" role="dialog" aria-modal="true" aria-labelledby="governance-action-title"><p className="clinical-eyebrow">Confirmation auditée</p><h2 id="governance-action-title">{dialog.target?.email || (dialog.type === 'reset-data' ? 'Remise à zéro des données' : dialog.type === 'merge' ? 'Fusion de 2 dossiers' : `${dialog.type} · ${detail.name}`)}</h2><label htmlFor="governance-reason">Raison</label><textarea id="governance-reason" rows="3" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Motif opérationnel précis…" />{!dialog.target?.email && <label htmlFor="governance-confirmation">Saisissez exactement « {dialog.type === 'merge' ? (dialog.target?.target?.patient_number || dialog.target?.target?.id) : detail.name} »<input id="governance-confirmation" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} autoComplete="off" /></label>}{dialog.type === 'reset-data' && <label className="platform-switch"><input type="checkbox" checked={waiveBackup} onChange={(e) => setWaiveBackup(e.target.checked)} />Continuer sans sauvegarde vérifiée si aucune sauvegarde récente n’est disponible</label>}{mergePreview && <div className="platform-preview-list"><strong>Prévisualisation</strong><p>{Object.values(mergePreview.dependent_records || {}).reduce((sum, value) => sum + value, 0)} enregistrement(s) seront rattachés au dossier {mergePreview.target.patient_number}.</p></div>}<div className="platform-modal-actions"><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => setDialog(null)}>Annuler</button><button type="button" className={`clinical-btn${['deactivate', 'delete', 'suspend', 'archive', 'reset-data'].includes(dialog.type) ? ' clinical-btn--danger' : ''}`} disabled={busy || reason.trim().length < 3 || (!dialog.target?.email && confirmation !== (dialog.type === 'merge' ? (dialog.target?.target?.patient_number || String(dialog.target?.target?.id)) : detail.name))} onClick={dialog.type === 'merge' ? () => mergePatients(Boolean(mergePreview)) : dialog.target ? runStaffAction : dialog.type === 'reset-data' ? resetData : changeClinicState}>{busy ? 'Traitement…' : dialog.type === 'merge' ? mergePreview ? 'Confirmer la fusion' : 'Prévisualiser la fusion' : 'Confirmer l’action'}</button></div></section></div>}
  </main>;
}
