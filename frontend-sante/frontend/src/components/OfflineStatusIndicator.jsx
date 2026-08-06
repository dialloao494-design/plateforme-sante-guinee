import { useCallback, useEffect, useState } from 'react';
import {
  countPendingOutbox,
  flushOutbox,
  getLastSyncAt,
  isBrowserOnline,
  listConflicts,
  onOnlineStatusChange,
  onSyncStateChange,
  resolveConflict,
} from '../offline/index.js';
import './OfflineStatusIndicator.css';

function formatRelativeTime(ts) {
  if (!ts) return '—';
  const diff = Date.now() - ts;
  if (diff < 60_000) return 'à l\'instant';
  if (diff < 3_600_000) return `il y a ${Math.floor(diff / 60_000)} min`;
  return new Date(ts).toLocaleString('fr-FR');
}

export default function OfflineStatusIndicator() {
  const [online, setOnline] = useState(isBrowserOnline());
  const [pending, setPending] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  const [open, setOpen] = useState(false);
  const [conflicts, setConflicts] = useState([]);

  const refresh = useCallback(async () => {
    const [count, last, rows] = await Promise.all([
      countPendingOutbox(),
      getLastSyncAt(),
      listConflicts({ includeResolved: false }),
    ]);
    setPending(count);
    setLastSync(last);
    setConflicts(rows.slice(0, 5));
  }, []);

  useEffect(() => {
    const unsubOnline = onOnlineStatusChange(setOnline);
    const unsubSync = onSyncStateChange((state) => {
      if (typeof state.flushing === 'boolean') setSyncing(state.flushing);
      refresh();
    });
    refresh();
    const timer = window.setInterval(refresh, 20_000);
    return () => {
      unsubOnline();
      unsubSync();
      window.clearInterval(timer);
    };
  }, [refresh]);

  const handleSyncNow = async () => {
    setSyncing(true);
    try {
      await flushOutbox();
      await refresh();
    } finally {
      setSyncing(false);
    }
  };

  const handleResolve = async (id) => {
    await resolveConflict(id, 'dismissed');
    await refresh();
  };

  const dotClass = syncing
    ? 'offline-status__dot--syncing'
    : online
      ? 'offline-status__dot--online'
      : 'offline-status__dot--offline';

  const label = syncing
    ? 'Synchronisation…'
    : online
      ? pending > 0
        ? `En ligne · ${pending} en attente`
        : 'En ligne'
      : `Hors ligne${pending > 0 ? ` · ${pending} en file` : ''}`;

  if (online && pending === 0 && conflicts.length === 0 && !open) {
    return null;
  }

  return (
    <div className="offline-status" aria-live="polite">
      <button
        type="button"
        className="offline-status__pill"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`État réseau: ${label}`}
      >
        <span className={`offline-status__dot ${dotClass}`} aria-hidden />
        <span>{label}</span>
      </button>

      {open ? (
        <div className="offline-status__panel" role="region" aria-label="Détails hors ligne">
          <div className="offline-status__row">
            <span className="offline-status__label">Réseau</span>
            <span>{online ? 'Connecté' : 'Hors ligne'}</span>
          </div>
          <div className="offline-status__row">
            <span className="offline-status__label">File d&apos;attente</span>
            <span>{pending}</span>
          </div>
          <div className="offline-status__row">
            <span className="offline-status__label">Dernière sync</span>
            <span>{formatRelativeTime(lastSync)}</span>
          </div>

          {conflicts.length > 0 ? (
            <div className="offline-conflicts">
              <strong>Conflits ({conflicts.length})</strong>
              {conflicts.map((c) => (
                <div key={c.id} className="offline-conflicts__item">
                  <div>{c.entity_type} · {c.resolution || 'pending'}</div>
                  <button
                    type="button"
                    className="offline-status__btn"
                    onClick={() => handleResolve(c.id)}
                  >
                    Ignorer
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          <div className="offline-status__actions">
            <button
              type="button"
              className="offline-status__btn"
              onClick={handleSyncNow}
              disabled={!online || syncing}
            >
              Synchroniser
            </button>
            <button type="button" className="offline-status__btn" onClick={() => setOpen(false)}>
              Fermer
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
