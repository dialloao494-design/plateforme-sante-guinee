import './EmptyState.css';

function Illustration({ preset }) {
  const common = { className: 'empty-state-svg', viewBox: '0 0 120 120', role: 'img', 'aria-hidden': true };

  if (preset === 'video') {
    return (
      <svg {...common}>
        <defs>
          <linearGradient id="es-vid-a" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0d9488" />
            <stop offset="100%" stopColor="#0f766e" />
          </linearGradient>
        </defs>
        <rect x="12" y="24" width="96" height="72" rx="14" fill="#0f172a" opacity="0.92" />
        <rect x="22" y="34" width="76" height="52" rx="8" fill="url(#es-vid-a)" opacity="0.35" />
        <polygon points="52,52 52,76 74,64" fill="#fff" opacity="0.9" />
        <circle cx="88" cy="44" r="6" fill="#22c55e" />
        <rect x="12" y="98" width="96" height="8" rx="4" fill="var(--color-border, #e2e8f0)" />
      </svg>
    );
  }

  if (preset === 'calendar') {
    return (
      <svg {...common}>
        <rect x="20" y="28" width="80" height="76" rx="12" fill="var(--color-surface, #fff)" stroke="var(--color-border, #e2e8f0)" strokeWidth="2" />
        <rect x="20" y="28" width="80" height="22" rx="12" fill="rgba(13, 148, 136, 0.18)" />
        <rect x="28" y="18" width="8" height="18" rx="2" fill="#0d9488" />
        <rect x="84" y="18" width="8" height="18" rx="2" fill="#0d9488" />
        <rect x="32" y="58" width="14" height="12" rx="2" fill="rgba(13, 148, 136, 0.35)" />
        <rect x="52" y="58" width="14" height="12" rx="2" fill="rgba(13, 148, 136, 0.2)" />
        <rect x="72" y="58" width="14" height="12" rx="2" fill="rgba(13, 148, 136, 0.2)" />
        <rect x="32" y="76" width="14" height="12" rx="2" fill="rgba(13, 148, 136, 0.2)" />
        <rect x="52" y="76" width="14" height="12" rx="2" fill="rgba(13, 148, 136, 0.45)" />
      </svg>
    );
  }

  if (preset === 'people') {
    return (
      <svg {...common}>
        <circle cx="44" cy="46" r="16" fill="rgba(13, 148, 136, 0.25)" stroke="#0d9488" strokeWidth="2" />
        <circle cx="78" cy="42" r="14" fill="rgba(14, 165, 233, 0.2)" stroke="#0284c7" strokeWidth="2" />
        <path d="M24 92c4-16 18-24 34-24s30 8 34 24" fill="none" stroke="var(--color-border-strong, #cbd5e1)" strokeWidth="2" strokeLinecap="round" />
        <path d="M58 88c10-4 22-2 30 8" fill="none" stroke="var(--color-border-strong, #cbd5e1)" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }

  if (preset === 'messages') {
    return (
      <svg {...common}>
        <rect x="18" y="30" width="84" height="56" rx="12" fill="var(--color-surface, #fff)" stroke="var(--color-border, #e2e8f0)" strokeWidth="2" />
        <path d="M38 86 L48 70 H88" fill="none" stroke="var(--color-border, #e2e8f0)" strokeWidth="2" />
        <rect x="32" y="46" width="40" height="6" rx="3" fill="rgba(13, 148, 136, 0.35)" />
        <rect x="32" y="58" width="56" height="6" rx="3" fill="rgba(148, 163, 184, 0.45)" />
      </svg>
    );
  }

  /* clipboard / default */
  return (
    <svg {...common}>
      <rect x="34" y="22" width="52" height="72" rx="8" fill="var(--color-surface, #fff)" stroke="var(--color-border, #e2e8f0)" strokeWidth="2" />
      <rect x="42" y="14" width="36" height="14" rx="4" fill="#0d9488" opacity="0.9" />
      <rect x="44" y="40" width="32" height="4" rx="2" fill="rgba(148, 163, 184, 0.55)" />
      <rect x="44" y="52" width="24" height="4" rx="2" fill="rgba(148, 163, 184, 0.4)" />
      <rect x="44" y="64" width="28" height="4" rx="2" fill="rgba(148, 163, 184, 0.4)" />
    </svg>
  );
}

/**
 * @param {object} props
 * @param {string} [props.icon] Optional emoji / short symbol (legacy)
 * @param {'clipboard'|'calendar'|'people'|'messages'|'video'} [props.preset]
 */
export default function EmptyState({ title, description, actionLabel, onAction, icon, preset = 'clipboard' }) {
  const graphic =
    typeof icon === 'string' && icon.trim() !== '' ? (
      <span className="empty-state-icon empty-state-icon--emoji" aria-hidden>
        {icon}
      </span>
    ) : (
      <span className="empty-state-icon-wrap" aria-hidden>
        <Illustration preset={preset} />
      </span>
    );

  return (
    <div className="empty-state animate-reveal" role="status">
      {graphic}
      <h3 className="empty-state-title">{title}</h3>
      {description && <p className="empty-state-desc">{description}</p>}
      {actionLabel && onAction && (
        <button type="button" className="btn btn-primary empty-state-action" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
