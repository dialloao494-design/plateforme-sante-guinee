import { useEffect, useMemo, useState } from 'react';
import api from '../services/api.js';

const Users = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [success, setSuccess] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axiosInstance.get('/users');
      setUsers(response.data);
      setSuccess('Users loaded successfully');
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = useMemo(() => {
    return users.filter(
      (user) =>
        user.email.toLowerCase().includes(search.toLowerCase()) ||
        user.role.toLowerCase().includes(search.toLowerCase())
    );
  }, [users, search]);

  return (
    <div className="users-page">
      <h1>User Management (Admin)</h1>

      {loading && <p>Loading users...</p>}
      {error && <p className="error">Error: {error}</p>}
      {success && <p className="success">{success}</p>}

      <div className="users-controls">
        <input
          type="text"
          placeholder="Search by email or role..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span className="users-count">Total users: {users.length}</span>
      </div>

      {filteredUsers.length === 0 ? (
        <p>No users found.</p>
      ) : (
        <table className="users-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.email}</td>
                <td>
                  <span className={`role-badge role-${user.role}`}>
                    {user.role}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <style>{`
        .users-page {
          padding: 20px;
          max-width: 1000px;
          margin: 0 auto;
        }
        .users-controls {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          gap: 20px;
        }
        .users-controls input {
          flex: 1;
          padding: 10px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        .users-count {
          font-weight: bold;
          color: #666;
        }
        .users-table {
          width: 100%;
          border-collapse: collapse;
          border: 1px solid #ddd;
        }
        .users-table thead {
          background-color: #f5f5f5;
        }
        .users-table th {
          padding: 12px;
          text-align: left;
          border-bottom: 2px solid #ddd;
          font-weight: bold;
        }
        .users-table td {
          padding: 12px;
          border-bottom: 1px solid #ddd;
        }
        .role-badge {
          padding: 4px 12px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: bold;
        }
        .role-patient {
          background-color: #e3f2fd;
          color: #1976d2;
        }
        .role-doctor {
          background-color: #f3e5f5;
          color: #7b1fa2;
        }
        .role-admin {
          background-color: #ffe0b2;
          color: #e65100;
        }
        .error {
          color: #d32f2f;
          font-weight: bold;
          margin-bottom: 20px;
        }
        .success {
          color: #388e3c;
          font-weight: bold;
          margin-bottom: 20px;
        }
      `}</style>
    </div>
  );
};

export default Users;
