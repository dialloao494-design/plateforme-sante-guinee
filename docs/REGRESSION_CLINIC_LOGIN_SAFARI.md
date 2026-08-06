# Regression lock — Clinic login / print on Safari (cross-origin SPA)

## Exact root cause

Production frontend (`*.vercel.app`) and API (`*.up.railway.app`) are **cross-site**.

After cookie-auth hardening, production login responses set HttpOnly cookies but **omitted** `access_token` / `refresh_token` from JSON (`AUTH_JSON_TOKENS` defaulted off in production). The SPA also stopped storing/sending Bearer tokens.

Safari / iPhone ITP often blocks those third-party cookies → `/auth/me` fails after “login” → generic error **« Une erreur est survenue, veuillez réessayer »**. Repeated failures lock the account (HTTP 429), still shown as the same generic message. PDF printing fails for the same auth reason.

## Permanent fix

1. Always return bearer tokens in login/refresh JSON (unless `AUTH_JSON_TOKENS=false`).
2. SPA persists tokens in `sessionStorage` and sends `Authorization: Bearer …`.
3. Cookies remain as complementary same-site path; CSRF still applies for cookie-only mutations.
4. Login UI surfaces lockouts (429) clearly.
5. Staff password reset clears `locked_until` / failed attempts.

## Tests / CI

- `tests/test_auth_spa_cross_origin_tokens.py`
- `frontend-sante/frontend/src/utils/loginErrors.test.mjs`
- `frontend-sante/frontend/src/utils/authStorage.test.mjs`
- Covered by `npm run test:unit` + `pytest` in CI
