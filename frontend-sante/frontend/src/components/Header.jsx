import './Header.css';

const Header = ({ user, onMenuClick, onLogout }) => {
  return (
    <header className="header">
      <div className="header-content">
        <button className="menu-btn" onClick={onMenuClick}>
          <span></span>
          <span></span>
          <span></span>
        </button>
        <h1 className="header-title">Plateforme Santé</h1>
        <div className="header-actions">
          <span className="user-name">{user?.name}</span>
          <button className="btn btn-outline" onClick={onLogout}>
            Déconnexion
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;