/** Platform account inventory and guarded technical-account governance. */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import platformApi from '../../services/platformApi.js';
import { formatApiError } from '../../utils/apiError.js';
import PageSkeleton from '../../components/ui/PageSkeleton.jsx';
import '../Users.css';
import './PlatformOwner.css';

const FILTERS = [['all', 'Tous'], ['production', 'Production'], ['test', 'Test'], ['technical', 'Technique'], ['unknown', 'À examiner']];
const CATEGORY_LABELS = { production: 'Production', test: 'Test', technical: 'Technique', unknown: 'À examiner' };

function formatDate(value) {
  if (!value) return 'Jamais';
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export default function PlatformAccounts() {
  const [params, setParams] = useSearchParams();
  const filter = params.get('type') || 'all';
  const search = params.get('q') || '';
  const clinic = params.get('clinic') || '';
  const role = params.get('role') || '';
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selected, setSelected] = useState([]);
  const [dialog, setDialog] = useState(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);

  const updateParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };

  const fetchUsers = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const { data } = await platformApi.listAccounts({
        category: filter, ...(search ? { search } : {}), ...(clinic ? { clinic_id: Number(clinic) } : {}), ...(role ? { role } : {}),
      });
      setUsers(Array.isArray(data) ? data : []);
      setSelected((current) => current.filter((id) => (data || []).some((row) => row.id === id)));
    } catch (err) { setError(formatApiError(err, 'Impossible de charger les comptes.')); }
    finally { setLoading(false); }
  }, [filter, search, clinic, role]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const clinics = useMemo(() => Array.from(new Map(users.filter((u) => u.clinic_id).map((u) => [u.clinic_id, u.clinic_name || `Clinique #${u.clinic_id}`])).entries()), [users]);
  const roles = useMemo(() => [...new Set(users.map((u) => u.role))].sort(), [users]);
  const allSelected = users.length > 0 && users.every((u) => selected.includes(u.id));

  const openAction = (action, user = null) => {
    setDialog({ action, user, ids: user ? [user.id] : selected }); setReason(''); setPreview(null); setError(''); setMessage('');
  };

  const runAction = async (execute = false) => {
    if (!dialog || reason.trim().length < 3) return;
    setBusy(true); setError('');
    try {
      if (dialog.user) {
        const user = dialog.user;
        if (!user.clinic_id) throw new Error('Ce compte doit être examiné et rattaché à une clinique avant toute action.');
        if (dialog.action === 'deactivate') await platformApi.deactivateStaff(user.clinic_id, user.id, reason);
        else if (dialog.action === 'reactivate') await platformApi.reactivateStaff(user.clinic_id, user.id, reason);
        else if (dialog.action === 'delete') await platformApi.deleteStaff(user.clinic_id, user.id, reason);
        else await platformApi.revokeStaffSessions(user.clinic_id, user.id, reason);
        setMessage(`Action terminée pour ${user.email}.`); setDialog(null); await fetchUsers();
      } else {
        const { data } = await platformApi.bulkAccounts({ user_ids: dialog.ids, action: dialog.action, reason, execute });
        if (!execute) setPreview(data);
        else { setMessage('Traitement groupé terminé. Vérifiez les résultats ci-dessous.'); setPreview(data); setSelected([]); await fetchUsers(); }
      }
    } catch (err) { setError(formatApiError(err, 'Action impossible.')); }
    finally { setBusy(false); }
  };

  return (
    <section className="users-page platform-accounts-page" aria-label="Comptes et accès">
      <div className="users-page-inner">
        <Link to="/platform/overview" className="platform-back-link">← Vue d’ensemble</Link>
        <header className="platform-admin-heading">
          <div><p className="clinical-eyebrow">Gouvernance des identités</p><h1>Comptes & accès</h1><p>Classez les identités, examinez les connexions et appliquez les mêmes protections dans chaque clinique.</p></div>
          <div className="platform-admin-heading__signal"><strong>{users.length}</strong><span>comptes dans cette vue</span></div>
        </header>
        <div aria-live="polite">{error && <p className="clinical-error" role="alert">{error}</p>}{message && <p className="clinical-success">{message}</p>}</div>

        <section className="platform-command-bar" aria-label="Filtres des comptes">
          <div className="platform-filter-tabs" role="tablist" aria-label="Catégorie">
            {FILTERS.map(([value, label]) => <button key={value} type="button" role="tab" aria-selected={filter === value} className={`platform-filter-tab${filter === value ? ' platform-filter-tab--active' : ''}`} onClick={() => updateParam('type', value)}>{label}</button>)}
          </div>
          <div className="platform-account-filters">
            <label>Recherche<input name="account-search" type="search" autoComplete="off" placeholder="E-mail…" value={search} onChange={(e) => updateParam('q', e.target.value)} /></label>
            <label>Clinique<select name="clinic" value={clinic} onChange={(e) => updateParam('clinic', e.target.value)}><option value="">Toutes</option>{clinics.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
            <label>Rôle<select name="role" value={role} onChange={(e) => updateParam('role', e.target.value)}><option value="">Tous</option>{roles.map((value) => <option key={value}>{value}</option>)}</select></label>
            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={fetchUsers} disabled={loading}>{loading ? 'Actualisation…' : 'Actualiser'}</button>
          </div>
        </section>

        {selected.length > 0 && <section className="platform-selection-bar" aria-label="Actions groupées"><strong>{selected.length} sélectionné(s)</strong><button type="button" onClick={() => openAction('deactivate')}>Prévisualiser la désactivation</button><button type="button" onClick={() => openAction('reactivate')}>Prévisualiser la réactivation</button><button type="button" className="platform-danger-link" onClick={() => openAction('delete')}>Prévisualiser la suppression</button></section>}

        {loading ? <PageSkeleton lines={7} /> : users.length === 0 ? <div className="platform-empty-state"><h2>Aucun compte</h2><p>Modifiez les filtres ou vérifiez l’établissement sélectionné.</p></div> : (
          <div className="users-table-wrap" tabIndex="0" role="region" aria-label="Inventaire des comptes">
            <table className="users-table platform-accounts-table">
              <thead><tr><th><input type="checkbox" aria-label="Sélectionner tous les comptes affichés" checked={allSelected} onChange={(e) => setSelected(e.target.checked ? users.map((u) => u.id) : [])} /></th><th>Identité</th><th>Catégorie</th><th>Clinique / rôle</th><th>Dernière connexion</th><th>Sécurité</th><th>Actions</th></tr></thead>
              <tbody>{users.map((user) => <tr key={user.id} className={!user.is_active ? 'platform-row-inactive' : ''}>
                <td><input type="checkbox" aria-label={`Sélectionner ${user.email}`} checked={selected.includes(user.id)} onChange={(e) => setSelected((current) => e.target.checked ? [...current, user.id] : current.filter((id) => id !== user.id))} /></td>
                <td><strong>{user.email}</strong><span className="platform-table-sub">Créé {formatDate(user.created_at)} · {user.is_active ? 'Actif' : 'Inactif'}</span></td>
                <td><span className={`platform-account-category platform-account-category--${user.category}`}>{CATEGORY_LABELS[user.category]}</span><span className="platform-table-sub">{user.classification_reasons?.[0]}</span></td>
                <td>{user.clinic_id ? <Link to={`/platform/clinics/${user.clinic_id}`}>{user.clinic_name || `#${user.clinic_id}`}</Link> : 'Non rattaché'}<span className="platform-table-sub">{user.role}</span></td>
                <td>{formatDate(user.last_login_at)}</td>
                <td><strong>{user.active_sessions} session(s)</strong><span className="platform-table-sub">MFA {user.mfa_enabled ? 'activée' : 'non activée'}{user.locked_until ? ' · verrouillé' : ''}</span></td>
                <td><div className="platform-actions-cell">{user.clinic_id && <><button type="button" onClick={() => openAction(user.is_active ? 'deactivate' : 'reactivate', user)}>{user.is_active ? 'Désactiver' : 'Réactiver'}</button><button type="button" onClick={() => openAction('sessions', user)}>Déconnecter</button>{user.can_delete && <button type="button" className="platform-danger-link" onClick={() => openAction('delete', user)}>Supprimer</button>}</>}</div></td>
              </tr>)}</tbody>
            </table>
          </div>
        )}

        {dialog && <div className="platform-modal-backdrop" role="presentation"><section className="clinical-card platform-modal platform-governance-dialog" role="dialog" aria-modal="true" aria-labelledby="account-action-title"><p className="clinical-eyebrow">Action sensible</p><h2 id="account-action-title">{dialog.user ? dialog.user.email : `${dialog.ids.length} comptes`}</h2><p>Indiquez une raison exploitable dans le journal d’audit. Une prévisualisation est obligatoire pour les actions groupées.</p><label htmlFor="account-action-reason">Raison</label><textarea id="account-action-reason" name="reason" rows="3" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Ex. Fin de contrat, compte de test terminé…" />
          {preview && <div className="platform-preview-list"><strong>Prévisualisation</strong><ul>{preview.items.map((item) => <li key={item.id} className={item.eligible ? '' : 'platform-preview-list__blocked'}>{item.email} — {item.completed ? 'terminé' : item.eligible ? 'autorisé' : item.reason}</li>)}</ul></div>}
          <div className="platform-modal-actions"><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => setDialog(null)}>Annuler</button>{!dialog.user && preview ? <button type="button" className="clinical-btn clinical-btn--danger" disabled={busy} onClick={() => runAction(true)}>{busy ? 'Traitement…' : 'Confirmer l’action groupée'}</button> : <button type="button" className={`clinical-btn${dialog.action === 'delete' || dialog.action === 'deactivate' ? ' clinical-btn--danger' : ''}`} disabled={busy || reason.trim().length < 3} onClick={() => runAction(false)}>{busy ? 'Vérification…' : dialog.user ? 'Confirmer' : 'Prévisualiser'}</button>}</div></section></div>}
      </div>
    </section>
  );
}
