/**
 * Breadcrumbs for the authenticated app chrome (no duplicate visible page titles).
 */
function c(to, label) {
  return { to, label };
}

export function getShellContext(pathname, role) {
  const r = String(role || '').toLowerCase();
  const isDoctorLike = r === 'doctor' || r === 'admin';
  const homeTo = isDoctorLike ? '/doctor/dashboard' : '/dashboard';
  const homeLabel = isDoctorLike ? 'Praticien' : 'Accueil';

  const withHome = (rest) => [c(homeTo, homeLabel), ...rest];

  if (pathname.startsWith('/consultation/')) {
    return {
      crumbs: withHome([c('/teleconsultation', 'Téléconsultation'), { label: 'Salle', to: null }]),
    };
  }
  if (pathname === '/teleconsultation') {
    return { crumbs: withHome([{ label: 'Téléconsultation', to: null }]) };
  }
  if (pathname === '/notifications') {
    return { crumbs: withHome([{ label: 'Notifications', to: null }]) };
  }
  if (pathname.startsWith('/doctor/patient/')) {
    return {
      crumbs: withHome([
        c(isDoctorLike ? '/doctor/appointments' : '/patients', isDoctorLike ? 'File d’attente' : 'Patients'),
        { label: 'Dossier patient', to: null },
      ]),
    };
  }
  if (pathname === '/doctor/dashboard') {
    return { crumbs: withHome([{ label: 'Agenda clinique', to: null }]) };
  }
  if (pathname === '/doctor/appointments') {
    return { crumbs: withHome([{ label: 'File d’attente', to: null }]) };
  }
  if (pathname === '/doctor/messages') {
    return { crumbs: withHome([{ label: 'Messagerie', to: null }]) };
  }
  if (pathname === '/patients') {
    return { crumbs: withHome([{ label: 'Patients', to: null }]) };
  }
  if (pathname.startsWith('/messages/')) {
    return { crumbs: withHome([{ label: 'Conversation', to: null }]) };
  }
  if (pathname === '/appointments') {
    return { crumbs: withHome([{ label: 'Rendez-vous', to: null }]) };
  }
  if (pathname.startsWith('/doctors/') && pathname !== '/doctors') {
    return { crumbs: withHome([c('/doctors', isDoctorLike ? 'Annuaire' : 'Médecins'), { label: 'Fiche praticien', to: null }]) };
  }
  if (pathname === '/doctors') {
    return {
      crumbs: withHome([{ label: isDoctorLike ? 'Annuaire' : 'Médecins', to: null }]),
    };
  }
  if (pathname === '/users') {
    return { crumbs: withHome([{ label: 'Utilisateurs', to: null }]) };
  }
  if (pathname === '/dashboard') {
    return { crumbs: [{ label: 'Tableau de bord', to: null }] };
  }

  return { crumbs: [{ label: 'Plateforme Santé', to: null }] };
}
