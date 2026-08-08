import test from 'node:test';
import assert from 'node:assert/strict';
import { buildInvoiceItemPayload } from './buildInvoiceItemPayload.js';

test('emergency specialty line keeps catalog_code and price_variant=emergency', () => {
  const payload = buildInvoiceItemPayload({
    charge_type: 'consultation',
    description: "Consultation d'urgences — Médecine",
    quantity: 1,
    unit_price_gnf: 150000,
    catalog_code: 'medicine',
    price_variant: 'emergency',
    source_type: 'reception',
  });
  assert.equal(payload.catalog_code, 'medicine');
  assert.equal(payload.price_variant, 'emergency');
  assert.equal(payload.description, "Consultation d'urgences — Médecine");
  // Server-authoritative: omit client price when catalog_code is set
  assert.equal(payload.unit_price_gnf, undefined);
});

test('specialized specialty line sends price_variant=specialized', () => {
  const payload = buildInvoiceItemPayload({
    charge_type: 'consultation',
    description: 'Consultation spécialisée — Médecine',
    quantity: 1,
    unit_price_gnf: 250000,
    catalog_code: 'medicine',
    price_variant: 'specialized',
  });
  assert.equal(payload.price_variant, 'specialized');
  assert.equal(payload.catalog_code, 'medicine');
});

test('ignores unknown price_variant values', () => {
  const payload = buildInvoiceItemPayload({
    catalog_code: 'medicine',
    price_variant: 'whatever',
    description: 'x',
    quantity: 1,
  });
  assert.equal(payload.price_variant, undefined);
});
