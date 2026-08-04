/** Map API paths to sync entity types (mirrors clinic-node outbox conventions). */

const RULES = [
  { pattern: /\/clinical\/(reception\/his\/)?patients\/search|\/clinical\/reception\/patients|\/clinical\/(doctor|nurse|pharmacy|lab|billing\/unified)\/patients\/search/, entityType: 'patient', domain: 'patients' },
  { pattern: /\/clinical\/consultations/, entityType: 'consultation', domain: 'consultations' },
  { pattern: /\/clinical\/(reception\/his\/)?invoices|\/clinical\/billing\//, entityType: 'billing', domain: 'billing' },
  { pattern: /\/clinical\/pharmacy\//, entityType: 'pharmacy', domain: 'pharmacy' },
  { pattern: /\/clinical\/lab\//, entityType: 'lab', domain: 'lab' },
  { pattern: /\/clinical\/doctor\/catalog|\/clinical\/lab\/catalog|\/clinical\/reception\/his\/billing-catalog/, entityType: 'catalog', domain: 'catalogs' },
];

export function classifyRequest(url = '', method = 'get') {
  const path = String(url).split('?')[0];
  const verb = String(method).toLowerCase();

  for (const rule of RULES) {
    if (rule.pattern.test(path)) {
      return {
        entityType: rule.entityType,
        domain: rule.domain,
        operation: verbToOperation(verb),
        cacheable: verb === 'get',
        queueable: ['post', 'patch', 'put', 'delete'].includes(verb),
      };
    }
  }

  return {
    entityType: 'unknown',
    domain: null,
    operation: verbToOperation(verb),
    cacheable: verb === 'get' && /\/clinical\//.test(path),
    queueable: ['post', 'patch', 'put', 'delete'].includes(verb) && /\/clinical\//.test(path),
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
