# Agent operating context

Before making a significant product, architecture, UX, security, offline, test,
or deployment change, read [`docs/PLATFORM_EXCELLENCE_ROADMAP.md`](docs/PLATFORM_EXCELLENCE_ROADMAP.md).
It is the canonical cross-agent assessment and improvement backlog for this
repository.

When work materially changes an item in that roadmap:

1. update the item's status and evidence in the same change;
2. distinguish code-complete, locally verified, CI-verified, production-verified,
   and field-validated states;
3. do not mark hospital-wide readiness from unit tests or HTTP health alone;
4. preserve patient safety, clinic isolation, auditability, offline idempotency,
   and rollback/recovery behavior while refactoring;
5. add or update regression coverage for every corrected defect.

Historical reports under `docs/` are evidence snapshots. If they conflict with
the living roadmap, investigate the dated evidence and update the roadmap; do
not silently choose the more optimistic verdict.
