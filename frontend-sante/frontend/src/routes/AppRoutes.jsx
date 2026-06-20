import { lazy } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import Home from "../pages/Home";
import Login from "../pages/Login";
import Signup from "../pages/Signup";
import ForgotPassword from "../pages/ForgotPassword.jsx";
import ResetPassword from "../pages/ResetPassword.jsx";
import VerifyEmail from "../pages/VerifyEmail.jsx";
import NotFound from "../pages/NotFound.jsx";
import ProtectedRoute from "./ProtectedRoute";
import AdminRouteEntry from "./AdminRouteEntry.jsx";

const Dashboard = lazy(() => import("../pages/Dashboard"));
const Doctors = lazy(() => import("../pages/Doctors"));
const DoctorProfile = lazy(() => import("../pages/DoctorProfile.jsx"));
const Appointments = lazy(() => import("../pages/Appointments"));
const DoctorDashboard = lazy(() => import("../pages/DoctorDashboard"));
const DoctorAppointments = lazy(() => import("../pages/DoctorAppointments"));
const DoctorMessages = lazy(() => import("../pages/DoctorMessages"));
const PatientDetails = lazy(() => import("../pages/PatientDetails"));
const Messages = lazy(() => import("../pages/Messages"));
const Patients = lazy(() => import("../pages/Patients"));
const Users = lazy(() => import("../pages/Users"));
const TeleconsultationHub = lazy(() => import("../pages/TeleconsultationHub.jsx"));
const ConsultationRoom = lazy(() => import("../pages/ConsultationRoom.jsx"));
const NotificationsPage = lazy(() => import("../pages/NotificationsPage.jsx"));
const PatientMedicalHistory = lazy(() => import("../pages/PatientMedicalHistory.jsx"));
const ReceptionDashboard = lazy(() => import("../pages/clinical/ReceptionDashboard.jsx"));
const DoctorClinicalDashboard = lazy(() => import("../pages/clinical/DoctorClinicalDashboard.jsx"));
const LabDashboard = lazy(() => import("../pages/clinical/LabDashboard.jsx"));
const PharmacyDashboard = lazy(() => import("../pages/clinical/PharmacyDashboard.jsx"));
const HospitalizationDashboard = lazy(() => import("../pages/clinical/HospitalizationDashboard.jsx"));
const UnifiedBillingDashboard = lazy(() => import("../pages/clinical/UnifiedBillingDashboard.jsx"));
const DischargeDashboard = lazy(() => import("../pages/clinical/DischargeDashboard.jsx"));
const RadiologyDashboard = lazy(() => import("../pages/clinical/RadiologyDashboard.jsx"));
const StaffNotificationCenter = lazy(() => import("../pages/clinical/StaffNotificationCenter.jsx"));
const ClinicalReportsDashboard = lazy(() => import("../pages/clinical/ClinicalReportsDashboard.jsx"));
const ClinicAdminDashboard = lazy(() => import("../pages/clinical/ClinicAdminDashboard.jsx"));
const PlatformFieldOnboard = lazy(() => import("../pages/platform/PlatformFieldOnboard.jsx"));
const PlatformClinicDirectory = lazy(() => import("../pages/platform/PlatformClinicDirectory.jsx"));
const PlatformClinicDetail = lazy(() => import("../pages/platform/PlatformClinicDetail.jsx"));
const ClinicOperationsDashboard = lazy(() => import("../pages/clinical/ClinicOperationsDashboard.jsx"));
const AccountProfile = lazy(() => import("../pages/AccountProfile.jsx"));
const ChangePassword = lazy(() => import("../pages/ChangePassword.jsx"));
const PlatformOwnerDashboard = lazy(() => import("../pages/platform/PlatformOwnerDashboard.jsx"));
const PlatformAccounts = lazy(() => import("../pages/platform/PlatformAccounts.jsx"));
const PlatformOwnerSetup = lazy(() => import("../pages/platform/PlatformOwnerSetup.jsx"));
const NutritionDashboard = lazy(() => import("../pages/clinical/NutritionDashboard.jsx"));
const ImmunizationDashboard = lazy(() => import("../pages/clinical/ImmunizationDashboard.jsx"));
const NursingCareDashboard = lazy(() => import("../pages/clinical/NursingCareDashboard.jsx"));
const PatientHistoryDashboard = lazy(() => import("../pages/clinical/PatientHistoryDashboard.jsx"));

