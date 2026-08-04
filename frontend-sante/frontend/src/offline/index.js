export { offlineDb, getMeta, setMeta, DB_NAME, DB_VERSION } from './db.js';
export {
  enqueueMutation,
  getPendingOutbox,
  countPendingOutbox,
  generateClientRequestId,
  computeBackoffMs,
  buildOptimisticResponse,
  OUTBOX_STATUS,
} from './outbox.js';
export {
  flushOutbox,
  startAutoSync,
  stopAutoSync,
  replayOutboxItem,
  getLastSyncAt,
  onSyncStateChange,
} from './sync.js';
export {
  resolveLastWriteWins,
  mergeLastWriteWins,
  listConflicts,
  resolveConflict,
  recordConflict,
} from './conflict.js';
export {
  cacheGetResponse,
  getCachedGet,
  cachePatientRecord,
  getCachedPatient,
  buildOfflineCacheKey,
} from './cache.js';
export { classifyRequest, isPatientSearchUrl, isCatalogUrl } from './entityTypes.js';
export {
  initOfflineSupport,
  isBrowserOnline,
  onOnlineStatusChange,
  registerServiceWorker,
} from './register.js';
