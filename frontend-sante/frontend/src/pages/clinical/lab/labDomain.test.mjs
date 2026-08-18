import assert from 'node:assert/strict';
import test from 'node:test';

import { parseLabPayload, sampleCodesFromLabels } from './labDomain.js';

test('parseLabPayload accepts stored JSON and rejects corrupted values', () => {
  assert.deepEqual(parseLabPayload('{"sample_types":["Sang"]}'), { sample_types: ['Sang'] });
  assert.deepEqual(parseLabPayload({ rows: [] }), { rows: [] });
  assert.equal(parseLabPayload('{corrupted'), null);
  assert.equal(parseLabPayload(''), null);
});

test('sampleCodesFromLabels maps known sample labels without inventing values', () => {
  assert.deepEqual(sampleCodesFromLabels(['Sang', 'Urine', 'Inconnu']), ['blood', 'urine']);
});