const STAFF_ADMIN_ROLES = ["admin", "clinic_admin", "platform_admin"];
const PLATFORM_OWNER_ROLES = ["platform_owner"];
const PLATFORM_CLINIC_PROVISION_ROLES = ["platform_owner", "platform_admin"];
const CLINIC_ADMIN_ROLES = ["admin", "clinic_admin"];
const RECEPTION_ROLES = ["receptionist", "cashier"];
const BILLING_ROLES = ["receptionist", "cashier", "admin", "clinic_admin"];
const NUTRITION_ROLES = ["nutritionist", "midwife", "doctor", "admin", "clinic_admin", "platform_admin", "pev_agent", "nurse"];
const PEV_ROLES = ["pev_agent", "midwife", "receptionist", "doctor", "admin", "clinic_admin", "platform_admin"];
const NURSING_ROLES = ["nurse", "midwife", "admin", "clinic_admin", "receptionist", "doctor"];
const IMMUNIZATION_ROLES = PEV_ROLES.concat(["nutritionist"]);
const HOSPITALIZATION_ROLES = ["admin", "clinic_admin", "platform_admin", "receptionist", "doctor", "nurse"];
const PATIENT_HISTORY_ROLES = [
  "receptionist",
  "cashier",
  "doctor",
  "lab_technician",
  "pharmacist",
  "nutritionist",
  "pev_agent",
  "nurse",
  "midwife",
  "clinic_admin",
  "admin",
  "platform_admin",
];

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/platform/setup" element={<PlatformOwnerSetup />} />
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

      <Route
        path="/platform"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_CLINIC_PROVISION_ROLES}>
            <Navigate to="/platform/clinics" replace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/settings"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_OWNER_ROLES}>
            <PlatformOwnerDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/system"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_OWNER_ROLES}>
            <PlatformOwnerDashboard />
          </ProtectedRoute>
        }
      />

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

      <Route
        path="/clinical"
        element={
          <ProtectedRoute allowedRoles={CLINIC_ADMIN_ROLES.concat(['platform_admin', 'platform_owner'])}>
            <ClinicOperationsDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clinical/admin"
        element={
          <ProtectedRoute allowedRoles={CLINIC_ADMIN_ROLES}>
            <AdminRouteEntry />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/onboard"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_CLINIC_PROVISION_ROLES}>
            <PlatformFieldOnboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/onboard/:clinicId"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_CLINIC_PROVISION_ROLES}>
            <PlatformFieldOnboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/aasma"
        element={<Navigate to="/platform/onboard/17" replace />}
      />
      <Route
        path="/platform/clinics"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_CLINIC_PROVISION_ROLES}>
            <PlatformClinicDirectory />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/clinics/:clinicId/:section"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_CLINIC_PROVISION_ROLES}>
            <PlatformClinicDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/platform/clinics/:clinicId"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_CLINIC_PROVISION_ROLES}>
            <PlatformClinicDetail />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/reception"
        element={
          <ProtectedRoute allowedRoles={RECEPTION_ROLES}>
            <ReceptionDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="/clinical/cashier" element={<Navigate to="/clinical/reception" replace />} />

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
        path="/clinical/nutrition"
        element={
          <ProtectedRoute allowedRoles={NUTRITION_ROLES}>
            <NutritionDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/pev"
        element={
          <ProtectedRoute allowedRoles={PEV_ROLES}>
            <ImmunizationDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/immunization"
        element={<Navigate to="/clinical/pev" replace />}
      />

      <Route
        path="/clinical/nursing-care"
        element={
          <ProtectedRoute allowedRoles={NURSING_ROLES}>
            <NursingCareDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/clinical/midwife"
        element={<Navigate to="/clinical/pev" replace />}
      />

      <Route
        path="/clinical/patient-history"
        element={
          <ProtectedRoute allowedRoles={PATIENT_HISTORY_ROLES}>
            <PatientHistoryDashboard />
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
        path="/platform/accounts"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_OWNER_ROLES}>
            <PlatformAccounts />
          </ProtectedRoute>
        }
      />

      <Route
        path="/users"
        element={
          <ProtectedRoute allowedRoles={PLATFORM_OWNER_ROLES}>
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
