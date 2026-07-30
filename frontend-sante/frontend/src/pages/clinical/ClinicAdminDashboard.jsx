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
import './clinical.css';

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
  const [staffForm, setStaffForm] = useState({
    email: '',
    password: '',
    role: 'receptionist',
  });
  const [resetBusyId, setResetBusyId] = useState(null);

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

  useEffect(() => {
    loadCompliance();
    if (clinicId) {
      loadClinicStaff(clinicId);
    }
  }, [clinicId]);

  const resetStaffPassword = async (staffUser) => {
    if (!clinicId || !staffUser?.id) return;
    const temporary = window.prompt(
      `Nouveau mot de passe temporaire pour ${staffUser.email} (min. 8 caractères) :`,
    );
    if (!temporary) return;
    setError('');
    setMessage('');
    setResetBusyId(staffUser.id);
    try {
      await clinicalApi.resetStaffPassword(staffUser.id, {
        clinic_id: Number(clinicId),
        new_password: temporary,
      });
      setMessage(
        `Mot de passe réinitialisé pour ${staffUser.email}. L’utilisateur devra le changer à la prochaine connexion.`,
      );
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
      setStaffForm((prev) => ({ ...prev, email: '', password: '' }));
      loadCompliance();
      loadClinicStaff(clinicId);
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

  return (
    <div className="clinical-page clinical-page--clinic-admin">
      <header className="clinical-page-header">
        <p className="clinical-eyebrow">Pilotage clinique</p>
        <h1>Administration — {user?.clinic_name || 'Ma clinique'}</h1>
        <p className="clinical-lead">
          Gestion du personnel et suivi d&apos;activité pour votre établissement uniquement.
          La création de nouvelles cliniques est réservée au propriétaire plateforme.
        </p>
      </header>

      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

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
        <section className="clinical-card" style={{ marginTop: '1rem' }}>
          <h2>Sauvegarde quotidienne</h2>
          <p className={backupStatus.status === 'ok' ? 'clinical-success' : 'clinical-error'}>
            {backupStatus.message}
          </p>
        </section>
      )}

      <section id="clinic-audit" className="clinical-card" style={{ marginTop: '1rem' }}>
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

      <section id="clinic-staff" className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Personnel ({clinicStaff.length})</h2>
        {clinicStaff.length === 0 ? (
          <p className="clinical-muted">Aucun membre — créez un compte ci-dessous.</p>
        ) : (
          <table className="clinical-stock-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Rôle</th>
                <th>Actif</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clinicStaff.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td><span className="clinical-badge">{u.role}</span></td>
                  <td>{u.is_active ? 'Oui' : 'Non'}</td>
                  <td>
                    {u.id !== user?.id && u.is_active ? (
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        disabled={resetBusyId === u.id}
                        onClick={() => resetStaffPassword(u)}
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
        )}
      </section>

      <section className="clinical-card" id="create-user" style={{ marginTop: '1rem' }}>
        <h2>Créer un compte personnel</h2>
        <p className="clinical-lead">
          Comptes pour votre clinique : réception, médecin, laboratoire, pharmacie, caisse, nutrition, sage-femme.
        </p>
        <form onSubmit={createStaff}>
          <div className="clinical-field">
            <label>Clinique</label>
            <input
              value={user?.clinic_name ? `${user.clinic_name} (#${clinicId})` : `#${clinicId || '—'}`}
              readOnly
              disabled
            />
          </div>
          <div className="clinical-field">
            <label>Email</label>
            <input
              type="email"
              value={staffForm.email}
              onChange={(e) => setStaffForm({ ...staffForm, email: e.target.value })}
              required
            />
          </div>
          <div className="clinical-field">
            <label>Mot de passe</label>
            <input
              type="password"
              value={staffForm.password}
              onChange={(e) => setStaffForm({ ...staffForm, password: e.target.value })}
              required
            />
          </div>
          <div className="clinical-field">
            <label>Rôle</label>
            <select
              value={staffForm.role}
              onChange={(e) => setStaffForm({ ...staffForm, role: e.target.value })}
            >
              {STAFF_ROLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <button type="submit" className="clinical-btn">Créer le compte</button>
        </form>
      </section>
    </div>
  );
}
