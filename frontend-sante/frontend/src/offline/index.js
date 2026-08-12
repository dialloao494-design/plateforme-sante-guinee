export {
  offlineDb,
  getMeta,
  setMeta,
  DB_NAME,
  DB_VERSION,
  purgeOfflinePrivacyState,
  clearOfflineDatabase,
  clearOfflineCacheStorage,
  buildOwnerKey,
} from './db.js';
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
export { readOfflineOwnerScope } from './sessionScope.js';
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
export {
  classifyRequest,
  isPatientSearchUrl,
  isCatalogUrl,
  isHisPatientRegisterUrl,
} from './entityTypes.js';
export {
  initOfflineSupport,
  isBrowserOnline,
  onOnlineStatusChange,
  registerServiceWorker,
} from './register.js';
export {
  onPatientReconciled,
  reconcilePatientCreate,
  buildRegistrationFingerprint,
  findPendingRegistrationByFingerprint,
  mergeReconciledPatient,
  isTempPatientId,
  lookupIdMap,
} from './reconcilePatient.js';
export {
  rewritePatientRefs,
  collectTempPatientIds,
  remapDependentRecords,
  resolveOutboxItemPatientRefs,
  sortOutboxForPatientDependencies,
} from './remapPatientRefs.js';
