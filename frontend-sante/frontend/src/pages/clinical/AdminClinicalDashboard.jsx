import { useEffect, useState } from 'react';

import { Link } from 'react-router-dom';

import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';

import httpClient from '../../services/httpClient';

import { formatApiError } from '../../utils/apiError.js';
import { formatGNF } from '../../utils/appointmentPresentation.js';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';

import './clinical.css';



export default function AdminClinicalDashboard() {

  const { user } = useAuth();

  const [message, setMessage] = useState('');

  const [error, setError] = useState('');

  const [auditLogs, setAuditLogs] = useState([]);

  const [backupStatus, setBackupStatus] = useState(null);

  const [activity, setActivity] = useState(null);

  const [users, setUsers] = useState([]);

  const [clinicStaff, setClinicStaff] = useState([]);

  const [clinicForm, setClinicForm] = useState({ name: '', city: 'Conakry', phone: '', address: '' });

  const [staffForm, setStaffForm] = useState({

    email: '',

    password: '',

    role: 'receptionist',

    clinic_id: '',

  });



  const loadClinicStaff = async (clinicId) => {

    if (!clinicId) return;

    try {

      const { data } = await clinicalApi.listStaff(Number(clinicId));

      setClinicStaff(data || []);

    } catch {

      setClinicStaff([]);

    }

  };



  const loadCompliance = async () => {

    try {

      const usersPromise =
        user?.role === 'platform_owner'
          ? httpClient.get('/platform/users').catch(() => ({ data: [] }))
          : Promise.resolve({ data: [] });

      const [logs, backup, reception, doctor, lab, pharmacy, charges, revenue, usersRes] = await Promise.all([

        clinicalApi.auditLogs({ limit: 30 }),

        clinicalApi.backupStatus(),

        clinicalApi.receptionQueue().catch(() => ({ data: [] })),

        clinicalApi.doctorQueue().catch(() => ({ data: [] })),

        clinicalApi.labQueue().catch(() => ({ data: [] })),

        clinicalApi.pharmacyQueue().catch(() => ({ data: [] })),

        clinicalApi.pendingCharges().catch(() => ({ data: [] })),

        clinicalApi.dailyRevenue().catch(() => ({ data: null })),

        usersPromise,

      ]);

      setAuditLogs(logs.data || []);

      setBackupStatus(backup.data || null);

      setUsers(usersRes.data || []);

      setActivity({

        reception: (reception.data || []).length,

        doctor: (doctor.data || []).length,

        lab: (lab.data || []).length,

        pharmacy: (pharmacy.data || []).length,

        pendingCharges: (charges.data || []).length,

        revenue: revenue.data,

      });

    } catch {

      /* admin may not have clinic yet */

    }

  };



  useEffect(() => {
    loadCompliance();
    if (user?.clinic_id && !staffForm.clinic_id) {
      setStaffForm((prev) => ({ ...prev, clinic_id: String(user.clinic_id) }));
      loadClinicStaff(user.clinic_id);
    }
  }, [user?.clinic_id, user?.role]);



  useEffect(() => {

    if (staffForm.clinic_id) {

      loadClinicStaff(staffForm.clinic_id);

    }

  }, [staffForm.clinic_id]);



  const createClinic = async (e) => {

    e.preventDefault();

    setError('');

    try {

      const { data } = await clinicalApi.createClinic(clinicForm);

      setMessage(`Clinique créée : ${data.name} (#${data.id})`);

      setStaffForm((prev) => ({ ...prev, clinic_id: String(data.id) }));

      loadCompliance();

    } catch (err) {

      setError(formatApiError(err, 'Création clinique impossible'));

    }

  };



  const createStaff = async (e) => {

    e.preventDefault();

    setError('');

    const chosenPassword = staffForm.password;

    try {

      const { data } = await clinicalApi.createStaff({

        ...staffForm,

        clinic_id: Number(staffForm.clinic_id),

      });

      setMessage(

        `Compte ${data.role} créé : ${data.email} — connectez-vous avec le mot de passe saisi (${chosenPassword})`

      );

      setStaffForm((prev) => ({ ...prev, password: '' }));

      loadCompliance();

      loadClinicStaff(staffForm.clinic_id);

    } catch (err) {

      setError(formatApiError(err, 'Création compte impossible'));

    }

  };



  const stats = activity

    ? [

        { label: 'Réception (RDV)', value: activity.reception, variant: 'accent' },

        { label: 'File médecin', value: activity.doctor },

        { label: 'Examens labo', value: activity.lab, variant: 'warning' },

        { label: 'Ordonnances pharma', value: activity.pharmacy },

        { label: 'Utilisateurs', value: users.length, variant: 'success' },

        {

          label: 'Encaissé aujourd\'hui',

          value: formatGNF(activity.revenue?.total_collected_gnf || 0),

        },

      ]

    : [];



  return (

    <div className="clinical-page">

      <h1>Tableau de bord — Administration</h1>

      <p className="clinical-lead">Conformité, utilisateurs, activité clinique et recettes.</p>

      {error && <p className="clinical-error">{String(error)}</p>}

      {message && <p className="clinical-success">{message}</p>}



      <ClinicalStatGrid stats={stats} />



      <nav className="clinical-section-nav" aria-label="Sections admin">

        <a href="#admin-activity">Activité</a>

        <a href="#admin-audit">Audit</a>

        <a href="#admin-users">Utilisateurs</a>

        <Link to="/clinical/revenue">Recettes →</Link>

      </nav>



      {activity && (

        <section id="admin-activity" className="clinical-card">

          <h2>Activité clinique en direct</h2>

          <div className="clinical-activity-grid">

            <div className="clinical-activity-item">

              <span className="clinical-stat-label">Réception</span>

              <strong>{activity.reception}</strong>

              <span className="clinical-stat-hint">rendez-vous / file</span>

            </div>

            <div className="clinical-activity-item">

              <span className="clinical-stat-label">Médecin</span>

              <strong>{activity.doctor}</strong>

              <span className="clinical-stat-hint">patients en attente</span>

            </div>

            <div className="clinical-activity-item">

              <span className="clinical-stat-label">Laboratoire</span>

              <strong>{activity.lab}</strong>

              <span className="clinical-stat-hint">examens actifs</span>

            </div>

            <div className="clinical-activity-item">

              <span className="clinical-stat-label">Pharmacie</span>

              <strong>{activity.pharmacy}</strong>

              <span className="clinical-stat-hint">ordonnances</span>

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

          {backupStatus.latest_backup && (

            <p className="clinical-lead">

              Dernier fichier : {backupStatus.latest_backup} ({backupStatus.age_hours}h)

            </p>

          )}

        </section>

      )}



      <section id="admin-audit" className="clinical-card" style={{ marginTop: '1rem' }}>

        <h2>Journal d&apos;audit</h2>

        <ul className="clinical-list clinical-audit-list">

          {auditLogs.length === 0 && <li>Aucune entrée — effectuez une action clinique pour alimenter le journal.</li>}

          {auditLogs.map((log) => (

            <li key={log.id}>

              <strong>{log.action}</strong> · {log.resource_type}

              {log.resource_id != null && ` #${log.resource_id}`}

              <br />

              <span className="clinical-badge">{log.actor_role}</span>

              {' · '}

              {log.timestamp ? new Date(log.timestamp).toLocaleString('fr-FR') : ''}

              {log.patient_id && ` · patient #${log.patient_id}`}

            </li>

          ))}

        </ul>

      </section>



      <section id="admin-users" className="clinical-card" style={{ marginTop: '1rem' }}>

        <h2>Utilisateurs ({users.length})</h2>

        <p className="clinical-lead">

          Comptes plateforme — <Link to="/users">gestion complète →</Link>

        </p>

        <div className="clinical-users-mini">

          <table className="clinical-stock-table">

            <thead>

              <tr>

                <th>ID</th>

                <th>Email</th>

                <th>Rôle</th>

              </tr>

            </thead>

            <tbody>

              {users.slice(0, 12).map((u) => (

                <tr key={u.id}>

                  <td>{u.id}</td>

                  <td>{u.email}</td>

                  <td><span className="clinical-badge">{u.role}</span></td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      </section>



      <div className="clinical-grid" style={{ marginTop: '1rem' }}>

        <section className="clinical-card">

          <h2>Créer une clinique</h2>

          <form onSubmit={createClinic}>

            <div className="clinical-field">

              <label>Nom</label>

              <input value={clinicForm.name} onChange={(e) => setClinicForm({ ...clinicForm, name: e.target.value })} required />

            </div>

            <div className="clinical-field">

              <label>Ville</label>

              <input value={clinicForm.city} onChange={(e) => setClinicForm({ ...clinicForm, city: e.target.value })} />

            </div>

            <div className="clinical-field">

              <label>Téléphone</label>

              <input value={clinicForm.phone} onChange={(e) => setClinicForm({ ...clinicForm, phone: e.target.value })} />

            </div>

            <div className="clinical-field">

              <label>Adresse</label>

              <input value={clinicForm.address} onChange={(e) => setClinicForm({ ...clinicForm, address: e.target.value })} />

            </div>

            <button type="submit" className="clinical-btn">Créer la clinique</button>

          </form>

        </section>



        <section className="clinical-card" id="create-user">

          <h2>Utilisateurs</h2>

          <p className="clinical-lead">
            Création interne des comptes personnel : réception, laboratoire, pharmacie, caisse, nutrition, sage-femme
            et administration clinique. L&apos;inscription publique reste réservée aux patients et médecins.
          </p>

          <h3>Créer un utilisateur</h3>

          <form onSubmit={createStaff}>

            <div className="clinical-field">

              <label>ID clinique</label>

              <input value={staffForm.clinic_id} onChange={(e) => setStaffForm({ ...staffForm, clinic_id: e.target.value })} required />

            </div>

            <div className="clinical-field">

              <label>Email</label>

              <input type="email" value={staffForm.email} onChange={(e) => setStaffForm({ ...staffForm, email: e.target.value })} required />

            </div>

            <div className="clinical-field">

              <label>Mot de passe</label>

              <input type="password" value={staffForm.password} onChange={(e) => setStaffForm({ ...staffForm, password: e.target.value })} required />

            </div>

            <div className="clinical-field">

              <label>Rôle</label>

              <select value={staffForm.role} onChange={(e) => setStaffForm({ ...staffForm, role: e.target.value })}>

                <option value="receptionist">Réceptionniste</option>

                <option value="cashier">Caissier</option>

                <option value="doctor">Médecin</option>

                <option value="lab_technician">Laborantin</option>

                <option value="pharmacist">Pharmacien</option>

                <option value="nutritionist">Nutritionniste</option>

                <option value="midwife">Sage-femme</option>

                <option value="clinic_admin">Administrateur clinique</option>

                <option value="admin">Admin (alias clinique)</option>

              </select>

            </div>

            <button type="submit" className="clinical-btn">Créer le compte</button>

          </form>

          {clinicStaff.length > 0 && (

            <div className="clinical-users-mini" style={{ marginTop: '1rem' }}>

              <h3>Personnel de la clinique ({clinicStaff.length})</h3>

              <table className="clinical-stock-table">

                <thead>

                  <tr>

                    <th>Email</th>

                    <th>Rôle</th>

                    <th>Actif</th>

                  </tr>

                </thead>

                <tbody>

                  {clinicStaff.map((u) => (

                    <tr key={u.id}>

                      <td>{u.email}</td>

                      <td><span className="clinical-badge">{u.role}</span></td>

                      <td>{u.is_active ? 'Oui' : 'Non'}</td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </section>

      </div>

    </div>

  );

}


