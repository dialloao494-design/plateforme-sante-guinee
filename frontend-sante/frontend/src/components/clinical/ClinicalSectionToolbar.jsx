function formatUpdatedAt(value) {
  if (!value) return 'Mise à jour non disponible';
  return `Mis à jour à ${new Intl.DateTimeFormat('fr-GN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))}`;
}

export default function ClinicalSectionToolbar({
  title,
  description,
  updatedAt,
  onRefresh,
  refreshing = false,
  children,
}) {
  return (
    <header className="clinical-section-toolbar">
      <div className="clinical-section-toolbar__copy">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      <div className="clinical-section-toolbar__controls">
        {updatedAt !== undefined ? (
          <span className="clinical-section-toolbar__timestamp">{formatUpdatedAt(updatedAt)}</span>
        ) : null}
        {children}
        {onRefresh ? (
          <button
            type="button"
            className="clinical-btn clinical-btn--secondary"
            onClick={onRefresh}
            disabled={refreshing}
          >
            {refreshing ? 'Actualisation…' : 'Actualiser les données'}
          </button>
        ) : null}
      </div>
    </header>
  );
}
