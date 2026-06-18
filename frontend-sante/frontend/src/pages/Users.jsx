import { useEffect, useMemo, useState } from 'react';
import httpClient from '../services/httpClient.js';
import { formatApiError } from '../utils/apiError.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './Users.css';

const Users = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      // Use /platform/users — no trailing-slash redirect (avoids http downgrade → Network Error).
      const response = await httpClient.get('/platform/users');
      setUsers(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError(formatApiError(err, 'Impossible de charger les utilisateurs.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return users;
    return users.filter(
      (user) =>
        String(user.email || '')
          .toLowerCase()
          .includes(q) || String(user.role || '')
          .toLowerCase()
          .includes(q)
    );
  }, [users, search]);

  return (
    <div className="users-page">
      <div className="users-page-inner">
        <h1>Utilisateurs</h1>
        <p className="users-lead">
          Vue d’ensemble des comptes enregistrés sur la plateforme. La création du personnel de clinique
          (réception, laboratoire, pharmacie, etc.) se fait depuis{' '}
          <strong>Administration clinique → Utilisateurs</strong>.
        </p>

        {error && (
          <div className="users-feedback users-feedback--error" role="alert">
            {error}
          </div>
        )}

        <div className="users-toolbar">
          <input
            type="search"
            placeholder="Rechercher par e-mail ou rôle…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Filtrer les utilisateurs"
          />
          <button type="button" className="users-refresh-btn" onClick={fetchUsers} disabled={loading}>
            Actualiser
          </button>
          <span className="users-count-pill">{filteredUsers.length} affiché(s) · {users.length} au total</span>
        </div>

        {loading && <PageSkeleton lines={6} />}

        {!loading && !error && filteredUsers.length === 0 && (
          <div className="users-feedback users-feedback--success">Aucun utilisateur ne correspond à ce filtre.</div>
        )}

        {!loading && filteredUsers.length > 0 && (
          <div className="users-table-wrap">
            <table className="users-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Email</th>
                  <th>Rôle</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.email}</td>
                    <td>
                      <span className={`role-badge role-${user.role}`}>{user.role}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Users;
