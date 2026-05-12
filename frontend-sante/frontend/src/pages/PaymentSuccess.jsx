import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { paymentsAPI } from '../services/api.js';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getAppointmentStatusLabel, getPaymentLabel } from '../utils/appointmentPresentation.js';

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const { fetchAppointments } = useAppointmentContext();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('Validation du paiement en cours...');

  useEffect(() => {
    const sessionId = searchParams.get('session_id');

    const confirm = async () => {
      if (!sessionId) {
        setError('Session de paiement introuvable.');
        setLoading(false);
        return;
      }

      try {
        const response = await paymentsAPI.confirmCheckout(sessionId);
        const confirmed = response?.data;
        await fetchAppointments();
        const paidLabel = getPaymentLabel(confirmed);
        const resolvedStatusLabel = getAppointmentStatusLabel(confirmed);
        setMessage(`Paiement confirmé. Statut du rendez-vous: ${resolvedStatusLabel} (${paidLabel}).`);
      } catch (err) {
        setError(err?.response?.data?.detail || err?.message || 'Paiement échoué.');
      } finally {
        setLoading(false);
      }
    };

    confirm();
  }, [searchParams]);

  return (
    <div style={{ padding: 24 }}>
      <h1>Paiement réussi</h1>
      {loading && <p>{message}</p>}
      {!loading && !error && <p>{message}</p>}
      {!loading && error && <p style={{ color: 'crimson' }}>{error}</p>}
      <p>
        <Link to={user?.role === 'doctor' ? '/doctor/dashboard' : '/appointments'}>
          Retour aux rendez-vous
        </Link>
      </p>
    </div>
  );
};

export default PaymentSuccess;
