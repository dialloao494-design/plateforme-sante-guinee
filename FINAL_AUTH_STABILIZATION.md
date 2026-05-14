# Final authentication & database stabilization (pilot)

This document is the **single reference** for demo credentials, reset workflow, and auth behavior after the stabilization pass.

## Canonical pilot accounts (passwords never change by design)

All accounts are recreated or **synchronized** on every API startup via `services/pilot_seed.py` (idempotent).  
Passwords are reset **only** if the stored hash does not verify against the documented password (e.g. after manual DB tampering or a broken hash).

### Doctors (password: `Doctor123!`)

| Email |
|-------|
| `dr.amu@example.com` |
| `dr.souleimane@example.com` |
| `dr.fatou@example.com` |
| `dr.mamady@example.com` |

### Patient (password: `Patient123!`)

| Email |
|-------|
| `test.patient@example.com` |

### Legacy email merge

If an older database still has `dr.soulaiman@example.com`, startup seed **renames** that user to `dr.souleimane@example.com` when the canonical address is free (avoids duplicate doctor rows).

---

## Backend: startup workflow

1. `Base.metadata.create_all` — schema present.
2. `database_migrations.ensure_doctor_geolocation_columns` — additive SQLite/Postgres columns.
3. **`services.pilot_seed.seed_pilot_accounts()`** — always runs: doctors + pilot patient.
4. Optional (off by default):
   - `ENABLE_STARTUP_TEST_USER=true` → `test123@gmail.com` / `123456` (not part of pilot; disable for clean pilots).
   - `ENABLE_STARTUP_SEED=true` → extra dev user `test@test.com` / `test123` only.
   - `ENABLE_DEMO_CLINIC_SEED=true` → extra demo patients + appointments (`services/demo_clinic_seed.py`).

---

## Full local reset + reseed

From repository root (Python 3 with project dependencies installed):

```bash
python scripts/reset_pilot_db.py
```

- **SQLite** (`DATABASE_URL` default `sqlite:///./sante.db`): disposes the engine, deletes the DB file, recreates tables, runs pilot seed.
- **Postgres**: drops all tables registered on SQLAlchemy `Base`, recreates them, runs pilot seed (**destructive** for that database).

Then start the API (e.g. `uvicorn main:app --reload`) and verify logins:

```bash
python scripts/verify_pilot_logins.py http://127.0.0.1:8000
```

All five accounts must return HTTP 200 and an `access_token`.

---

## Frontend: auth stabilization

### Token persistence

- Tokens: `localStorage.token` and `localStorage.access_token` (both set to the same JWT on login).
- Role / user id cache: `user_role`, `user_id` (updated from `/auth/me` after login and on session restore).

### Session restore

- On load, if a token exists, `GET /auth/me` runs once.
- On failure: **`clearClientAuth()`** removes token + cached ids/role and clears the axios default `Authorization` header.

### Login

- After `POST /auth/login-json`, the client **always** calls **`GET /auth/me`** so `doctor_id` and role are always consistent (fixes broken links to `/doctors/:id`).

### Logout

- Clears password-reset flags, calls **`clearClientAuth()`**, clears React user state.

### Invalid token / 401

- Response interceptor: `clearClientAuth()` then **`window.location.replace('/login')`** (no history stack pile-up; no-op if already on `/login`).

### Auth loops prevented

- **`AppointmentContext`** loads `/appointments/me` **only when `user` is non-null** after auth bootstrap.  
  Previously, unauthenticated visitors triggered protected requests and a redirect to `/login` even on public routes — removed.

---

## Manual verification checklist (pilot)

1. **Doctor** — login `dr.amu@example.com` / `Doctor123!` → dashboard → agenda → liste RDV charge sans spinner infini.
2. **Patient** — login `test.patient@example.com` / `Patient123!` → dashboard → rendez-vous.
3. **Logout** — retour login, pas de token résiduel (onglet Application → Local Storage).
4. **Bad token** — mettre un JWT invalide dans `localStorage.token`, recharger → redirection login sans boucle.

---

## Known remaining issues / limits

- **Postgres reset** `drop_all` is destructive; use only on dev/staging or dedicated pilot DBs.
- **`ENABLE_STARTUP_SEED`** still creates `test@test.com` — optional; keep **disabled** for a clean pilot aligned with this document only.
- **Concurrent 401s** can still trigger multiple redirects in theory; `replace` + cleared storage limits impact.
- **Production**: turn off any optional seeds; rely on `pilot_seed` only or replace with real user provisioning.

---

## Files touched (reference)

| Area | File |
|------|------|
| Pilot seed | `services/pilot_seed.py` |
| Startup | `main.py` |
| Reset | `scripts/reset_pilot_db.py` |
| Login verify | `scripts/verify_pilot_logins.py` |
| Auth state | `frontend-sante/frontend/src/contexts/AuthContext.jsx` |
| Appointments fetch guard | `frontend-sante/frontend/src/contexts/AppointmentContext.jsx` |
| Token clear + 401 | `frontend-sante/frontend/src/services/httpClient.js` |
| Demo clinic compatibility | `services/demo_clinic_seed.py` |
