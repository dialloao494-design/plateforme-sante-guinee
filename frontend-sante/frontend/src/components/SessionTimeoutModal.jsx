import './SessionTimeoutModal.css';
import { SESSION_IDLE_MINUTES, SESSION_WARNING_MINUTES } from '../utils/sessionConfig.js';

export default function SessionTimeoutModal({ open, secondsLeft, onStaySignedIn, onLogout }) {
  if (!open) {
    return null;
  }

  const minutes = Math.max(1, Math.ceil((secondsLeft || 60) / 60));

  return (
    <div className="session-timeout-overlay" role="dialog" aria-modal="true" aria-labelledby="session-timeout-title">
      <div className="session-timeout-card">
        <h2 id="session-timeout-title">Session sur le point d&apos;expirer</h2>
        <p>
          Votre session sera fermée automatiquement dans environ{' '}
          <strong>{minutes} min</strong> par mesure de sécurité
          (délai configuré : {SESSION_IDLE_MINUTES} min, avertissement {SESSION_WARNING_MINUTES} min avant).
        </p>
        <div className="session-timeout-actions">
          <button type="button" className="session-timeout-primary" onClick={onStaySignedIn}>
            Rester connecté
          </button>
          <button type="button" className="session-timeout-secondary" onClick={onLogout}>
            Se déconnecter
          </button>
        </div>
      </div>
    </div>
  );
}
