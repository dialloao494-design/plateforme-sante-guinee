/** Role normalization and RBAC helpers for routes and navigation. */

const ALIASES = {
  admin: ['clinic_admin'],
  clinic_admin: ['admin'],
  doctor: ['medecin', 'médecin', 'physician', 'professional', 'praticien'],
  medecin: ['doctor'],
  médecin: ['doctor'],
  physician: ['doctor'],
  professional: ['doctor'],
  praticien: ['doctor'],
};

export function normalizeRole(role) {
  return String(role || '').toLowerCase();
}

export function expandAllowedRoles(allowedRoles = []) {
  const expanded = new Set();
  for (const role of allowedRoles) {
    const r = normalizeRole(role);
    expanded.add(r);
    for (const alias of ALIASES[r] || []) {
      expanded.add(alias);
    }
  }
  return expanded;
}

export function userHasRole(userRole, allowedRoles = []) {
  if (!allowedRoles.length) {
    return true;
  }
  const r = normalizeRole(userRole);
  const expanded = expandAllowedRoles(allowedRoles);
  if (expanded.has(r)) {
    return true;
  }
  // Platform owner inherits platform_admin route access.
  if (r === 'platform_owner' && expanded.has('platform_admin')) {
    return true;
  }
  return false;
}
