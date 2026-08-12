/** Map API paths to sync entity types (mirrors clinic-node outbox conventions). */

const RULES = [
  // HIS registration requires a real server-issued dossier number — never queue offline.
  {
    pattern: /\/clinical\/reception\/his\/patients\/?$/,
    entityType: 'patient',
    domain: 'patients',
    queueable: false,
  },
  { pattern: /\/clinical\/(reception\/his\/)?patients\/search|\/clinical\/reception\/patients|\/clinical\/(doctor|nurse|pharmacy|lab|billing\/unified)\/patients\/search/, entityType: 'patient', domain: 'patients' },
  { pattern: /\/clinical\/consultations/, entityType: 'consultation', domain: 'consultations' },
  { pattern: /\/clinical\/(reception\/his\/)?invoices|\/clinical\/billing\//, entityType: 'billing', domain: 'billing' },
  { pattern: /\/clinical\/pharmacy\//, entityType: 'pharmacy', domain: 'pharmacy' },
  { pattern: /\/clinical\/lab\//, entityType: 'lab', domain: 'lab' },
  { pattern: /\/clinical\/doctor\/catalog|\/clinical\/lab\/catalog|\/clinical\/reception\/his\/billing-catalog/, entityType: 'catalog', domain: 'catalogs' },
];

/** True for mutations that must reach the server immediately (no outbox). */
export function isOnlineOnlyMutation(url = '', method = 'get') {
  const verb = String(method).toLowerCase();
  if (!['post', 'patch', 'put', 'delete'].includes(verb)) return false;
  return /\/clinical\/reception\/his\/patients\/?$/.test(String(url).split('?')[0]);
}

export function classifyRequest(url = '', method = 'get') {
  const path = String(url).split('?')[0];
  const verb = String(method).toLowerCase();
  const isMutation = ['post', 'patch', 'put', 'delete'].includes(verb);

  for (const rule of RULES) {
    if (rule.pattern.test(path)) {
      const queueable =
        rule.queueable === false ? false : isMutation && rule.queueable !== false;
      return {
        entityType: rule.entityType,
        domain: rule.domain,
        operation: verbToOperation(verb),
        cacheable: verb === 'get',
        queueable,
      };
    }
  }

  return {
    entityType: 'unknown',
    domain: null,
    operation: verbToOperation(verb),
    cacheable: verb === 'get' && /\/clinical\//.test(path),
    queueable: isMutation && /\/clinical\//.test(path) && !isOnlineOnlyMutation(path, verb),
  };
}

function verbToOperation(verb) {
  switch (verb) {
    case 'post':
      return 'create';
    case 'patch':
    case 'put':
      return 'update';
    case 'delete':
      return 'delete';
    default:
      return 'read';
  }
}

export function isPatientSearchUrl(url = '') {
  return /\/patients(\/search)?(\?|$)/.test(String(url)) || /\/patients\/search/.test(String(url));
}

export function isCatalogUrl(url = '') {
  return /\/catalog/.test(String(url)) || /billing-catalog/.test(String(url));
}
