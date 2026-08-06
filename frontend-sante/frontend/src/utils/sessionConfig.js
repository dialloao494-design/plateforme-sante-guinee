/** Session idle timeout configuration (minutes). */

const parseMinutes = (value, fallback) => {
  const n = Number.parseInt(String(value || '').trim(), 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
};

// Pilot clinic: logout after 5 minutes of inactivity (override via VITE_SESSION_IDLE_MINUTES).
export const SESSION_IDLE_MINUTES = parseMinutes(
  import.meta.env.VITE_SESSION_IDLE_MINUTES,
  5
);

// Warn 1 minute before idle logout (override via VITE_SESSION_WARNING_MINUTES).
export const SESSION_WARNING_MINUTES = parseMinutes(
  import.meta.env.VITE_SESSION_WARNING_MINUTES,
  1
);

export const SESSION_IDLE_MS = SESSION_IDLE_MINUTES * 60 * 1000;
export const SESSION_WARNING_MS = SESSION_WARNING_MINUTES * 60 * 1000;
export const SESSION_WARN_AT_MS = Math.max(SESSION_IDLE_MS - SESSION_WARNING_MS, 60_000);
