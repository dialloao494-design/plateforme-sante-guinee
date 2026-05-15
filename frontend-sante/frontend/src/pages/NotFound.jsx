import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getRoleHomePath } from '../utils/rolePaths.js';

export default function NotFound() {
  const { user } = useAuth();
  const home = user ? getRoleHomePath(user.role) : '/';

  return (
    <div className="ds-page" style={{ padding: '2rem', textAlign: 'center' }}>
      <h1>Page introuvable</h1>
      <p>Cette adresse n&apos;existe pas ou a été déplacée.</p>
      <Link to={home} className="btn btn-primary">
        Retour à l&apos;accueil
      </Link>
    </div>
  );
}
