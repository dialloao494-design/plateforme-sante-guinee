/**
 * Platform owner administration — clinics + all users + cross-clinic staff provisioning.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import httpClient from '../../services/httpClient';
import { formatApiError } from '../../utils/apiError.js';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import ClinicalStatGrid from '../clinical/ClinicalStatGrid.jsx';
import '../clinical/clinical.css';

const STAFF_ROLE_OPTIONS = [
  { value: 'receptionist', label: 'Réceptionniste' },
  { value: 'cashier', label: 'Caissier' },
  { value: 'doctor', label: 'Médecin' },
  { value: 'lab_technician', label: 'Laborantin' },
  { value: 'pharmacist', label: 'Pharmacien' },
  { value: 'nutritionist', label: 'Nutritionniste' },
  { value: 'midwife', label: 'Sage-femme' },
  { value: 'clinic_admin', label: 'Administrateur clinique' },
  { value: 'admin', label: 'Admin (alias clinique)' },
];

export default function PlatformOwnerAdminDashboard() {
  const { user } = useAuth();
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [platformUsers, setPlatformUsers] = useState([]);
  const [clinicStaff, setClinicStaff] = useState([]);
  const [clinicForm, setClinicForm] = useState({ name: '', city: 'Conakry', phone: '', address: '' });
  const [staffForm, setStaffForm] = useState({
    email: '',
    password: '',
    role: 'clinic_admin',
    clinic_id: '',
  });

  const loadPlatformUsers = async () => {
    try {
      const { data } = await httpClient.get('/platform/users');
      setPlatformUsers(Array.isArray(data) ? data : []);
    } catch {
      setPlatformUsers([]);
    }
  };

  const loadClinicStaff = async (clinicId) => {
    if (!clinicId) return;
    try {
      const { data } = await clinicalApi.listStaff(Number(clinicId));
      setClinicStaff(data || []);
    } catch {
      setClinicStaff([]);
    }
  };

  useEffect(() => {
    loadPlatformUsers();
  }, []);

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
      setClinicForm({ name: '', city: 'Conakry', phone: '', address: '' });
    } catch (err) {
      setError(formatApiError(err, 'Création clinique impossible'));
    }
  };

  const createStaff = async (e) => {
    e.preventDefault();
    setError('');
    if (!staffForm.clinic_id) {
      setError('Indiquez l’ID de la clinique.');
      return;
    }
    const chosenPassword = staffForm.password;
    try {
      const { data } = await clinicalApi.createStaff({
        ...staffForm,
        clinic_id: Number(staffForm.clinic_id),
      });
      setMessage(`Compte ${data.role} créé : ${data.email} — mot de passe : ${chosenPassword}`);
      setStaffForm((prev) => ({ ...prev, email: '', password: '' }));
      loadClinicStaff(staffForm.clinic_id);
      loadPlatformUsers();
    } catch (err) {
      setError(formatApiError(err, 'Création compte impossible'));
    }
  };

  const stats = useMemo(
    () => [
      { label: 'Utilisateurs plateforme', value: platformUsers.length, variant: 'accent' },
      { label: 'Personnel (clinique sélectionnée)', value: clinicStaff.length, variant: 'success' },
    ],
    [platformUsers.length, clinicStaff.length]
  );

  return (
    <div className="clinical-page clinical-page--platform-owner">
      <header className="clinical-page-header">
        <p className="clinical-eyebrow">Propriétaire plateforme</p>
        <h1>Administration plateforme</h1>
        <p className="clinical-lead">
          Bienvenue, {user?.full_name || user?.email}. Créez des cliniques, des administrateurs clinique et
          supervisez tous les comptes.
        </p>
      </header>

      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <nav className="clinical-section-nav" aria-label="Sections plateforme">
        <a href="#platform-clinics">Cliniques</a>
        <a href="#platform-users">Utilisateurs</a>
        <a href="#platform-staff">Créer un admin / staff</a>
        <Link to="/users">Gestion utilisateurs →</Link>
        <Link to="/platform">Console plateforme →</Link>
      </nav>

      <section id="platform-clinics" className="clinical-card">
        <h2>Créer une clinique</h2>
        <p className="clinical-lead">Réservé au propriétaire plateforme.</p>
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

      <section id="platform-users" className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Utilisateurs plateforme ({platformUsers.length})</h2>
        <table className="clinical-stock-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Rôle</th>
            </tr>
          </thead>
          <tbody>
            {platformUsers.slice(0, 20).map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.email}</td>
                <td><span className="clinical-badge">{u.role}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section id="platform-staff" className="clinical-card" style={{ marginTop: '1rem' }}>
        <h2>Créer administrateur clinique ou personnel</h2>
        <form onSubmit={createStaff}>
          <div className="clinical-field">
            <label>ID clinique</label>
            <input
              value={staffForm.clinic_id}
              onChange={(e) => setStaffForm({ ...staffForm, clinic_id: e.target.value })}
              placeholder="ex. 1"
              required
            />
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
