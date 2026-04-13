import { Routes, Route } from "react-router-dom";
import Home from "../pages/Home";
import Login from "../pages/Login";
import Signup from "../pages/Signup";
import Dashboard from "../pages/Dashboard";
import Doctors from "../pages/Doctors";
import Appointments from "../pages/Appointments";
import PaymentSuccess from "../pages/PaymentSuccess";
import PaymentCancel from "../pages/PaymentCancel";
import Patients from "../pages/Patients";
import Users from "../pages/Users";
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
        path="/doctors"
        element={
          <ProtectedRoute allowedRoles={["doctor", "admin"]}>
            <Doctors />
          </ProtectedRoute>
        }
      />
      <Route
        path="/appointments"
        element={
          <ProtectedRoute allowedRoles={["patient", "doctor", "admin"]}>
            <Appointments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/success"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <PaymentSuccess />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cancel"
        element={
          <ProtectedRoute allowedRoles={["patient"]}>
            <PaymentCancel />
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
          <ProtectedRoute allowedRoles={["doctor"]}>
            <Patients />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

export default AppRoutes;