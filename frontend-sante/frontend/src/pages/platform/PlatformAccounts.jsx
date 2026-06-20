/**
 * Technical accounts view — platform-level and orphan accounts only.
 * Clinic staff is managed per-clinic at /platform/clinics/:id.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import httpClient from '../../services/httpClient.js';
import { formatApiError } from '../../utils/apiError.js';
import PageSkeleton from '../../components/ui/PageSkeleton.jsx';
import '../Users.css';
import './PlatformOwner.css';

const ACCOUNT_FILTERS = [
  { value: 'platform', label: 'Comptes plateforme' },
  { value: 'orphan', label: 'Comptes orphelins' },
  { value: 'test', label: 'Comptes test' },
  { value: 'all', label: 'Tous (technique)' },
];

const TEST_EMAIL_PATTERNS = [
  /@sante-gn\.test$/i,
  /@pilot\.local$/i,
  /@clinic\.test$/i,
  /@patient\.gn$/i,
  /stress|e2e|staging/i,
];

function isTestEmail(email) {
  const e = String(email || '');
  return TEST_EMAIL_PATTERNS.some((re) => re.test(e));
}

function classifyAccount(user) {
  const role = String(user.role || '').toLowerCase();
  if (role === 'platform_owner' || role === 'platform_admin') return 'platform';
  if (user.clinic_id != null) return 'clinic_staff';
  if (isTestEmail(user.email)) return 'test';
  return 'orphan';
}

export default function PlatformAccounts() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('platform');

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await httpClient.get('/platform/users');
      setUsers(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError(formatApiError(err, 'Impossible de charger les comptes.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = useMemo(() => {
    const q = search.toLowerCase().trim();
    return users.filter((user) => {
      const bucket = classifyAccount(user);
      if (filter === 'platform' && bucket !== 'platform') return false;
      if (filter === 'orphan' && bucket !== 'orphan') return false;
      if (filter === 'test' && bucket !== 'test') return false;
      if (filter === 'all' && bucket === 'clinic_staff') return false;
      if (!q) return true;
      return (
        String(user.email || '').toLowerCase().includes(q)
        || String(user.role || '').toLowerCase().includes(q)
        || String(user.clinic_name || '').toLowerCase().includes(q)
      );
    });
  }, [users, search, filter]);

  return (
    <div className="users-page platform-accounts-page">
      <div className="users-page-inner">
        <Link to="/platform" className="platform-back-link">← Console plateforme</Link>
        <h1>Comptes techniques</h1>
        <p className="users-lead">
          Le personnel clinique se gère par établissement depuis{' '}
          <Link to="/platform/clinics">Cliniques</Link>. Cette page affiche uniquement les comptes
          plateforme, orphelins et de test — les comptes rattachés à une clinique sont masqués par défaut.
        </p>

        {error && (
          <div className="users-feedback users-feedback--error" role="alert">
            {error}
          </div>
        )}

        <div className="platform-filter-tabs platform-accounts-filters" role="tablist">
          {ACCOUNT_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              role="tab"
              aria-selected={filter === f.value}
              className={`platform-filter-tab${filter === f.value ? ' platform-filter-tab--active' : ''}`}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="users-toolbar">
          <input
            type="search"
            placeholder="Rechercher par e-mail, rôle ou clinique…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Filtrer les comptes"
          />
          <button type="button" className="users-refresh-btn" onClick={fetchUsers} disabled={loading}>
            Actualiser
          </button>
          <span className="users-count-pill">
            {filteredUsers.length} affiché(s) · comptes clinique exclus
          </span>
        </div>

        {loading && <PageSkeleton lines={6} />}

        {!loading && !error && filteredUsers.length === 0 && (
          <div className="users-feedback users-feedback--success">Aucun compte ne correspond à ce filtre.</div>
        )}

        {!loading && filteredUsers.length > 0 && (
          <div className="users-table-wrap">
            <table className="users-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Email</th>
                  <th>Rôle</th>
                  <th>Clinique</th>
                  <th>Catégorie</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => {
                  const bucket = classifyAccount(user);
                  return (
                    <tr key={user.id}>
                      <td>{user.id}</td>
                      <td>{user.email}</td>
                      <td>
                        <span className={`role-badge role-${user.role}`}>{user.role}</span>
                      </td>
                      <td>
                        {user.clinic_id ? (
                          <Link to={`/platform/clinics/${user.clinic_id}`}>
                            {user.clinic_name || `#${user.clinic_id}`}
                          </Link>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>{bucket}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
