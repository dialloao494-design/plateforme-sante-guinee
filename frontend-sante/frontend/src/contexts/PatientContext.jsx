import { createContext, useContext, useEffect, useState } from 'react';
import { patientsAPI } from '../services/api.js';
import { formatApiError } from '../utils/apiError.js';
import { useAuth } from './AuthContext.jsx';

const PatientContext = createContext(null);

const CLINIC_STAFF_ROLES = new Set([
  'receptionist',
  'cashier',
  'lab_technician',
  'pharmacist',
  'nutritionist',
  'midwife',
  'pev_agent',
  'nurse',
  'clinic_admin',
  'admin',
  'platform_admin',
  'platform_owner',
]);

function shouldLoadTelehealthPatients(user) {
  if (!user?.role) {
    return false;
  }
  const role = String(user.role).toLowerCase();
  if (CLINIC_STAFF_ROLES.has(role)) {
    return false;
  }
  if (role === 'doctor' && user.clinic_id) {
    return false;
  }
  return role === 'doctor' || role === 'admin';
}

const normalizePatient = (patient) => ({
  ...patient,
  id: patient.id,
  user_id: patient.user_id,
  name: `${patient.first_name ?? ''} ${patient.last_name ?? ''}`.trim() || `Patient #${patient.id}`,
  condition: patient.gender,
});

export const PatientProvider = ({ children }) => {
  const { user, authLoading } = useAuth();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPatients = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await patientsAPI.getAll();
      const normalized = data.map(normalizePatient);
      setPatients(normalized);
    } catch (err) {
      setError(formatApiError(err, 'Erreur de connexion. Veuillez réessayer.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (shouldLoadTelehealthPatients(user)) {
      fetchPatients();
    }
  }, [user, authLoading]);

  const addPatient = async ({ firstName, lastName, age, gender, userId }) => {
    const role = String(user?.role || '').toLowerCase();
    if (!['admin', 'clinic_admin', 'platform_admin', 'platform_owner'].includes(role)) {
      const errMsg = 'Seuls les administrateurs peuvent créer un dossier patient.';
      setError(errMsg);
      throw new Error(errMsg);
    }
    const uid = Number(userId);
    if (!Number.isInteger(uid) || uid < 1) {
      const errMsg = 'Sélectionnez un compte patient confirmé avant de créer le dossier.';
      setError(errMsg);
      throw new Error(errMsg);
    }

    setLoading(true);
    setError(null);
    try {
      const payload = {
        user_id: uid,
        first_name: firstName,
        last_name: lastName,
        age,
        gender,
      };
      const { data } = await patientsAPI.create(payload);
      const normalized = normalizePatient(data);
      setPatients((prev) => [normalized, ...prev]);
      return normalized;
    } catch (err) {
      setError(formatApiError(err, 'Erreur création'));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updatePatient = async (id, { firstName, lastName, age, gender }) => {
    const existing = patients.find((p) => p.id === id);
    const resolvedUserId = existing?.user_id;
    if (resolvedUserId == null) {
      const errMsg = 'Impossible de mettre à jour : identifiant utilisateur lié manquant.';
      setError(errMsg);
      throw new Error(errMsg);
    }

    setLoading(true);
    setError(null);
    try {
      const payload = {
        user_id: resolvedUserId,
        first_name: firstName,
        last_name: lastName,
        age,
        gender,
      };
      const { data } = await patientsAPI.update(id, payload);
      const normalized = normalizePatient(data);
      setPatients((prev) => prev.map((p) => (p.id === id ? normalized : p)));
      return normalized;
    } catch (err) {
      setError(formatApiError(err, 'Erreur mise à jour'));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const deletePatient = async (id) => {
    const role = String(user?.role || '').toLowerCase();
    if (!['admin', 'clinic_admin', 'platform_admin', 'platform_owner'].includes(role)) {
      const errMsg = 'Seuls les administrateurs peuvent supprimer un dossier patient.';
      setError(errMsg);
      throw new Error(errMsg);
    }
    setLoading(true);
    setError(null);
    try {
      await patientsAPI.delete(id);
      setPatients((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(formatApiError(err, 'Erreur suppression'));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return (
    <PatientContext.Provider
      value={{ patients, loading, error, fetchPatients, addPatient, updatePatient, deletePatient }}
    >
      {children}
    </PatientContext.Provider>
  );
};

/* eslint-disable react-refresh/only-export-components */
export const usePatientContext = () => {
  const context = useContext(PatientContext);
  if (!context) {
    throw new Error('usePatientContext must be used within PatientProvider');
  }
  return context;
};
/* eslint-enable react-refresh/only-export-components */
