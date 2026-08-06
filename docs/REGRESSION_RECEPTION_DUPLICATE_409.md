# Regression lock — Reception duplicate patient 409

## Exact root cause

`POST /clinical/reception/his/patients` returns **HTTP 409** with a structured FastAPI detail object:

```json
{
  "detail": {
    "code": "duplicate_patient",
    "message": "Un ou plusieurs patients similaires existent déjà",
    "matches": [{ "id": 1, "match_reasons": ["phone"] }]
  }
}
```

The reception UI historically:

1. Parsed `detail` only when it was a **string** or **validation array** (`formatApiError`).
2. Had **no** `confirm_duplicate` confirm/open-existing path.

Axios then fell through to `err.message` → `Request failed with status code 409`, so staff believed registration was broken whenever a phone or name+DOB matched an existing patient (common in clinic workflows).

## Why the bug reappeared

This was not a flaky race — it was a **contract mismatch + duplicated UI surface**:

1. Backend already implemented the safe duplicate check + `confirm_duplicate` override.
2. Frontend never completed the consumer side of that contract.
3. Reception UI was later split into a modular tree (`reception/hooks`, `RegisterTab`) on feature branches while hotfixes landed on the older monolithic dashboard. Merges could ship one surface without the other, so a “fixed once” patch on the monolith did not permanently protect production after modularization.

## Permanent protection

| Layer | Guard |
|-------|--------|
| Shared helper | `frontend-sante/frontend/src/pages/clinical/reception/registrationConflict.js` — only place that interprets duplicate 409 for reception |
| Unit | `apiError.test.mjs` + `registrationConflict.test.mjs` (object detail, confirm payload, RegisterTab testids, hook import) |
| Integration | `tests/test_reception_his_duplicate_registration.py` (409 object contract + confirm + search/open) |
| E2E | `e2e/reception-registration.spec.js` duplicate panel + confirm |
| CI | `.github/workflows/ci.yml` runs `npm run test:unit`, `npm run test:offline`, full `pytest`, and Playwright e2e |

Removing the object-detail branch, the shared helper, the panel testids, or the backend object contract fails CI before merge.
