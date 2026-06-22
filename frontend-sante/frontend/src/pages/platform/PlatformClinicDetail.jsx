/**
 * PlatformClinicDetail — per-clinic staff management.
 * Temp passwords are generated only on explicit create or confirmed reset.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  CLINIC_MODULES,
  ROLE_LABELS,
  createClinicStaff,
  deactivateClinicStaff,
  filterStaffByModule,
  getModuleById,
  loadClinicDetail,
  loadClinicStaff,
  reactivateClinicStaff,
  resetClinicStaffPassword,
} from '../../services/platformClinicData.js';
import { formatApiError } from '../../utils/apiError.js';
import {
  displaySessionPassword,
  genStaffPassword,
  loadSessionCreds,
  saveSessionCred,
} from '../../utils/staffSessionCreds.js';
import { copyToClipboard } from '../../components/PasswordInput.jsx';
import ClinicalStatGrid from '../clinical/ClinicalStatGrid.jsx';
import '../clinical/clinical.css';
import './PlatformOwner.css';

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return '—';
  }
}

export default function PlatformClinicDetail() {
  const { clinicId, section } = useParams();
  const numericId = Number(clinicId);
  const activeModule = section ? getModuleById(section) : null;

  const [detail, setDetail] = useState(null);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', role: 'receptionist' });
  const [resetTarget, setResetTarget] = useState(null);
  const [resetStep, setResetStep] = useState('confirm');
  const [resetPassword, setResetPassword] = useState('');
  const [resetBusy, setResetBusy] = useState(false);
  const [copyHint, setCopyHint] = useState('');
  const [sessionCreds, setSessionCreds] = useState(() => loadSessionCreds(numericId));

  useEffect(() => {
    setSessionCreds(loadSessionCreds(numericId));
  }, [numericId]);

  const loadAll = useCallback(async () => {
    if (!numericId) return;
    setLoading(true);
    setError('');
    try {
      const [detailData, staffData] = await Promise.all([
        loadClinicDetail(numericId),
        loadClinicStaff(numericId),
      ]);
      setDetail(detailData);
      setStaff(staffData);
    } catch (err) {
      setError(formatApiError(err, 'Clinique introuvable'));
      setDetail(null);
      setStaff([]);
    } finally {
      setLoading(false);
    }
  }, [numericId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (activeModule) {
      setForm((f) => ({ ...f, role: activeModule.createRole }));
    }
  }, [activeModule]);

  const visibleStaff = useMemo(
    () => (activeModule ? filterStaffByModule(staff, activeModule) : staff),
    [staff, activeModule]
  );

  const stats = useMemo(
    () =>
      detail
        ? [
            { label: 'Personnel', value: detail.staff_count ?? staff.length, variant: 'accent' },
            { label: 'Patients', value: detail.patient_count ?? '—', variant: 'success' },
            {
              label: 'Consultations',
              value: detail.consultation_count ?? '—',
            },
          ]
        : [],
    [detail, staff.length]
  );

  const openCreateForm = () => {
    setShowForm((open) => {
      if (open) return false;
      setForm((f) => ({
        ...f,
        password: f.password || genStaffPassword(),
        role: activeModule?.createRole || f.role,
      }));
      return true;
    });
  };

  const handleCopyPassword = async (password) => {
    const ok = await copyToClipboard(password);
    setCopyHint(ok ? 'Copié !' : 'Copie impossible');
    setTimeout(() => setCopyHint(''), 2000);
  };

  const createStaff = async (e) => {
    e.preventDefault();
    setError('');
    const password = form.password || genStaffPassword();
    try {
      const data = await createClinicStaff({
        clinicId: numericId,
        email: form.email.trim(),
        password,
        role: form.role,
      });
      saveSessionCred(numericId, data.id, password);
      setSessionCreds(loadSessionCreds(numericId));
      setMessage(`Compte créé : ${data.email} — mot de passe : ${password}`);
      setForm({ email: '', password: '', role: activeModule?.createRole || form.role });
      setShowForm(false);
      loadAll();
    } catch (err) {
      setError(formatApiError(err, 'Création impossible'));
    }
  };

  const toggleStatus = async (member) => {
    setError('');
    try {
      if (member.is_active) {
        await deactivateClinicStaff({ clinicId: numericId, userId: member.id });
        setMessage(`${member.email} désactivé`);
      } else {
        await reactivateClinicStaff(member.id);
        setMessage(`${member.email} réactivé`);
      }
      loadAll();
    } catch (err) {
      setError(formatApiError(err, 'Mise à jour impossible'));
    }
  };

  const openResetDialog = (member) => {
    setResetTarget(member);
    setResetStep('confirm');
    setResetPassword('');
    setResetBusy(false);
  };

  const closeResetDialog = () => {
    setResetTarget(null);
    setResetStep('confirm');
    setResetPassword('');
    setResetBusy(false);
  };

  const confirmReset = async () => {
    if (!resetTarget || resetBusy) return;
    setError('');
    setResetBusy(true);
    const password = genStaffPassword();
    try {
      await resetClinicStaffPassword({
        clinicId: numericId,
        userId: resetTarget.id,
        newPassword: password,
      });
      saveSessionCred(numericId, resetTarget.id, password);
      setSessionCreds(loadSessionCreds(numericId));
      setResetPassword(password);
      setResetStep('done');
      setMessage(`Mot de passe réinitialisé pour ${resetTarget.email}`);
    } catch (err) {
      setError(formatApiError(err, 'Réinitialisation impossible'));
      closeResetDialog();
    } finally {
      setResetBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="clinical-page">
        <p className="clinical-lead">Chargement…</p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="clinical-page">
        <p className="clinical-error">{error || 'Clinique introuvable'}</p>
        <Link to="/platform/clinics" className="platform-back-link">← Cliniques</Link>
      </div>
    );
  }

  return (
    <div className="clinical-page platform-clinic-detail">
      <Link to="/platform/clinics" className="platform-back-link">← Cliniques</Link>

      <header className="clinical-page-header">
        <p className="clinical-eyebrow">Clinique #{detail.id}</p>
        <h1>{detail.name}</h1>
        <p className="clinical-lead">
          {detail.city || 'Conakry'} ·{' '}
          <span className={`platform-status platform-status--${detail.is_active ? 'active' : 'archived'}`}>
            {detail.status}
          </span>
        </p>
      </header>

      {error && <p className="clinical-error">{error}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <div className="platform-detail-grid">
        <section className="clinical-card">
          <h2>Informations</h2>
          <dl className="platform-info-list">
            <div><dt>Adresse</dt><dd>{detail.address || '—'}</dd></div>
            <div><dt>Téléphone</dt><dd>{detail.phone || '—'}</dd></div>
            <div><dt>Créée le</dt><dd>{formatDate(detail.created_at)}</dd></div>
          </dl>
        </section>
        <section className="clinical-card">
          <h2>Administrateur</h2>
          <p><strong>{detail.admin_email || 'Non assigné'}</strong></p>
        </section>
        <section className="clinical-card">
          <h2>Personnel par rôle</h2>
          {detail.role_breakdown?.length ? (
            <ul className="platform-role-breakdown">
              {detail.role_breakdown.map((row) => (
                <li key={row.role}>
                  {row.label} <strong>({row.count})</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p className="clinical-lead">Aucun personnel.</p>
          )}
        </section>
      </div>

      <section className="clinical-card">
        <h2>Modules — {detail.name}</h2>
        <div className="platform-module-grid">
          {CLINIC_MODULES.map((mod) => {
            const count = filterStaffByModule(staff, mod).length;
            const isActive = activeModule?.id === mod.id;
            return (
              <Link
                key={mod.id}
                to={`/platform/clinics/${numericId}/${mod.id}`}
                className={`platform-module-card${isActive ? ' platform-module-card--active' : ''}`}
              >
                <h3>{mod.label}</h3>
                <p>{count} compte(s)</p>
                <span className="platform-module-card__cta">Gérer →</span>
              </Link>
            );
          })}
        </div>
        {activeModule && (
          <p className="clinical-lead">
            <Link to={`/platform/clinics/${numericId}`}>← Vue générale clinique</Link>
          </p>
        )}
      </section>

      <section className="clinical-card platform-staff-section">
        <div className="platform-staff-header">
          <h2>
            {activeModule ? `${activeModule.label} — personnel` : 'Tout le personnel'}
            {' '}({visibleStaff.length})
          </h2>
          <button type="button" className="clinical-btn" onClick={openCreateForm}>
            {showForm ? 'Annuler' : `+ Créer ${ROLE_LABELS[activeModule?.createRole || 'receptionist'] || 'compte'}`}
          </button>
        </div>

        {showForm && (
          <form className="platform-staff-form" onSubmit={createStaff}>
            <div className="platform-form-grid">
              <div className="clinical-field">
                <label>Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </div>
              <div className="clinical-field">
                <label>Mot de passe temporaire</label>
                <input
                  type="text"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required
                />
              </div>
              {!activeModule && (
                <div className="clinical-field">
                  <label>Rôle</label>
                  <select
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                  >
                    {['clinic_admin', 'receptionist', 'cashier', 'doctor', 'lab_technician', 'pharmacist'].map(
                      (r) => (
                        <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>
                      )
                    )}
                  </select>
                </div>
              )}
            </div>
            <button type="submit" className="clinical-btn">Créer le compte</button>
          </form>
        )}

        <table className="clinical-stock-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Rôle</th>
              <th>Mot de passe temp.</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleStaff.length === 0 ? (
              <tr>
                <td colSpan={5} className="clinical-lead">Aucun compte pour ce module.</td>
              </tr>
            ) : (
              visibleStaff.map((member) => (
                <tr key={member.id} className={!member.is_active ? 'platform-row-inactive' : ''}>
                  <td>{member.email}</td>
                  <td><span className="clinical-badge">{ROLE_LABELS[member.role] || member.role}</span></td>
                  <td>{displaySessionPassword(sessionCreds, member.id)}</td>
                  <td>{member.is_active ? 'Actif' : 'Inactif'}</td>
                  <td className="platform-actions-cell">
                    <button type="button" className="platform-action-btn" onClick={() => toggleStatus(member)}>
                      {member.is_active ? 'Désactiver' : 'Réactiver'}
                    </button>
                    <button
                      type="button"
                      className="platform-action-btn"
                      onClick={() => openResetDialog(member)}
                    >
                      Réinitialiser MDP
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      {resetTarget && (
        <div className="platform-modal-backdrop" role="dialog" aria-modal="true">
          <div className="clinical-card platform-modal">
            {resetStep === 'confirm' ? (
              <>
                <h2>Réinitialiser le mot de passe ?</h2>
                <p className="clinical-lead">
                  Un nouveau mot de passe temporaire sera généré pour <strong>{resetTarget.email}</strong>.
                  L&apos;utilisateur devra le changer à la première connexion.
                </p>
                <div className="platform-modal-actions">
                  <button type="button" className="clinical-btn clinical-btn--ghost" onClick={closeResetDialog}>
                    Annuler
                  </button>
                  <button
                    type="button"
                    className="clinical-btn"
                    onClick={confirmReset}
                    disabled={resetBusy}
                  >
                    {resetBusy ? 'Génération…' : 'Confirmer la réinitialisation'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2>Mot de passe réinitialisé</h2>
                <p className="clinical-lead">{resetTarget.email}</p>
                <div className="clinical-field">
                  <label>Nouveau mot de passe temporaire (affiché une seule fois)</label>
                  <div className="password-copy-row">
                    <input type="text" value={resetPassword} readOnly />
                    <button
                      type="button"
                      className="password-copy-btn"
                      onClick={() => handleCopyPassword(resetPassword)}
                    >
                      Copier
                    </button>
                  </div>
                  {copyHint && <p className="clinical-lead">{copyHint}</p>}
                </div>
                <div className="platform-modal-actions">
                  <button type="button" className="clinical-btn" onClick={closeResetDialog}>
                    Fermer
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
