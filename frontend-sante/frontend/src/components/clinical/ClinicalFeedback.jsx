export default function ClinicalFeedback({ error, message }) {
  if (!error && !message) return null;
  return (
    <div className="clinical-feedback" aria-live="polite" aria-atomic="true">
      {error && (
        <p className="clinical-error" role="alert">
          {String(error)}
        </p>
      )}
      {message && (
        <p className="clinical-success" role="status">
          {message}
        </p>
      )}
    </div>
  );
}
