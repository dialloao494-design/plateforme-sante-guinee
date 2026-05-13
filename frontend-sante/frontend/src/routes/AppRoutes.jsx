import { Routes, Route } from "react-router-dom";
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
import PaymentSuccess from "../pages/PaymentSuccess";
import PaymentCancel from "../pages/PaymentCancel";
import Messages from "../pages/Messages";
import Patients from "../pages/Patients";
import Users from "../pages/Users";
import TeleconsultationHub from "../pages/TeleconsultationHub.jsx";
import ConsultationRoom from "../pages/ConsultationRoom.jsx";
import ProtectedRoute from "./ProtectedRoute";

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor", "admin"]}>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctors/:doctorId"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor", "admin"]}>
            <DoctorProfile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctors"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor", "admin"]}>
            <Doctors />
          </ProtectedRoute>
        }
      />
      <Route
        path="/appointments"
        element={
          <ProtectedRoute allowedRoles={["patient", "admin"]}>
            <Appointments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/dashboard"
        element={
          <ProtectedRoute allowedRoles={["doctor", "admin"]}>
            <DoctorDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/appointments"
        element={
          <ProtectedRoute allowedRoles={["doctor", "admin"]}>
            <DoctorAppointments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/messages"
        element={
          <ProtectedRoute allowedRoles={["doctor", "admin"]}>
            <DoctorMessages />
          </ProtectedRoute>
        }
      />
      <Route
        path="/doctor/patient/:id"
        element={
          <ProtectedRoute allowedRoles={["doctor", "admin"]}>
            <PatientDetails />
          </ProtectedRoute>
        }
      />
      <Route
        path="/success"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor"]}>
            <PaymentSuccess />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cancel"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor"]}>
            <PaymentCancel />
          </ProtectedRoute>
        }
      />
      <Route
        path="/messages/:appointmentId"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor"]}>
            <Messages />
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Users />
          </ProtectedRoute>
        }
      />
      <Route
        path="/patients"
        element={
          <ProtectedRoute allowedRoles={["doctor", "admin"]}>
            <Patients />
          </ProtectedRoute>
        }
      />
      <Route
        path="/teleconsultation"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor", "admin"]}>
            <TeleconsultationHub />
          </ProtectedRoute>
        }
      />
      <Route
        path="/consultation/:appointmentId"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor", "admin"]}>
            <ConsultationRoom />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

export default AppRoutes;