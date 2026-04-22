import { createContext, useContext, useEffect, useState } from 'react';
import { appointmentsAPI } from '../services/api.js';

const AppointmentContext = createContext(null);

const normalizeAppointment = (appointment) => ({
  ...appointment,
  id: appointment.id,
});

const extractErrorMessage = (err, fallbackMessage) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => (typeof item === 'string' ? item : item?.msg || JSON.stringify(item)))
      .join(' | ');
  }

  const message = err?.response?.data?.message;
  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  if (typeof err?.message === 'string' && err.message.trim()) {
    return err.message;
  }

  return fallbackMessage;
};

export const AppointmentProvider = ({ children }) => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAppointments = async () => {
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
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  const addAppointment = async ({ doctor_id, date, duration_minutes }) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await appointmentsAPI.create({ doctor_id, date, duration_minutes });
      const normalized = normalizeAppointment(data);
      setAppointments((prev) => [normalized, ...prev]);
      return normalized;
    } catch (err) {
      setError(extractErrorMessage(err, 'Erreur création'));
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
      setError(extractErrorMessage(err, 'Erreur suppression'));
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
      setError(extractErrorMessage(err, 'Erreur mise à jour'));
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

export const useAppointmentContext = () => {
  const context = useContext(AppointmentContext);
  if (!context) {
    throw new Error('useAppointmentContext must be used within AppointmentProvider');
  }
  return context;
};