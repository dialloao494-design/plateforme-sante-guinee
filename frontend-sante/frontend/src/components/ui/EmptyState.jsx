import './EmptyState.css';

export default function EmptyState({ title, description, actionLabel, onAction, icon = '📋' }) {
  return (
    <div className="empty-state" role="status">
      <span className="empty-state-icon" aria-hidden>
        {icon}
      </span>
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
