import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';

const KiB = 1024;
const assetsDir = path.resolve('dist/assets');

const budgets = [
  { label: 'largest JavaScript asset', pattern: /\.js$/, maxKiB: 230 },
  { label: 'clinical stylesheet', pattern: /^clinical-.*\.css$/, maxKiB: 65 },
  { label: 'reception route', pattern: /^ReceptionDashboard-.*\.js$/, maxKiB: 115 },
  { label: 'doctor clinical route', pattern: /^DoctorClinicalDashboard-.*\.js$/, maxKiB: 50 },
  { label: 'laboratory route', pattern: /^LabDashboard-.*\.js$/, maxKiB: 40 },
  { label: 'pharmacy route', pattern: /^PharmacyDashboard-.*\.js$/, maxKiB: 32 },
];

const names = await readdir(assetsDir);
const assets = await Promise.all(names.map(async (name) => ({
  name,
  bytes: (await stat(path.join(assetsDir, name))).size,
})));

const failures = [];
for (const budget of budgets) {
  const matches = assets.filter((asset) => budget.pattern.test(asset.name));
  if (matches.length === 0) {
    failures.push(`${budget.label}: expected asset not found (${budget.pattern})`);
    continue;
  }
  const largest = matches.reduce((current, asset) => asset.bytes > current.bytes ? asset : current);
  const actualKiB = largest.bytes / KiB;
  const result = `${budget.label}: ${actualKiB.toFixed(2)} KiB / ${budget.maxKiB} KiB (${largest.name})`;
  if (actualKiB > budget.maxKiB) failures.push(result);
  else console.log(`PASS ${result}`);
}

if (failures.length > 0) {
  console.error(`Performance budget failed:\n${failures.map((failure) => `- ${failure}`).join('\n')}`);
  process.exitCode = 1;
}
