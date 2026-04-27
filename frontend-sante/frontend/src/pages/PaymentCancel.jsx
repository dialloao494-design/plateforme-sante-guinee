import { Link } from 'react-router-dom';

const PaymentCancel = () => {
  return (
    <div style={{ padding: 24 }}>
      <h1>Paiement annulé</h1>
      <p>Le paiement a été interrompu. Votre rendez-vous reste en attente et non payé.</p>
      <p>
        <Link to="/appointments">Retour aux rendez-vous</Link>
      </p>
      <p>
        <Link to="/appointments">Réessayer le paiement</Link>
      </p>
    </div>
  );
};

export default PaymentCancel;
