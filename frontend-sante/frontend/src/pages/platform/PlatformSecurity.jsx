import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import platformApi from '../../services/platformApi.js';
import { formatApiError } from '../../utils/apiError.js';
import PageSkeleton from '../../components/ui/PageSkeleton.jsx';
import '../clinical/clinical.css';
import './PlatformOwner.css';

export default function PlatformSecurity() {
  const [accounts, setAccounts] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    Promise.all([platformApi.listAccounts({ category: 'production' }), platformApi.getSettings()])
      .then(([accountsResponse, settingsResponse]) => { if (active) { setAccounts(Array.isArray(accountsResponse.data) ? accountsResponse.data : []); setSettings(settingsResponse.data); } })
      .catch((err) => active && setError(formatApiError(err, 'Impossible de charger la posture de sécurité.')))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);
  const signals = useMemo(() => ({
    active: accounts.filter((a) => a.is_active).length,
    withoutMfa: accounts.filter((a) => a.is_active && !a.mfa_enabled).length,
    locked: accounts.filter((a) => a.locked_until).length,
    sessions: accounts.reduce((sum, a) => sum + (a.active_sessions || 0), 0),
  }), [accounts]);
  const review = accounts.filter((a) => a.locked_until || a.failed_login_attempts > 0 || (a.is_active && !a.mfa_enabled));

  return <main className="platform-owner-page">
    <header className="platform-admin-heading"><div><p className="clinical-eyebrow">Protection des accès</p><h1>Sécurité</h1><p>Repérez les comptes exposés sans ajouter de complexité au quotidien des équipes cliniques.</p></div><div className="platform-environment"><span>Environnement</span><strong>{settings?.environment || '—'}</strong></div></header>
    {error && <p className="clinical-error" role="alert">{error}</p>}
    {loading ? <PageSkeleton lines={8} /> : <>
      <dl className="platform-summary-strip"><div><dt>Comptes actifs</dt><dd>{signals.active}</dd></div><div><dt>Sans MFA</dt><dd>{signals.withoutMfa}</dd></div><div><dt>Comptes verrouillés</dt><dd>{signals.locked}</dd></div><div><dt>Sessions actives</dt><dd>{signals.sessions}</dd></div></dl>
      <section className="platform-security-review" aria-labelledby="security-review-title">
        <div className="platform-section-heading"><div><p className="clinical-eyebrow">Revue conseillée</p><h2 id="security-review-title">Comptes à examiner</h2></div><Link to="/platform/accounts">Gérer tous les comptes</Link></div>
        {review.length === 0 ? <div className="platform-clear-state"><span aria-hidden="true">✓</span><div><strong>Aucun signal prioritaire</strong><p>Aucun verrouillage ni échec de connexion n’est visible.</p></div></div> : <ul className="platform-security-list">{review.slice(0, 12).map((account) => <li key={account.id}><div><strong>{account.email}</strong><span>{account.clinic_name || 'Non rattaché'} · {account.role}</span></div><div className="platform-security-reasons">{account.locked_until && <span>Verrouillé</span>}{account.failed_login_attempts > 0 && <span>{account.failed_login_attempts} échec(s)</span>}{account.is_active && !account.mfa_enabled && <span>MFA inactive</span>}</div><Link to={`/platform/accounts?q=${encodeURIComponent(account.email)}`}>Examiner</Link></li>)}</ul>}
      </section>
      <aside className="platform-guidance-note"><h2>Une sécurité adaptée au terrain</h2><p>La MFA reste ciblée sur les rôles privilégiés. Les équipes cliniques conservent un parcours de connexion simple, avec récupération assistée et révocation immédiate en cas de risque.</p></aside>
    </>}
  </main>;
}
