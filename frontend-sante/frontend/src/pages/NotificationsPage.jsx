import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { notificationsAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatApiError } from '../utils/apiError.js';
import { getRoleHomePath } from '../utils/rolePaths.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './NotificationsPage.css';

export default function NotificationsPage() {
  const { user } = useAuth();
  const dashboardHref = useMemo(() => getRoleHomePath(user?.role), [user?.role]);

  const [channelsPayload, setChannelsPayload] = useState(null);
  const [inbox, setInbox] = useState(null);
  const [loading, setLoading] = useState(true);
  const [channelsError, setChannelsError] = useState('');
  const [inboxError, setInboxError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setChannelsError('');
    setInboxError('');
    try {
      const chRes = await notificationsAPI.channels();
      setChannelsPayload(chRes.data);
    } catch (err) {
      setChannelsPayload(null);
      setChannelsError(formatApiError(err, 'Impossible de charger les canaux.'));
    }
    try {
      const listRes = await notificationsAPI.list();
      setInbox(listRes.data);
    } catch (err) {
      setInbox({ items: [], message: null });
      setInboxError(formatApiError(err, 'Impossible de charger la boîte de réception.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const channels = Array.isArray(channelsPayload?.channels) ? channelsPayload.channels : [];

  const inboxItems = Array.isArray(inbox?.items) ? inbox.items : [];
  const inboxEmpty = !loading && !inboxError && inboxItems.length === 0;

  return (
    <div className="notifications-page ds-page">
      <header className="notifications-header">
        <div>
          <p className="notifications-eyebrow">Centre de notifications</p>
          <h1>Rappels &amp; confirmations</h1>
          <p className="notifications-lead">
            État des canaux SMS / email et boîte de réception applicative. Les envois réels se branchent sur le backend
            sans changer cette page.
          </p>
        </div>
        <Link className="btn btn-secondary" to={dashboardHref}>
          Tableau de bord
        </Link>
      </header>

      {loading && (
        <div className="notifications-loading">
          <PageSkeleton lines={5} />
        </div>
      )}

      {!loading && (
        <div className="notifications-grid">
          <section className="notifications-card">
            <h2>Canaux prévus</h2>
            {channelsError ? (
              <div className="notifications-banner notifications-banner--error" role="alert">
                {channelsError}
              </div>
            ) : (
              <>
                <p className="notifications-muted">
                  {channelsPayload?.enabled
                    ? 'Au moins un canal transactionnel est activé côté serveur.'
                    : 'Aucun canal transactionnel n’est encore activé — configuration serveur requise.'}
                </p>
                <ul className="notifications-channel-list">
                  {channels.map((ch) => (
                    <li key={ch.id} className="notifications-channel-item">
                      <div className="notifications-channel-top">
                        <strong>{ch.label}</strong>
                        <span className={`notifications-status notifications-status--${ch.status || 'planned'}`}>
                          {ch.status === 'planned' ? 'Prévu' : ch.status === 'live' ? 'Actif' : ch.status}
                        </span>
                      </div>
                      {Array.isArray(ch.use_cases) && ch.use_cases.length > 0 && (
                        <p className="notifications-usecases">{ch.use_cases.join(' · ')}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>

          <section className="notifications-card">
            <h2>Boîte de réception</h2>
            {inboxError && (
              <div className="notifications-banner notifications-banner--error" role="alert">
                <span>{inboxError}</span>
                <button type="button" className="btn btn-secondary notifications-retry" onClick={() => setReloadKey((k) => k + 1)}>
                  Réessayer
                </button>
              </div>
            )}
            {!inboxError && inbox?.message && inboxItems.length === 0 && (
              <p className="notifications-muted">{inbox.message}</p>
            )}
            {!inboxError && inboxItems.length > 0 ? (
              <ul className="notifications-inbox-list">
                {inboxItems.map((item) => (
                  <li key={item.id} className="notifications-inbox-item">
                    <div className="notifications-inbox-item-top">
                      <span className="notifications-inbox-subject">{item.subject}</span>
                      <time dateTime={item.created_at}>
                        {item.created_at
                          ? new Date(item.created_at).toLocaleString('fr-FR', {
                              dateStyle: 'short',
                              timeStyle: 'short',
                            })
                          : ''}
                      </time>
                    </div>
                    <p className="notifications-inbox-body">{item.body}</p>
                    <span className="notifications-inbox-channel">{item.channel}</span>
                  </li>
                ))}
              </ul>
            ) : null}
            {inboxEmpty && !inbox?.message && (
              <p className="notifications-empty">
                Les rappels de rendez-vous et accusés de lecture apparaîtront ici après des événements (ex. paiement
                confirmé).
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
