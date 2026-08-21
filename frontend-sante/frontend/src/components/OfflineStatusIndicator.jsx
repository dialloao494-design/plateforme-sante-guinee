import { useCallback, useEffect, useState } from 'react';
import {
  countPendingOutbox,
  downloadOfflineRecoveryExport,
  flushOutbox,
  getLastSyncAt,
  isBrowserOnline,
  listConflicts,
  listDeadOutbox,
  onOnlineStatusChange,
  onSyncStateChange,
  resolveConflict,
  retryDeadOutbox,
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
  const [deadItems, setDeadItems] = useState([]);
  const [recoveryMessage, setRecoveryMessage] = useState('');
  const [storageError, setStorageError] = useState('');
  const [syncFeedback, setSyncFeedback] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [count, last, rows, dead] = await Promise.all([
        countPendingOutbox(),
        getLastSyncAt(),
        listConflicts({ includeResolved: false }),
        listDeadOutbox(),
      ]);
      setPending(count);
      setLastSync(last);
      setConflicts(rows.slice(0, 5));
      setDeadItems(dead.slice(0, 5));
      setStorageError('');
    } catch {
      setStorageError("Le stockage hors ligne est illisible. N'effacez pas les données du navigateur; contactez le support de la clinique.");
    }
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

  useEffect(() => {
    if (!syncFeedback || syncFeedback.kind !== 'success') return undefined;
    const timer = window.setTimeout(() => setSyncFeedback(null), 4_000);
    return () => window.clearTimeout(timer);
  }, [syncFeedback]);

  const handleSyncNow = async () => {
    setRecoveryMessage('');
    setSyncFeedback(null);
    setSyncing(true);
    try {
      // A staff-requested retry must not remain hidden behind automatic
      // exponential backoff from an earlier network failure.
      const result = await flushOutbox(undefined, { forceRetry: true });
      await refresh();
      if (result?.failed > 0) {
        const text = `${result.failed} opération(s) n'ont pas pu être synchronisées. Exportez-les avant toute intervention sur ce navigateur.`;
        setRecoveryMessage(text);
        setSyncFeedback({ kind: 'error', text: 'Synchronisation incomplète' });
        setOpen(true);
      } else if (result?.synced > 0) {
        const text = `${result.synced} opération(s) synchronisée(s) avec succès.`;
        setRecoveryMessage(text);
        setSyncFeedback({ kind: 'success', text: 'Synchronisation terminée' });
        window.dispatchEvent(new CustomEvent('clinical:offline-sync-complete', {
          detail: result,
        }));
      } else if (result?.blocked > 0) {
        const text = `${result.blocked} opération(s) attendent d'abord la synchronisation du dossier patient. Réessayez; si le blocage persiste, exportez les données pour le support.`;
        setRecoveryMessage(text);
        setSyncFeedback({ kind: 'error', text: 'Dossier patient en attente' });
        setOpen(true);
      } else if (result?.offline) {
        const text = 'Le navigateur est encore hors ligne. Reconnectez le réseau avant de synchroniser.';
        setRecoveryMessage(text);
        setSyncFeedback({ kind: 'error', text: 'Connexion requise' });
        setOpen(true);
      } else if (result?.skipped) {
        const text = 'La session ne permet pas de synchroniser cette file. Reconnectez-vous avec le compte qui a créé ces opérations.';
        setRecoveryMessage(text);
        setSyncFeedback({ kind: 'error', text: 'Session à vérifier' });
        setOpen(true);
      } else {
        const text = "La file n'a pas avancé. Les données restent conservées sur cet appareil. Exportez-les pour récupération si une nouvelle tentative échoue.";
        setRecoveryMessage(text);
        setSyncFeedback({ kind: 'error', text: 'Synchronisation non terminée' });
        setOpen(true);
      }
    } catch {
      const text = "Synchronisation interrompue. Les opérations restent conservées sur cet appareil; réessayez lorsque la connexion est stable.";
      setRecoveryMessage(text);
      setSyncFeedback({ kind: 'error', text: 'Synchronisation interrompue' });
      setOpen(true);
    } finally {
      setSyncing(false);
    }
  };

  const handleResolve = async (id) => {
    await resolveConflict(id, 'accept_remote');
    await refresh();
  };

  const handleRetryConflict = async (id) => {
    await resolveConflict(id, 'retry_local');
    await flushOutbox();
    await refresh();
  };

  const handleRetryDead = async (id) => {
    await retryDeadOutbox(id);
    await flushOutbox();
    await refresh();
  };

  const handleExport = async () => {
    try {
      const bundle = await downloadOfflineRecoveryExport();
      const warning = bundle.integrity_warnings.length
        ? ` ${bundle.integrity_warnings.length} élément(s) endommagé(s) sont signalés dans le fichier.`
        : '';
      setRecoveryMessage(`${bundle.mutations.length} opération(s) exportée(s).${warning} Conservez ce fichier de santé chiffré ou remettez-le uniquement au support autorisé.`);
    } catch (error) {
      setRecoveryMessage(error?.message || 'Export de récupération impossible.');
    }
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

  const dockLabel = syncFeedback?.text || label;

  if (online && pending === 0 && conflicts.length === 0 && deadItems.length === 0 && !storageError && !open && !syncFeedback) {
    return null;
  }

  return (
    <div className="offline-status" aria-live="polite">
      <div className={`offline-status__dock${online && pending > 0 ? ' offline-status__dock--attention' : ''}${syncFeedback ? ` offline-status__dock--${syncFeedback.kind}` : ''}`}>
        <button
          type="button"
          className="offline-status__pill"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={`État réseau: ${dockLabel}. Afficher les détails.`}
        >
          <span className={`offline-status__dot ${dotClass}`} aria-hidden />
          <span>{dockLabel}</span>
        </button>
        {online && pending > 0 ? (
          <button
            type="button"
            className="offline-status__sync-now"
            onClick={handleSyncNow}
            disabled={syncing}
          >
            {syncing ? 'Synchronisation…' : syncFeedback?.kind === 'error' ? 'Réessayer' : 'Synchroniser maintenant'}
          </button>
        ) : null}
      </div>

      {open ? (
        <div className="offline-status__panel" role="region" aria-label="Détails hors ligne">
          <div className="offline-status__row">
            <span className="offline-status__label">Réseau</span>
            <span>{online ? 'Connecté' : 'Hors ligne'}</span>
          </div>

          {storageError ? <p className="offline-status__recovery-message" role="alert">{storageError}</p> : null}
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
                    Garder serveur
                  </button>
                  <button type="button" className="offline-status__btn" onClick={() => handleRetryConflict(c.id)}>
                    Renvoyer local
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          {deadItems.length > 0 ? (
            <div className="offline-conflicts">
              <strong>Échecs permanents ({deadItems.length})</strong>
              {deadItems.map((item) => (
                <div key={item.id} className="offline-conflicts__item">
                  <div>{item.entity_type} · {item.last_error || 'Échec de synchronisation'}</div>
                  {String(item.last_error || '').includes('Contenu hors ligne illisible') ? (
                    <small>Contenu endommagé — exportez-le pour récupération; ne le renvoyez pas.</small>
                  ) : (
                    <button type="button" className="offline-status__btn" onClick={() => handleRetryDead(item.id)}>
                      Réessayer
                    </button>
                  )}
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
              {syncing ? 'Synchronisation…' : 'Synchroniser maintenant'}
            </button>
            {(pending > 0 || conflicts.length > 0 || deadItems.length > 0) && (
              <button type="button" className="offline-status__btn" onClick={handleExport}>
                Exporter pour récupération
              </button>
            )}
            <button type="button" className="offline-status__btn" onClick={() => setOpen(false)}>
              Fermer
            </button>
          </div>
          {recoveryMessage && <p className="offline-status__recovery-message" role="status">{recoveryMessage}</p>}
        </div>
      ) : null}
    </div>
  );
}
