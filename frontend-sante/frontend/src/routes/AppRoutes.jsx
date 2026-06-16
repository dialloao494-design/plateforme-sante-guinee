import { Routes, Route, Navigate } from "react-router-dom";

import Home from "../pages/Home";
import Login from "../pages/Login";
import Signup from "../pages/Signup";
import Dashboard from "../pages/Dashboard";
import Doctors from "../pages/Doctors";
import DoctorProfile from "../pages/DoctorProfile.jsx";
import Appointments from "../pages/Appointments";
import DoctorDashboard from "../pages/DoctorDashboard";
import DoctorAppointments from "../pages/DoctorAppointments";
import DoctorMessages from "../pages/DoctorMessages";
import PatientDetails from "../pages/PatientDetails";
import Messages from "../pages/Messages";
import Patients from "../pages/Patients";
import Users from "../pages/Users";
import TeleconsultationHub from "../pages/TeleconsultationHub.jsx";
import ConsultationRoom from "../pages/ConsultationRoom.jsx";
import NotificationsPage from "../pages/NotificationsPage.jsx";
import PatientMedicalHistory from "../pages/PatientMedicalHistory.jsx";
import NotFound from "../pages/NotFound.jsx";
import ReceptionDashboard from "../pages/clinical/ReceptionDashboard.jsx";
import DoctorClinicalDashboard from "../pages/clinical/DoctorClinicalDashboard.jsx";
import LabDashboard from "../pages/clinical/LabDashboard.jsx";
import PharmacyDashboard from "../pages/clinical/PharmacyDashboard.jsx";
import HospitalizationDashboard from "../pages/clinical/HospitalizationDashboard.jsx";
import UnifiedBillingDashboard from "../pages/clinical/UnifiedBillingDashboard.jsx";
import DischargeDashboard from "../pages/clinical/DischargeDashboard.jsx";
import RadiologyDashboard from "../pages/clinical/RadiologyDashboard.jsx";
import StaffNotificationCenter from "../pages/clinical/StaffNotificationCenter.jsx";
import ClinicalReportsDashboard from "../pages/clinical/ClinicalReportsDashboard.jsx";
import AdminClinicalDashboard from "../pages/clinical/AdminClinicalDashboard.jsx";
import ClinicOperationsDashboard from "../pages/clinical/ClinicOperationsDashboard.jsx";
import AccountProfile from "../pages/AccountProfile.jsx";
import ChangePassword from "../pages/ChangePassword.jsx";
import ProtectedRoute from "./ProtectedRoute";

const STAFF_ADMIN_ROLES = ["admin", "clinic_admin", "platform_admin"];
const CLINIC_ADMIN_ROLES = ["admin", "clinic_admin"];
const RECEPTION_ROLES = ["receptionist", "cashier"];
const BILLING_ROLES = ["receptionist", "cashier", "admin", "clinic_admin"];
const HOSPITALIZATION_ROLES = ["admin", "clinic_admin", "platform_admin", "receptionist", "doctor"];

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route
        path="/account/profile"
        element={
          <ProtectedRoute>
            <AccountProfile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/account/password"
        element={
          <ProtectedRoute>
            <ChangePassword />
          </ProtectedRoute>
        }
      />

      {/* Patient portal */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctors/:doctorId"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <DoctorProfile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctors"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <Doctors />
          </ProtectedRoute>
        }
      />
      <Route
        path="/my-records"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <PatientMedicalHistory />
          </ProtectedRoute>
        }
      />
      <Route
        path="/appointments"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <Appointments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/messages/:appointmentId"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <Messages />
          </ProtectedRoute>
        }
      />
      <Route
        path="/teleconsultation"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor"]}>
            <TeleconsultationHub />
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor"]}>
            <NotificationsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/consultation/:appointmentId"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor"]}>
            <ConsultationRoom />
          </ProtectedRoute>
        }
      />

      {/* Legacy telehealth doctor routes */}
      <Route
        path="/doctor/dashboard"
        element={
          <ProtectedRoute allowedRoles={["doctor"]}>
            <DoctorDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/appointments"
        element={
          <ProtectedRoute allowedRoles={["doctor"]}>
            <DoctorAppointments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/messages"
        element={
          <ProtectedRoute allowedRoles={["doctor"]}>
            <DoctorMessages />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patient/:id"
        element={
          <ProtectedRoute allowedRoles={["doctor"]}>
            <PatientDetails />
          </ProtectedRoute>
        }
      />

      {/* Manager — operations dashboard only */}
      <Route
        path="/clinical"
        element={
          <ProtectedRoute allowedRoles={CLINIC_ADMIN_ROLES.concat(['platform_admin'])}>
            <ClinicOperationsDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clinical/admin"
        element={
          <ProtectedRoute allowedRoles={STAFF_ADMIN_ROLES}>
            <AdminClinicalDashboard />
          </ProtectedRoute>
        }
      />

      {/* Reception (merged with cashier) */}
      <Route
        path="/clinical/reception"
        element={
          <ProtectedRoute allowedRoles={RECEPTION_ROLES}>
            <ReceptionDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/clinical/cashier" element={<Navigate to="/clinical/reception" replace />} />

      {/* Role workstations */}
      <Route
        path="/clinical/doctor"
        element={
          <ProtectedRoute allowedRoles={["doctor"]}>
            <DoctorClinicalDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clinical/lab"
        element={
          <ProtectedRoute allowedRoles={["lab_technician"]}>
            <LabDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clinical/pharmacy"
        element={
          <ProtectedRoute allowedRoles={["pharmacist"]}>
            <PharmacyDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/clinical/revenue" element={<Navigate to="/clinical/billing" replace />} />

      <Route
        path="/clinical/billing"
        element={
          <ProtectedRoute allowedRoles={BILLING_ROLES}>
            <UnifiedBillingDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/hospitalization"
        element={
          <ProtectedRoute allowedRoles={HOSPITALIZATION_ROLES}>
            <HospitalizationDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/discharge"
        element={
          <ProtectedRoute allowedRoles={HOSPITALIZATION_ROLES}>
            <DischargeDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/radiology"
        element={
          <ProtectedRoute allowedRoles={["admin", "clinic_admin", "doctor", "lab_technician", "platform_admin"]}>
            <RadiologyDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/notifications"
        element={
          <ProtectedRoute allowedRoles={["admin", "clinic_admin", "receptionist", "doctor", "platform_admin"]}>
            <StaffNotificationCenter />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/reports"
        element={
          <ProtectedRoute allowedRoles={["admin", "clinic_admin", "receptionist", "doctor", "cashier", "platform_admin"]}>
            <ClinicalReportsDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/users"
        element={
          <ProtectedRoute allowedRoles={['admin', 'clinic_admin', 'platform_admin']}>
            <Users />
          </ProtectedRoute>
        }
      />
      <Route
        path="/patients"
        element={
          <ProtectedRoute allowedRoles={['doctor']}>
            <Patients />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

export default AppRoutes;
