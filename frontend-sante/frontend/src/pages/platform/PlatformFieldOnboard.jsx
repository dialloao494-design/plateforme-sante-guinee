/**
 * URGENT field onboarding — works with production /clinical APIs only.
 * Scoped to one clinic; shows temp passwords for accounts created this session.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import { filterProductionClinics } from '../../utils/clinicProductionFilter.js';
import './PlatformOwner.css';
import '../clinical/clinical.css';

const ONBOARD_ROLES = [
  { value: 'clinic_admin', label: 'Administrateur clinique' },
  { value: 'receptionist', label: 'Réceptionniste' },
  { value: 'cashier', label: 'Caissier' },
  { value: 'doctor', label: 'Médecin' },
  { value: 'lab_technician', label: 'Laborantin' },
  { value: 'pharmacist', label: 'Pharmacien' },
];

const ROLE_LABELS = Object.fromEntries(ONBOARD_ROLES.map((o) => [o.value, o.label]));

function credKey(clinicId) {
  return `field_onboard_creds_${clinicId}`;
}

function loadCreds(clinicId) {
  try {
    const raw = sessionStorage.getItem(credKey(clinicId));
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveCred(clinicId, userId, entry) {
  const all = loadCreds(clinicId);
  all[userId] = entry;
  sessionStorage.setItem(credKey(clinicId), JSON.stringify(all));
}

function genPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
  let s = 'Aasma';
  for (let i = 0; i < 6; i += 1) s += chars[Math.floor(Math.random() * chars.length)];
  return s + '!';
}

export default function PlatformFieldOnboard() {
  const { clinicId: routeClinicId } = useParams();
  const [clinics, setClinics] = useState([]);
  const [selectedId, setSelectedId] = useState(routeClinicId ? Number(routeClinicId) : '');
  const [staff, setStaff] = useState([]);
  const [creds, setCreds] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({ email: '', password: genPassword(), role: 'receptionist' });

  const clinic = useMemo(
    () => clinics.find((c) => c.id === Number(selectedId)),
    [clinics, selectedId]
  );

  const loadClinics = useCallback(async () => {
    const { data } = await clinicalApi.listClinics({ forceRefresh: true });
    const prod = filterProductionClinics(data || []);
    setClinics(prod);
    if (routeClinicId) {
      setSelectedId(Number(routeClinicId));
    } else {
      const aasma = prod.find((c) => String(c.name || '').toLowerCase().includes('aasma'));
      if (aasma) setSelectedId(aasma.id);
      else if (prod.length === 1) setSelectedId(prod[0].id);
    }
  }, [routeClinicId]);

  const loadStaff = useCallback(async (id) => {
    if (!id) return;
    const { data } = await clinicalApi.listStaff(Number(id));
    setStaff(Array.isArray(data) ? data : []);
    setCreds(loadCreds(id));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError('');
    loadClinics()
      .catch((err) => setError(formatApiError(err, 'Impossible de charger les cliniques')))
      .finally(() => setLoading(false));
  }, [loadClinics]);

  useEffect(() => {
    if (selectedId) loadStaff(selectedId).catch(() => setStaff([]));
  }, [selectedId, loadStaff]);

  const createStaff = async (e) => {
    e.preventDefault();
    if (!selectedId) return;
    setError('');
    const password = form.password || genPassword();
    try {
      const { data } = await clinicalApi.createStaff({
        email: form.email.trim(),
        password,
        role: form.role,
        clinic_id: Number(selectedId),
      });
      const entry = { email: data.email, role: data.role, password, createdAt: Date.now() };
      saveCred(selectedId, data.id, entry);
      setCreds((prev) => ({ ...prev, [data.id]: entry }));
      setMessage(`Compte créé : ${data.email} — mot de passe : ${password}`);
      setForm({ email: '', password: genPassword(), role: form.role });
      loadStaff(selectedId);
    } catch (err) {
      setError(formatApiError(err, 'Création impossible'));
    }
  };

  if (loading) {
    return <div className="clinical-page"><p className="clinical-lead">Chargement…</p></div>;
  }

  return (
    <div className="clinical-page platform-field-onboard">
      <header className="clinical-page-header">
        <p className="clinical-eyebrow">Mode terrain — onboarding personnel</p>
        <h1>Créer le personnel clinique</h1>
        <p className="clinical-lead">
          Sélectionnez la clinique, créez les comptes. Chaque compte est rattaché uniquement à la clinique choisie.
        </p>
      </header>

      {error && <p className="clinical-error">{error}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <section className="clinical-card">
        <div className="clinical-field">
          <label>Clinique</label>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(Number(e.target.value))}
          >
            <option value="">— Choisir —</option>
            {clinics.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} (ID {c.id}) — {c.city || 'Conakry'}
              </option>
            ))}
          </select>
        </div>
        {clinic && (
          <p className="clinical-lead">
            <strong>{clinic.name}</strong> · ID {clinic.id} · {clinic.phone || '—'}
          </p>
        )}
      </section>

      {selectedId && (
        <>
          <section className="clinical-card">
            <h2>Nouveau compte</h2>
            <form onSubmit={createStaff}>
              <div className="platform-form-grid">
                <div className="clinical-field">
                  <label>Email</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    required
                    placeholder="nom@email.com"
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
                <div className="clinical-field">
                  <label>Rôle</label>
                  <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                    {ONBOARD_ROLES.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <button type="submit" className="clinical-btn">Créer le compte</button>
            </form>
          </section>

          <section className="clinical-card">
            <h2>Personnel — {clinic?.name} ({staff.length})</h2>
            <table className="clinical-stock-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Rôle</th>
                  <th>Mot de passe temp.</th>
                  <th>Connexion</th>
                </tr>
              </thead>
              <tbody>
                {staff.map((member) => (
                  <tr key={member.id}>
                    <td>{member.email}</td>
                    <td>{ROLE_LABELS[member.role] || member.role}</td>
                    <td>{creds[member.id]?.password || '— (créé avant cette session)'}</td>
                    <td>{member.is_active ? 'Actif' : 'Inactif'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}

      <p className="clinical-lead">
        <Link to="/platform/clinics">Répertoire cliniques</Link>
      </p>
    </div>
  );
}
