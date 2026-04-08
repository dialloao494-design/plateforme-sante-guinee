import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Dashboard.css';

const Dashboard = () => {
  const { user } = useAuth();
  const role = localStorage.getItem('user_role');

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      <div className="user-info">
        <h2>Welcome, {user?.email || 'User'}</h2>
        {role && <p className="user-role">Role: {role.charAt(0).toUpperCase() + role.slice(1)}</p>}
      </div>
      <div className="dashboard-actions">
        {role === 'patient' && (
          <>
            <Link to="/appointments" className="action-button">My Appointments</Link>
            <Link to="/doctors" className="action-button">Find Doctors</Link>
          </>
        )}
        {role === 'doctor' && (
          <>
            <Link to="/doctors" className="action-button">My Profile</Link>
            <Link to="/appointments" className="action-button">My Appointments</Link>
          </>
        )}
        {role === 'admin' && (
          <>
            <Link to="/users" className="action-button">Manage Users</Link>
            <Link to="/appointments" className="action-button">All Appointments</Link>
            <Link to="/doctors" className="action-button">Manage Doctors</Link>
          </>
        )}
        {!role && (
          <>
            <Link to="/doctors" className="action-button">View Doctors</Link>
            <Link to="/appointments" className="action-button">My Appointments</Link>
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;