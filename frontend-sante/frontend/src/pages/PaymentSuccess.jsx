import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { paymentsAPI } from '../services/api.js';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const { fetchAppointments } = useAppointmentContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('Validating payment with Stripe...');

  useEffect(() => {
    const sessionId = searchParams.get('session_id');

    const confirm = async () => {
      if (!sessionId) {
        setError('Missing session_id in success URL.');
        setLoading(false);
        return;
      }

      try {
        const response = await paymentsAPI.confirmCheckout(sessionId);
        const confirmed = response?.data;
        await fetchAppointments();
        const paidLabel = confirmed?.is_paid ? 'payé' : 'non payé';
        setMessage(`Paiement confirmé. Rendez-vous ${confirmed?.status || 'confirmé'} (${paidLabel}).`);
      } catch (err) {
        setError(err?.response?.data?.detail || err?.message || 'Failed to confirm payment.');
      } finally {
        setLoading(false);
      }
    };

    confirm();
  }, [searchParams]);

  return (
    <div style={{ padding: 24 }}>
      <h1>Stripe Payment Success</h1>
      {loading && <p>{message}</p>}
      {!loading && !error && <p>{message}</p>}
      {!loading && error && <p style={{ color: 'crimson' }}>{error}</p>}
      <p>
        <Link to="/appointments">Back to Appointments</Link>
      </p>
    </div>
  );
};

export default PaymentSuccess;
