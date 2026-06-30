export default function ClinicalStatGrid({ stats, onStatClick, activeKey }) {
  if (!stats?.length) return null;
  return (
    <div className="clinical-stat-grid">
      {stats.map((stat) => {
        const isActive = Boolean(activeKey && stat.key && stat.key === activeKey);
        const className = [
          'clinical-stat-card',
          stat.variant ? `clinical-stat-card--${stat.variant}` : '',
          onStatClick && stat.key ? 'clinical-stat-card--clickable' : '',
          isActive ? 'clinical-stat-card--active' : '',
        ]
          .filter(Boolean)
          .join(' ');

        const content = (
          <>
            <span className="clinical-stat-label">{stat.label}</span>
            <strong className="clinical-stat-value">{stat.value}</strong>
            {stat.hint && <span className="clinical-stat-hint">{stat.hint}</span>}
          </>
        );

        if (onStatClick && stat.key) {
          return (
            <button
              key={stat.key}
              type="button"
              className={className}
              onClick={() => onStatClick(stat.key)}
              aria-pressed={isActive}
            >
              {content}
            </button>
          );
        }

        return (
          <div key={stat.label} className={className}>
            {content}
          </div>
        );
      })}
    </div>
  );
}
