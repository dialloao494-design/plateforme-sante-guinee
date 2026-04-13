import { Link } from 'react-router-dom';

const PaymentCancel = () => {
  return (
    <div style={{ padding: 24 }}>
      <h1>Payment Canceled</h1>
      <p>Payment cancelled. Your appointment remains pending and unpaid.</p>
      <p>
        <Link to="/appointments">Back to Appointments</Link>
      </p>
      <p>
        <Link to="/appointments">Retry payment</Link>
      </p>
    </div>
  );
};

export default PaymentCancel;
