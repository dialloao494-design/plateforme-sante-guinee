import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { appointmentsAPI } from '../services/api.js';
import { formatApiError } from '../utils/apiError.js';
import { useAuth } from './AuthContext.jsx';

const AppointmentContext = createContext(null);

const TELEHEALTH_APPOINTMENT_ROLES = new Set(['patient', 'doctor']);

function shouldLoadAppointments(user) {
  if (!user?.role) {
    return false;
  }
  const role = String(user.role).toLowerCase();
  if (!TELEHEALTH_APPOINTMENT_ROLES.has(role)) {
    return false;
  }
  if (role === 'doctor' && user.clinic_id) {
    return false;
  }
  return true;
}

const normalizeAppointment = (appointment) => ({
  ...appointment,
  id: appointment.id,
});

const extractErrorMessage = (err, fallbackMessage) => formatApiError(err, fallbackMessage);

export const AppointmentProvider = ({ children }) => {
  const { authLoading, user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAppointments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await appointmentsAPI.getMyAppointments();
      const normalized = data.map(normalizeAppointment);
      setAppointments(normalized);
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur lors du chargement des rendez-vous'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!shouldLoadAppointments(user)) {
      setAppointments([]);
      setLoading(false);
      setError(null);
      return;
    }
    void fetchAppointments();
  }, [authLoading, user, fetchAppointments]);

  const addAppointment = async ({ doctor_id, date, duration_minutes, consultation_type }) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await appointmentsAPI.create({ doctor_id, date, duration_minutes, consultation_type });
      const normalized = normalizeAppointment(data);
      setAppointments((prev) => [normalized, ...prev]);
      return normalized;
    } catch (err) {
      setError(extractErrorMessage(err, 'Impossible de créer le rendez-vous.'));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const deleteAppointment = async (id) => {
    setLoading(true);
    setError(null);
    try {
      await appointmentsAPI.cancel(id);
      setAppointments((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      setError(extractErrorMessage(err, 'Impossible d’annuler le rendez-vous.'));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updateAppointment = async (id, status) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await appointmentsAPI.updateStatus(id, status);
      const normalized = normalizeAppointment(data);
      setAppointments((prev) => prev.map((a) => (a.id === id ? normalized : a)));
      return normalized;
    } catch (err) {
      setError(extractErrorMessage(err, 'Mise à jour du rendez-vous impossible.'));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppointmentContext.Provider
      value={{
        appointments,
        loading,
        error,
        addAppointment,
        updateAppointment,
        deleteAppointment,
        fetchAppointments,
      }}
    >
      {children}
    </AppointmentContext.Provider>
  );
};

/* eslint-disable react-refresh/only-export-components */
export const useAppointmentContext = () => {
  const context = useContext(AppointmentContext);
  if (!context) {
    throw new Error('useAppointmentContext must be used within AppointmentProvider');
  }
  return context;
};
/* eslint-enable react-refresh/only-export-components */