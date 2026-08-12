import { useEffect, useMemo, useState } from 'react';
import { usePatientContext } from '../contexts/PatientContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import PatientList from '../components/PatientList.jsx';
import PatientAccountSelector from '../components/PatientAccountSelector.jsx';
import './Patients.css';

const ADMIN_ROLES = new Set(['admin', 'clinic_admin', 'platform_admin', 'platform_owner']);

const Patients = () => {
  const { user } = useAuth();
  const { patients, loading, error, addPatient, updatePatient, deletePatient } = usePatientContext();
  const [formData, setFormData] = useState({ firstName: '', lastName: '', age: '', gender: '', selectedAccount: null });
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState('');
  const isAdmin = ADMIN_ROLES.has(String(user?.role || '').toLowerCase());
  const isDoctor = user?.role === 'doctor';
  const showForm = isAdmin || (isDoctor && editingId !== null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const firstName = formData.firstName.trim();
    const lastName = formData.lastName.trim();
    const age = Number(formData.age);
    const gender = formData.gender.trim();
    if (!firstName || !lastName || !age || !gender) return;
    try {
      if (editingId !== null) await updatePatient(editingId, { firstName, lastName, age, gender });
      else {
        if (!formData.selectedAccount?.id) return;
        await addPatient({ firstName, lastName, age, gender, userId: formData.selectedAccount.id });
      }
      setFormData({ firstName: '', lastName: '', age: '', gender: '', selectedAccount: null });
      setEditingId(null);
    } catch {}
  };

  const handleEdit = (patient) => {
    setEditingId(patient.id);
    setFormData({
      firstName: patient.first_name || patient.name.split(' ')[0] || '',
      lastName: patient.last_name || patient.name.split(' ').slice(1).join(' ') || '',
      age: String(patient.age || ''),
      gender: patient.gender || patient.condition || '',
      selectedAccount: patient.user_id ? { id: patient.user_id, email: patient.user_email || `compte #${patient.user_id}` } : null,
    });
  };

  const filteredPatients = useMemo(() => patients.filter((p) => p.name.toLowerCase().includes(search.toLowerCase())), [patients, search]);

  return (
    <div className="patients-page">
      <h1>Gestion des patients</h1>
      {loading && <p>Chargement...</p>}
      {error && <p className="error">Erreur : {error}</p>}
      <input type="text" placeholder="Rechercher un patient..." value={search} onChange={(e) => setSearch(e.target.value)} />
      {showForm && (
        <form className="patients-form" onSubmit={handleSubmit}>
          {isAdmin && editingId === null && (
            <PatientAccountSelector value={formData.selectedAccount} onChange={(a) => setFormData((p) => ({ ...p, selectedAccount: a }))} />
          )}
          <input type="text" placeholder="Prénom" value={formData.firstName} onChange={(e) => setFormData((p) => ({ ...p, firstName: e.target.value }))} />
          <input type="text" placeholder="Nom" value={formData.lastName} onChange={(e) => setFormData((p) => ({ ...p, lastName: e.target.value }))} />
          <input type="number" placeholder="Âge" value={formData.age} onChange={(e) => setFormData((p) => ({ ...p, age: e.target.value }))} />
          <input type="text" placeholder="Genre" value={formData.gender} onChange={(e) => setFormData((p) => ({ ...p, gender: e.target.value }))} />
          <button type="submit" disabled={editingId === null && isAdmin && !formData.selectedAccount?.id}>{editingId !== null ? 'Mettre à jour' : 'Ajouter'}</button>
        </form>
      )}
      <PatientList patients={filteredPatients} onEdit={isAdmin || isDoctor ? handleEdit : undefined} onDelete={isAdmin ? deletePatient : undefined} />
    </div>
  );
};

export default Patients;
