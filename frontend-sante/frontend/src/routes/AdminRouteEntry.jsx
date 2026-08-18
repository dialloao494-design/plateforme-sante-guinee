import { lazy } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { normalizeRole } from '../utils/roleAccess.js';

const ClinicAdminDashboard = lazy(() => import('../pages/clinical/ClinicAdminDashboard.jsx'));

/**
 * /clinical/admin — clinic_admin and admin only.
 * Platform owner is redirected to /platform/clinics (clinic creation lives there).
 */
export default function AdminRouteEntry() {
  const { user } = useAuth();
  const role = normalizeRole(user?.role);

  if (role === 'platform_owner') {
    return <Navigate to="/platform/clinics" replace />;
  }

  if (role === 'clinic_admin' || role === 'admin') {
    return <ClinicAdminDashboard />;
  }

  if (role === 'platform_admin') {
    return <Navigate to="/platform/clinics" replace />;
  }

  return <Navigate to="/clinical" replace />;
}
