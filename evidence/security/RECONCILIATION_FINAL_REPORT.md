# Santé Guinée — Git Reconciliation & Production Deployment Recovery Report

**Canonical production commit (main):** see section 14 (updated at end of recovery).  
**Branch:** `cursor/git-reconciliation-deploy-ab76` (also pushed directly to `main`)  
**Frontend:** https://plateforme-sante-guinee.vercel.app  
**Backend:** https://web-production-ad6a36.up.railway.app  

---

## 1. Git audit summary

| Area | Finding |
|---|---|
| `origin/main` before recovery | `a3dd731` — production hardening + empty-DB Alembic bootstrap; **missing** Offline V1 + Security Waves 0–7 + Red Team |
| Cursor / draft PRs #12–#25 | Contained Offline V1, Waves 0–7, Red Team; many `CONFLICTING` vs post-hardening `main` |
| Divergence | Red Team tip `49a26d1` and `main` `a3dd731` diverged from merge-base `d52d4ff` |
| Alembic collision | Both trees had `…_0023_*` with same `down_revision` — rechained Wave0 as `20260730_0024` |
| Local workspace | Reconciliation branch created; merges completed; secrets scrubbed from working tree |

**Inventory (after merge to main):**

| Status | Items |
|---|---|
| **Present in main** | Offline V1 `deploy/clinic-node/`, `evidence/clinic-node/`, Security Waves 0–7 evidence, Red Team report, `core/*_security.py`, Wave0 identity migration `0024`, hardened `0023` demote, JWT/session, doctor ownership, fail-closed boot, pyotp |
| **Present only in other branches (pre-merge)** | All of the above were only on Cursor branches / draft PRs #12–#25 |
| **Present only in open PRs** | Draft PRs #12–#25 remain open historically; content now on `main` via reconciliation commits |
| **Missing from GitHub (resolved)** | None of the approved Offline/Security/Red Team packages remain local-only |
| **Superseded** | Per-wave draft PR stacks superseded by reconciliation merge on `main` |
| **Unsafe to merge (handled)** | Conflicting Alembic 0023 IDs — resolved by rechain + demote-before-index |
| **Requires manual review** | Railway dashboard logs; live env var values; branch protection apply |

---

## 2. Missing work discovered

Before reconciliation, **main lacked**:

- Entire Clinic Node Offline V1 package (compose, installer, sync/backup/update, migrate tools, E2E evidence)
- Security Waves 0–7 implementations + evidence packs
- Final Red Team remediations + `FINAL_RED_TEAM_SECURITY_REPORT.md`
- `pyotp` dependency (MFA import) — would crash any deploy that included Wave 0 without it

---

## 3. Branches and PRs reconciled

