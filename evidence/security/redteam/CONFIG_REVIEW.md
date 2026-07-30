# Red Team — Configuration Review

Date: 2026-07-29

## Production boot
- JWT/DB/Jitsi/reminder secrets validated for deployed environments
- Attachment encryption required unless dual emergency attestation
- DB TLS: `sslmode=disable` forbidden; Railway requires require/verify-* unless dual attestation
- Pilot/demo seed flags abort production boot
- Security middleware (SlowAPI + headers) fail-loud when `is_deployed`

## WhatsApp / reminders
- POST webhook requires `WHATSAPP_APP_SECRET` + valid `X-Hub-Signature-256`
- Verify token has no insecure default
- Reminder respond tokens fail closed when secret unset

## Tenancy
- Clinic-scoped roles fail closed when `clinic_id` is null
- Platform roles remain global by design

## Updates / clinic node
- Unsigned or empty digest maps with image payloads rejected
- Path traversal in manifest file entries rejected

## Secrets in repository
- Working tree AASMA plaintext passwords removed / env-gated
- Git history rotation required (see FINAL report RR-1)
