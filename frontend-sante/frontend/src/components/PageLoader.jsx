export default function PageLoader({ label = 'Chargement…' }) {
  return (
    <div className="app-loading" role="status" aria-live="polite">
      <div className="app-loading-inner">
        <span className="app-spinner" aria-hidden />
        <span>{label}</span>
      </div>
    </div>
  );
}
