# Role E2E button matrix

Living matrix of clinic role dashboards, critical CTAs, and Playwright coverage.
Spec: `frontend-sante/frontend/e2e/role-button-matrix.spec.js`

Credentials default to CIS pilot seed (`ENABLE_PILOT_SEED=true` in Playwright webServer).
Override per role with `E2E_<ROLE>_EMAIL` / `E2E_<ROLE>_PASSWORD` (same pattern as reception).

| Role | Route | Critical buttons / navigation | E2E coverage |
|---|---|---|---|
| Réception | `/clinical/reception` | Tabs: Tableau de bord, Enregistrement, Admission, Facturation, Remboursement, Demandes | **Automated** — matrix + full tab walk |
| Caisse / Cashier | `/clinical/reception` | Facturation, Remboursement tabs | **Automated** |
| Médecin | `/clinical/doctor` | Recherche patient CTA | **Automated** |
| Laboratoire | `/clinical/lab` | Tableau de bord Labo | **Automated** |
| Pharmacie | `/clinical/pharmacy` | Dispensation, Stock tabs | **Automated** |
| Infirmier(ère) — Triage | `/clinical/nurse` | Recherche patient | **Automated** |
| Soins infirmiers | `/clinical/nursing-care` | Enregistrement tab | **Automated** |
| Facturation unifiée | `/clinical/billing` | Section « Générer une facture » | **Automated** (section visible; generate requires patient) |
| Hospitalisation | `/clinical/hospitalization` | Rechercher patient (admission) | **Automated** |
| Nutrition | `/clinical/nutrition` | Rechercher patient | **Automated** |
| PEV / Vaccination | `/clinical/pev` | Enregistrement tab | **Automated** |
| Administration | `/clinical/admin` | Nav « Créer un compte », personnel | **Automated** |

## `data-testid` hooks (minimal)

| Dashboard | test id |
|---|---|
| Réception | `reception-dashboard`, `reception-tab-*` |
| Médecin | `doctor-dashboard`, `doctor-patient-search-btn` |
| Laboratoire | `lab-dashboard` |
| Pharmacie | `pharmacy-dashboard`, `pharmacy-tab-*` |
| Infirmier | `nurse-dashboard` |
| Soins infirmiers | `nursing-care-dashboard`, `nursing-care-tab-record` |
| Facturation | `billing-dashboard`, `billing-generate-invoice` |
| Hospitalisation | `hospitalization-dashboard` |
| Nutrition | `nutrition-dashboard` |
| PEV | `pev-dashboard`, `pev-tab-*` |
| Admin | `admin-dashboard` |

## npm scripts

- `npm run test:e2e:matrix` — role button matrix only
- `npm run test:e2e` — full Playwright suite (includes matrix + offline)
