export default function ClinicalStatGrid({ stats }) {
  if (!stats?.length) return null;
  return (
    <div className="clinical-stat-grid">
      {stats.map((stat) => (
        <div key={stat.label} className={`clinical-stat-card${stat.variant ? ` clinical-stat-card--${stat.variant}` : ''}`}>
          <span className="clinical-stat-label">{stat.label}</span>
          <strong className="clinical-stat-value">{stat.value}</strong>
          {stat.hint && <span className="clinical-stat-hint">{stat.hint}</span>}
        </div>
      ))}
    </div>
  );
}
