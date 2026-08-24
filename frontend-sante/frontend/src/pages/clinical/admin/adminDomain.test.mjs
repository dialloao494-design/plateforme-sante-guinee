import test from 'node:test';
import assert from 'node:assert/strict';
import { ROLE_LABELS, buildAttentionItems } from './adminDomain.js';

test('admin handoff lists incomplete readiness work before billing work', () => {
  const items = buildAttentionItems({ checklist: [
    { key: 'offline', label: 'Poste hors ligne vérifié', detail: 'Test requis', target: 'verification', complete: false },
    { key: 'printing', label: 'Impression', detail: 'OK', target: 'verification', complete: true },
  ] }, { pendingCharges: 3 });
  assert.deepEqual(items.map((item) => item.key), ['offline', 'unpaid']);
  assert.match(items[1].label, /3 facture/);
});

test('clinical roles use human-readable French labels', () => {
  assert.equal(ROLE_LABELS.lab_technician, 'Laborantin');
  assert.equal(ROLE_LABELS.nurse, 'Infirmier(ère)');
});
