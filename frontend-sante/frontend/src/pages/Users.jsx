import { Navigate } from 'react-router-dom';

/** Legacy route — clinic staff is managed per clinic. */
export default function Users() {
  return <Navigate to="/platform/clinics" replace />;
}
