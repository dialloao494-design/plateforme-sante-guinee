import { useEffect, useMemo, useState } from 'react';
import { usePatientContext } from '../contexts/PatientContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { patientsAPI } from '../services/api.js';
import PatientList from '../components/PatientList.jsx';
import './Patients.css';

const ADMIN_ROLES = new Set(['admin', 'clinic_admin', 'platform_admin', 'platform_owner']);

const Patients = () => {
  const { user } = useAuth();
  const { patients, loading, error, addPatient, updatePatient, deletePatient } = usePatientContext();
  const [formData, setFormData] = useState({ firstName: '', lastName: '', age: '', gender: '', userId: '' });
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState('');
  const [accountQuery, setAccountQuery] = useState('');
  const [accountResults, setAccountResults] = useState([]);
  const [accountSearching, setAccountSearching] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);

  const isAdmin = ADMIN_ROLES.has(String(user?.role || '').toLowerCase());
  const isDoctor = user?.role === 'doctor';
  const showForm = isAdmin || (isDoctor && editingId !== null);

  useEffect(() => {
    if (!isAdmin || editingId !== null) {
      return undefined;
    }
    const term = accountQuery.trim();
    if (term.length < 2) {
      setAccountResults([]);
      return undefined;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      setAccountSearching(true);
      try {
        const { data } = await patientsAPI.searchAccountCandidates(term);
        if (!cancelled) {
          setAccountResults(Array.isArray(data) ? data : []);
        }
      } catch {
        if (!cancelled) {
          setAccountResults([]);
        }
      } finally {
        if (!cancelled) {
          setAccountSearching(false);
        }
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [accountQuery, isAdmin, editingId]);

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
        if (!selectedAccount?.id) {
          return;
        }
        await addPatient({
          firstName,
          lastName,
          age,
          gender,
          userId: String(selectedAccount.id),
        });
      }
      setFormData({ firstName: '', lastName: '', age: '', gender: '', userId: '' });
      setSelectedAccount(null);
      setAccountQuery('');
      setAccountResults([]);
      setEditingId(null);
    } catch {
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
      userId: patient.user_id != null ? String(patient.user_id) : '',
    });
    setSelectedAccount(null);
    setAccountQuery('');
    setAccountResults([]);
  };

  const handleCancel = () => {
    setEditingId(null);
    setFormData({ firstName: '', lastName: '', age: '', gender: '', userId: '' });
    setSelectedAccount(null);
    setAccountQuery('');
    setAccountResults([]);
  };

  const filteredPatients = useMemo(() => {
    return patients.filter((patient) => patient.name.toLowerCase().includes(search.toLowerCase()));
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

      {showForm && (
        <form className="patients-form" onSubmit={handleSubmit}>
          {isAdmin && editingId === null && (
            <div className="patients-account-picker">
              <label htmlFor="patient-account-search">Compte patient</label>
              <input
                id="patient-account-search"
                type="search"
                placeholder="Rechercher par e-mail ou n° de dossier..."
                value={accountQuery}
                onChange={(e) => {
                  setAccountQuery(e.target.value);
                  setSelectedAccount(null);
                  setFormData((prev) => ({ ...prev, userId: '' }));
                }}
                autoComplete="off"
              />
              {accountSearching && <p className="patients-account-hint">Recherche…</p>}
              {selectedAccount ? (
                <div className="patients-account-confirm" role="status">
                  <strong>Compte sélectionné</strong>
                  <span>{selectedAccount.email}</span>
                  <span>Dossier utilisateur #{selectedAccount.id}</span>
                  {selectedAccount.already_linked ? (
                    <span className="patients-account-warn">Déjà lié à un dossier — création refusée</span>
                  ) : null}
                  <button
                    type="button"
                    className="btn btn-tertiary"
                    onClick={() => {
                      setSelectedAccount(null);
                      setFormData((prev) => ({ ...prev, userId: '' }));
                    }}
                  >
                    Changer
                  </button>
                </div>
              ) : (
                <ul className="patients-account-results">
                  {accountResults.map((candidate) => (
                    <li key={candidate.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedAccount(candidate);
                          setFormData((prev) => ({ ...prev, userId: String(candidate.id) }));
                          setAccountQuery(candidate.email || '');
                        }}
                      >
                        <span>{candidate.email}</span>
                        <span>#{candidate.id}</span>
                        {candidate.already_linked ? <span>déjà lié</span> : null}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
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
          <button type="submit" disabled={editingId === null && isAdmin && !selectedAccount?.id}>
            {editingId !== null ? 'Mettre à jour' : 'Ajouter'}
          </button>
          {(editingId !== null || (isAdmin && formData.firstName)) && (
            <button type="button" className="btn btn-tertiary" onClick={handleCancel}>
              Annuler
            </button>
          )}
        </form>
      )}

      <PatientList
        patients={filteredPatients}
        onDelete={isAdmin ? deletePatient : undefined}
        onEdit={isAdmin || isDoctor ? handleEdit : undefined}
      />
    </div>
  );
};

export default Patients;
