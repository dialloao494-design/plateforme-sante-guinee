import { useMemo, useState } from 'react';
import { usePatientContext } from '../contexts/PatientContext.jsx';
import PatientList from '../components/PatientList.jsx';
import './Patients.css';

const Patients = () => {
  const { patients, loading, error, addPatient, updatePatient, deletePatient } = usePatientContext();
  const [formData, setFormData] = useState({ firstName: '', lastName: '', age: '', gender: '' });
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const firstName = formData.firstName.trim();
    const lastName = formData.lastName.trim();
    const age = Number(formData.age);
    const gender = formData.gender.trim();
    if (!firstName || !lastName || !age || !gender) return;

    try {
      if (editingId !== null) {
        await updatePatient(editingId, { firstName, lastName, age, gender });
      } else {
        await addPatient({ firstName, lastName, age, gender });
      }
      setFormData({ firstName: '', lastName: '', age: '', gender: '' });
      setEditingId(null);
    } catch (error) {
      // Error is handled by the context and displayed in UI
    }
  };

  const handleEdit = (patient) => {
    setEditingId(patient.id);
    setFormData({
      firstName: patient.first_name || patient.name.split(' ')[0] || '',
      lastName: patient.last_name || patient.name.split(' ').slice(1).join(' ') || '',
      age: String(patient.age || ''),
      gender: patient.gender || patient.condition || '',
    });
  };

  const handleCancel = () => {
    setEditingId(null);
    setFormData({ firstName: '', lastName: '', age: '', gender: '' });
  };

  const filteredPatients = useMemo(() => {
    return patients.filter((patient) =>
      patient.name.toLowerCase().includes(search.toLowerCase())
    );
  }, [patients, search]);

  return (
    <div className="patients-page">
      <h1>Gestion des patients</h1>

      {loading && <p>Chargement...</p>}
      {error && <p className="error">Erreur : {error}</p>}

      <div className="patients-top-controls">
        <div>
          <input
            type="text"
            placeholder="Rechercher un patient..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="patients-stats">
          <span>Total: {patients.length}</span>
        </div>
      </div>

      <form className="patients-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Prénom"
          value={formData.firstName}
          onChange={(e) => setFormData((prev) => ({ ...prev, firstName: e.target.value }))}
        />
        <input
          type="text"
          placeholder="Nom"
          value={formData.lastName}
          onChange={(e) => setFormData((prev) => ({ ...prev, lastName: e.target.value }))}
        />
        <input
          type="number"
          placeholder="Âge"
          value={formData.age}
          onChange={(e) => setFormData((prev) => ({ ...prev, age: e.target.value }))}
        />
        <input
          type="text"
          placeholder="Genre"
          value={formData.gender}
          onChange={(e) => setFormData((prev) => ({ ...prev, gender: e.target.value }))}
        />
        <button type="submit">{editingId !== null ? 'Mettre à jour' : 'Ajouter'}</button>
        {editingId !== null && (
          <button type="button" className="btn btn-tertiary" onClick={handleCancel}>
            Annuler
          </button>
        )}
      </form>

      <PatientList
        patients={filteredPatients}
        onDelete={deletePatient}
        onEdit={handleEdit}
      />
    </div>
  );
};

export default Patients;
