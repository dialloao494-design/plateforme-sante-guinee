// Shared by routing and replay. A first-party probe may override a stale browser flag.
let online = typeof navigator === 'undefined' ? true : navigator.onLine !== false;
const listeners = new Set();
export function isBrowserOnline() { return online; }
export function setOnlineStatus(value) {
  if (online === value) return;
  online = value;
  for (const listener of listeners) {
    try { listener(online); } catch { /* listener isolation */ }
  }
}
export function onOnlineStatusChange(listener) {
  listeners.add(listener);
  listener(online);
  return () => listeners.delete(listener);
}