| Branch / PR | Action |
|---|---|
| `cursor/offline-v1-production-go-ab76` (#14) | Merged into reconciliation |
| `cursor/red-team-final-assessment-ab76` (#25) + Waves 0–7 (#15–#24) | Merged into reconciliation |
| `cursor/git-reconciliation-deploy-ab76` | Working branch; pushed to `main` |
| Historical merged #4–#11 | Already on main ancestry — preserved |
| Draft PRs #12–#25 | Content landed on main; PRs can be closed manually as superseded |

---

## 4. Commits merged into main

Key tips pushed to `main` during recovery (newest last):

1. Merge Offline V1 + conflict resolution  
2. Merge Security Waves + Red Team; harden owner migration  
3. Test/fixture session_version fixes + entrypoint model imports + evidence  
4. Add `pyotp==2.9.0`  
5. Railway private-mesh TLS + attachment key derivation  
6. Simplify Dockerfile (remove fragile pgdg mirror)

Exact SHA: **see §14**.

---

## 5. Secret scan results

- Working tree: no live production secrets committed; `.env` examples only  
- Prior AASMA/pilot credentials scrubbed in Red Team work  
- Hits limited to docs placeholders, Fernet examples, openssl generators, pentest search strings  
- **Residual risk:** secrets may still exist in **git history** → **rotate** JWT/DB/reminder/WhatsApp/attachment keys in Railway/Vercel if ever exposed historically  
- **Never committed:** real Railway/Vercel tokens (also absent from Actions secrets)

---

## 6. Railway failure root cause

**Evidence:** GitHub Actions run `30506994598` on `main` @ `a3dd731`:

- `RAILWAY_TOKEN` / `RAILWAY_SERVICE_ID` **empty** → CLI deploy skipped  
- Health wait: HTTP **502** `"Application failed to respond"` for **600s**

**Prior “success”** run `30506642414` on `e3108b4` reported ready in **~2s** → treated as **stale healthy process**, not proof the new revision booted.

**Root causes (layered):**

1. **Primary (e3108b4):** Alembic `20260730_0023` created unique `platform_owner` index **without demoting duplicates** + fail-closed startup → crash → 502  
2. **Secondary (security merge):** missing **`pyotp`** → `ModuleNotFoundError` on `import main` (confirmed in CI e2e/backend logs)  
3. **Secondary:** Wave 3 boot guards requiring **`ATTACHMENT_ENCRYPTION_KEY`** and **public `sslmode=require`** against typical Railway **private** `*.railway.internal` URLs  
4. **Secondary:** Dockerfile pulling **apt.postgresql.org** (build fragility)  
5. **Operational:** no Railway CLI token → cannot force redeploy or read Railway build/runtime logs from this agent  

---

## 7. Fixes implemented

| Fix | File(s) |
|---|---|
| Demote duplicate platform owners before unique index | `alembic/versions/20260730_0023_…`, `database_migrations.py` |
| Rechain Wave0 identity as `0024` | `alembic/versions/20260730_0024_…` |
| Add `pyotp` | `requirements.txt` |
| Railway private-mesh TLS exemption; don’t force SSL on internal host | `core/deploy_hardening.py` |
| Derive Fernet attachment key from strong JWT/SECRET when unset (encryption still on; bypass still needs attestation) | `core/settings.py` |
| Simplify Dockerfile / soft gosu | `Dockerfile`, `scripts/docker/entrypoint-backend.sh` |
| Session_version test pollution fix | `tests/conftest.py`, Wave0 + visit workflow tests |
| Env checklist (no secret values) | `deploy/railway-vercel.env.template` |
| Merge Offline V1 + Security + Red Team onto main | reconciliation commits |

**Tests:** `302 passed, 1 skipped` (local full suite).

---

## 8. Environment variables verified (checklist — values not exposed)

| Variable | Where | Status |
|---|---|---|
| `DATABASE_URL` | Railway | Assumed present (was healthy pre-`e3108b4`); private mesh OK without `sslmode` |
| `SECRET_KEY` / `JWT_SECRET` | Railway | Required ≥32; used for attachment key derivation if needed |
| `REMINDER_RESPOND_TOKEN` | Railway | Required in production |
| `JITSI_SECRET` / `JITSI_APP_SECRET` | Railway | Required for cloud |
| `ATTACHMENT_ENCRYPTION_KEY` | Railway | **Recommended explicit**; auto-derived from JWT if missing |
| `FRONTEND_URL` / `CORS_ORIGINS` | Railway | Canonical Vercel URL |
| `ENVIRONMENT=production` | Railway | Expected |
| `RAILWAY_TOKEN` + `RAILWAY_SERVICE_ID` | **GitHub Actions secrets** | **MISSING** — blocks CLI deploy + log access |
| `VERCEL_TOKEN` + org/project | **GitHub Actions secrets** | **MISSING** — relies on Vercel GitHub auto-deploy |
| Emergency bypass attestation | Railway | Must **not** be set |

---

## 9. Railway deployment result

| Check | Result |
|---|---|
| Code fixes on `main` | Yes |
| Actions “Deploy Railway + Vercel” | Still **fails wait** (502 for 600s) while `RAILWAY_TOKEN` empty |
| Live `GET /health` | **Still 502** as of last probe after Dockerfile push |
| Agent can redeploy / read Railway logs | **No** — no token |

**Conclusion:** Repository-side blockers identified and fixed on `main`. **Live Railway recovery is blocked on operational access** (dashboard Redeploy + confirm build logs / env). Until Railway successfully builds & starts commit in §14, production API remains down.

---

## 10. Vercel deployment result

| Check | Result |
|---|---|
| Canonical URL | https://plateforme-sante-guinee.vercel.app → **HTTP 200** |
| Legacy `frontend-seven-rust-94` | Not used by recovery |
| Actions Vercel CLI | Skipped (no token); relies on GitHub auto-deploy |
| Frontend ↔ backend | Frontend up; API still 502 → clinical flows cannot succeed end-to-end |

---

## 11. Production verification results

| Check | Result |
|---|---|
| Frontend loads | **Pass** (200) |
| Backend `/health` / `/health/ready` | **Fail** (502) |
| Auth / clinical / billing / RBAC / PDFs / uploads | **Not runnable** while API down |
| Security headers / console | Deferred until API healthy |
| Production data integrity | No destructive migrations executed against live DB from this agent |
| Clinic Node not deployed as cloud service | **Honored** — package only in GitHub for mini-PC |

---

## 12. Remaining manual actions

1. **Railway dashboard** → backend service → **View logs** for the latest deploy of SHA in §14; confirm build success and startup lines (`Alembic upgrade`, no `SystemExit`).  
2. If no new deploy appeared: **Settings → connect GitHub** / **Redeploy** latest `main`.  
3. Set **explicit** `ATTACHMENT_ENCRYPTION_KEY` (Fernet) for independent rotation (optional once derived key works).  
4. Add GitHub Actions secrets: `RAILWAY_TOKEN`, `RAILWAY_SERVICE_ID`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` per `docs/GITHUB_DEPLOY_SECRETS.md`.  
5. Close superseded draft PRs #12–#25 after confirming main content.  
6. Rotate any historically exposed credentials.  
7. Re-run production smoke (auth + clinical paths) after `/health/ready` returns 200.  
8. Apply branch protection (§13) **after** recovery is confirmed healthy.

---

## 13. Branch-protection recommendation

**Do not enable blocking rules until Railway is healthy** (would hinder emergency hotfixes without review bypass).

Recommended (apply later):

| Rule | Setting |
|---|---|
| Force pushes | Deny on `main` |
| Branch deletion | Deny on `main` |
| Require PR | Yes (1 reviewer) once ops staffed |
| Required checks | `backend-tests`, `frontend-build`, `secrets-guard` (make e2e non-blocking until stable) |
| Admin enforcement | Include administrators |
| Linear history | Optional |
| Emergency recovery | Repo admin temporary bypass or break-glass admin; document in runbook; re-enable after |

Current agent cannot read/write protection API (`403`).

---

## 14. Exact production commit SHA

```
40a163ec0dc89f581170a67d398eb5356646f3ef
```

This is `origin/main` after Offline V1 + Security/Red Team reconciliation, Railway boot fixes, `pyotp`, simplified Dockerfile, and this report.

**Clinic Node:** available under `deploy/clinic-node/` on that commit for mini-PC install — **not** a Railway/Vercel service.

---

## Honesty statement

Success is **not** claimed for live Railway. Git reconciliation + code deploy blockers are fixed on `main` with test evidence. **Railway remains 502** without dashboard/token access to complete redeploy verification. Frontend canonical URL is up.
