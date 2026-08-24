import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { authAPI } from '../services/api.js';
import './Login.css';

export default function ActivateStaff() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = useMemo(() => params.get('token') || '', [params]);
  const [invitation, setInvitation] = useState(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) { setError("Le lien d'invitation est incomplet."); setLoading(false); return; }
    authAPI.inspectStaffActivation(token)
      .then(({ data }) => setInvitation(data))
      .catch((err) => setError(err?.response?.data?.detail || "Cette invitation n'est plus valide."))
      .finally(() => setLoading(false));
  }, [token]);

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    if (password !== confirm) { setError('La confirmation ne correspond pas.'); return; }
    setLoading(true);
    try {
      await authAPI.completeStaffActivation(token, password);
      navigate('/login', { replace: true, state: { activationSuccess: true } });
    } catch (err) {
      setError(err?.response?.data?.detail || "L'activation a échoué.");
      setLoading(false);
    }
  };

  return <div className="login-page">
    <div className="login-card login-card--narrow">
      <p className="login-eyebrow">Accès sécurisé du personnel</p>
      <h1 className="login-title">Activer mon compte</h1>
      {loading && !invitation ? <p className="login-lead">Vérification de l’invitation…</p> : null}
      {invitation ? <>
        <p className="login-lead">{invitation.first_name ? `Bienvenue ${invitation.first_name}. ` : ''}{invitation.clinic_name} vous a invité à rejoindre son équipe.</p>
        <p className="login-help">Compte : <strong>{invitation.email_masked}</strong>. Ce lien personnel ne fonctionnera qu’une fois.</p>
        <form className="login-form" onSubmit={submit}>
          <div className="login-field"><label htmlFor="activation-password">Choisir mon mot de passe</label><input id="activation-password" type="password" minLength="8" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required disabled={loading} /></div>
          <div className="login-field"><label htmlFor="activation-confirm">Confirmer le mot de passe</label><input id="activation-confirm" type="password" minLength="8" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required disabled={loading} /></div>
          {error ? <p className="login-error" role="alert">{error}</p> : null}
          <button className="btn btn-primary login-submit" type="submit" disabled={loading}>{loading ? 'Activation…' : 'Activer et continuer'}</button>
        </form>
      </> : null}
      {!invitation && error ? <p className="login-error" role="alert">{error}</p> : null}
      <p className="login-footer-text"><Link to="/login">Retour à la connexion</Link></p>
    </div>
  </div>;
}
