import { createContext, useContext, useEffect, useState } from 'react';
import { patientsAPI } from '../services/api.js';
import { useAuth } from './AuthContext.jsx';

const PatientContext = createContext(null);

const normalizePatient = (patient) => ({
  ...patient,
  id: patient.id,
  name: `${patient.first_name} ${patient.last_name}`,
  condition: patient.gender,
});

export const PatientProvider = ({ children }) => {
  const { user } = useAuth();
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
      setError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Erreur réseau');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  const addPatient = async ({ firstName, lastName, age, gender }) => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        user_id: user?.id || 1,
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
      setError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Erreur création');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updatePatient = async (id, { firstName, lastName, age, gender }) => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        user_id: user?.id || 1,
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
      setError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Erreur mise à jour');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const deletePatient = async (id) => {
    setLoading(true);
    setError(null);
    try {
      await patientsAPI.delete(id);
      setPatients((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err?.response?.data?.detail || err?.response?.data?.message || err.message || 'Erreur suppression');
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

export const usePatientContext = () => {
  const context = useContext(PatientContext);
  if (!context) {
    throw new Error('usePatientContext must be used within PatientProvider');
  }
  return context;
};
