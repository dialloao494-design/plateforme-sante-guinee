import assert from 'node:assert/strict';
import test from 'node:test';

import { calculateBmi, nursingCompletion, vitalAlerts } from './nurseDomain.js';

test('calculates BMI and ignores incomplete measurements', () => {
  assert.equal(calculateBmi(60, 165), '22.0');
  assert.equal(calculateBmi('', 165), '');
});

test('flags clinically important observations without diagnosing', () => {
  assert.deepEqual(vitalAlerts({
    temperature_c: '39.2', bp_systolic: '85', oxygen_saturation: '89',
    heart_rate: '130', respiratory_rate: '28', pain_score: '8',
  }), [
    'Température critique', 'Tension systolique critique', 'Saturation basse',
    'Pouls anormal', 'Fréquence respiratoire anormale', 'Douleur sévère',
  ]);
});

test('workflow completion reflects the three nursing stages', () => {
  assert.deepEqual(nursingCompletion({
    temperature_c: 37, bp_systolic: 120, bp_diastolic: 80, heart_rate: 70,
    respiratory_rate: 16, reason_for_consultation: 'Douleur', nurse_notes: 'Stable',
  }), { vitalsComplete: true, contextComplete: true, continuityComplete: true });
});
