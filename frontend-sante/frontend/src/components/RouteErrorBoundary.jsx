import React from 'react';

export default class RouteErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('[RouteErrorBoundary]', error, info?.componentStack);
  }

  handleRetry = () => {
    this.setState({ error: null });
    window.location.assign(this.props.fallbackPath || '/login');
  };

  render() {
    const { error } = this.state;
    if (!error) {
      return this.props.children;
    }

    return (
      <div className="app-loading" role="alert">
        <div className="login-card login-card--narrow" style={{ margin: '2rem auto', maxWidth: '28rem' }}>
          <p className="login-eyebrow">Plateforme Santé · Guinée</p>
          <h1 className="login-title">Erreur d&apos;affichage</h1>
          <p className="login-lead">
            La page n&apos;a pas pu se charger. Votre session peut être valide — réessayez ou reconnectez-vous.
          </p>
          {error?.message && (
            <pre className="login-error" style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
              {String(error.message)}
            </pre>
          )}
          {import.meta.env.DEV && error?.stack && (
            <pre className="login-error" style={{ whiteSpace: 'pre-wrap', fontSize: '0.75rem' }}>
              {error.stack}
            </pre>
          )}
          <button type="button" className="btn btn-primary login-submit" onClick={this.handleRetry}>
            Retour à la connexion
          </button>
        </div>
      </div>
    );
  }
}
