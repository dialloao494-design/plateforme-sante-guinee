/**
 * Breadcrumbs for the authenticated app chrome (no duplicate visible page titles).
 */
import { getRoleHomePath } from './rolePaths.js';
import { isClinicPortalRole } from './portalAccess.js';

function c(to, label) {
  return { to, label };
}

const CLINICAL_CRUMBS = {
  '/clinical': 'Opérations',
  '/clinical/reception': 'Réception',
  '/clinical/cashier': 'Caisse',
  '/clinical/doctor': 'Consultations',
  '/clinical/lab': 'Laboratoire',
  '/clinical/pharmacy': 'Pharmacie',
  '/clinical/admin': 'Administration',
  '/clinical/revenue': 'Recettes',
};

export function getShellContext(pathname, role) {
  const r = String(role || '').toLowerCase();
  const homeTo = isClinicPortalRole(r) ? getRoleHomePath(r) : '/dashboard';
  const homeLabel = isClinicPortalRole(r) ? 'Clinique' : 'Accueil';

  const withHome = (rest) => [c(homeTo, homeLabel), ...rest];

  for (const [prefix, label] of Object.entries(CLINICAL_CRUMBS)) {
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
      return { crumbs: withHome([{ label, to: null }]) };
    }
  }

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
        c('/clinical/doctor', 'Consultations'),
        { label: 'Dossier patient', to: null },
      ]),
    };
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
    return {
      crumbs: withHome([c('/doctors', 'Médecins'), { label: 'Fiche praticien', to: null }]),
    };
  }
  if (pathname === '/doctors') {
    return { crumbs: withHome([{ label: 'Médecins', to: null }]) };
  }
  if (pathname === '/users') {
    return { crumbs: withHome([{ label: 'Utilisateurs', to: null }]) };
  }
  if (pathname === '/account/profile') {
    return { crumbs: withHome([{ label: 'Mon profil', to: null }]) };
  }
  if (pathname === '/account/password') {
    return { crumbs: withHome([c('/account/profile', 'Mon profil'), { label: 'Mot de passe', to: null }]) };
  }
  if (pathname === '/dashboard') {
    return { crumbs: [{ label: 'Tableau de bord', to: null }] };
  }
  if (pathname === '/platform' || pathname.startsWith('/platform/')) {
    if (/^\/platform\/clinics\/\d+/.test(pathname)) {
      return {
        crumbs: [
          c('/platform', 'Plateforme'),
          c('/platform/clinics', 'Cliniques'),
          { label: 'Détail clinique', to: null },
        ],
      };
    }
    if (pathname === '/platform/accounts') {
      return {
        crumbs: [
          c('/platform', 'Plateforme'),
          { label: 'Comptes techniques', to: null },
        ],
      };
    }
    const label =
      pathname === '/platform/clinics' || pathname.startsWith('/platform/clinics')
        ? 'Cliniques'
        : 'Console';
    return { crumbs: [c('/platform', 'Plateforme'), { label, to: null }] };
  }

  return { crumbs: [{ label: 'Plateforme Santé', to: null }] };
}
