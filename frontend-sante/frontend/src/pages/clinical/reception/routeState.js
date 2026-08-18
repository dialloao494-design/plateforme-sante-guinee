import { TABS } from './constants.js';

const VALID_TABS = new Set(TABS.map(({ id }) => id));

export function readReceptionRouteState(searchParams) {
  const requestedTab = searchParams.get('tab');
  return {
    tab: VALID_TABS.has(requestedTab) ? requestedTab : 'dashboard',
    patientId: searchParams.get('patient') || '',
  };
}

export function updateReceptionRouteState(searchParams, patch) {
  const next = new URLSearchParams(searchParams);
  if (patch.tab !== undefined) {
    if (patch.tab === 'dashboard') next.delete('tab');
    else if (VALID_TABS.has(patch.tab)) next.set('tab', patch.tab);
  }
  if (patch.patientId !== undefined) {
    if (patch.patientId) next.set('patient', String(patch.patientId));
    else next.delete('patient');
  }
  return next;
}
