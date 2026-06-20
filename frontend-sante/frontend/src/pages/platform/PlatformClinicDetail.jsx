/**
 * Dedicated clinic dashboard — one clinic only, no cross-clinic mixing.
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
import ClinicalStatGrid from '../clinical/ClinicalStatGrid.jsx';
import '../clinical/clinical.css';
import './PlatformOwner.css';

function genPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
  let s = 'Clinic';
  for (let i = 0; i < 6; i += 1) s += chars[Math.floor(Math.random() * chars.length)];
  return `${s}!`;
}

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
  const [form, setForm] = useState({ email: '', password: genPassword(), role: 'receptionist' });
  const [resetTarget, setResetTarget] = useState(null);
  const [resetPassword, setResetPassword] = useState('');
  const [createdPasswords, setCreatedPasswords] = useState({});

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
      setForm((f) => ({ ...f, role: activeModule.createRole, password: genPassword() }));
      setShowForm(true);
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

  const createStaff = async (e) => {
    e.preventDefault();
    setError('');
    const password = form.password || genPassword();
    try {
      const data = await createClinicStaff({
        clinicId: numericId,
        email: form.email.trim(),
        password,
        role: form.role,
      });
      setCreatedPasswords((prev) => ({ ...prev, [data.id]: password }));
      setMessage(`Compte créé : ${data.email} — mot de passe : ${password}`);
      setForm({ email: '', password: genPassword(), role: activeModule?.createRole || form.role });
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

  const submitReset = async (e) => {
    e.preventDefault();
    if (!resetTarget) return;
    setError('');
    try {
      await resetClinicStaffPassword({
        clinicId: numericId,
        userId: resetTarget.id,
        newPassword: resetPassword,
      });
      setCreatedPasswords((prev) => ({ ...prev, [resetTarget.id]: resetPassword }));
      setMessage(`Mot de passe réinitialisé pour ${resetTarget.email}`);
      setResetTarget(null);
      setResetPassword('');
    } catch (err) {
      setError(formatApiError(err, 'Réinitialisation impossible'));
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
          <button type="button" className="clinical-btn" onClick={() => setShowForm((v) => !v)}>
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
                  <td>{createdPasswords[member.id] || '—'}</td>
                  <td>{member.is_active ? 'Actif' : 'Inactif'}</td>
                  <td className="platform-actions-cell">
                    <button type="button" className="platform-action-btn" onClick={() => toggleStatus(member)}>
                      {member.is_active ? 'Désactiver' : 'Réactiver'}
                    </button>
                    <button
                      type="button"
                      className="platform-action-btn"
                      onClick={() => {
                        setResetTarget(member);
                        setResetPassword(genPassword());
                      }}
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
          <form className="clinical-card platform-modal" onSubmit={submitReset}>
            <h2>Réinitialiser le mot de passe</h2>
            <p className="clinical-lead">{resetTarget.email}</p>
            <div className="clinical-field">
              <label>Nouveau mot de passe</label>
              <input
                type="text"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <div className="platform-modal-actions">
              <button type="button" className="clinical-btn clinical-btn--ghost" onClick={() => setResetTarget(null)}>
                Annuler
              </button>
              <button type="submit" className="clinical-btn">Confirmer</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
