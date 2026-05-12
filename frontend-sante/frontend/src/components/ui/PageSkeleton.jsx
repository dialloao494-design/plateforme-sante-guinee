import './PageSkeleton.css';

export default function PageSkeleton({ lines = 4 }) {
  return (
    <div className="page-skeleton" aria-busy="true" aria-label="Chargement">
      <div className="page-skeleton-block page-skeleton-block--hero" />
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="page-skeleton-line" style={{ width: `${68 + (i % 3) * 8}%` }} />
      ))}
    </div>
  );
}
