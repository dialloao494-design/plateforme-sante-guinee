# Clinic Node Security Hardening Checklist — Security Wave 4

**Audience:** Field technicians / clinic IT installing the mini-PC appliance  
**Related:** `deploy/clinic-node/`, architecture §§12–17, 21

Offline Clinic Node **product features** (sync/license UX) remain frozen; this checklist is **security-only**.

---

## Before power-on

- [ ] Dedicated mini-PC + UPS (not a shared personal laptop)
- [ ] Full-disk encryption (LUKS) enabled with strong boot password
- [ ] Cable lock / locked cabinet
- [ ] Run `sudo deploy/clinic-node/scripts/verify-luks.sh /path/to/luks-evidence.txt`

## Network (LAN)

- [ ] Prefer **bridge** networking (`compose.yml`) — Postgres not published to LAN
- [ ] Host-network (`compose.host.yml`) is **lab-only**; requires `CLINIC_NODE_ALLOW_HOST_NETWORK=true`
- [ ] Host mode binds Postgres to `127.0.0.1` only
- [ ] Apply firewall: `sudo deploy/clinic-node/scripts/harden-host-firewall.sh`  
      (allow 80/443; deny 5432/8000; SSH from admin VLAN if possible)

## Local HTTPS / certificates

- [ ] Installer ran `generate-pki.sh` (CA + server cert)
- [ ] Audit permissions: `deploy/clinic-node/scripts/audit-pki-perms.sh`
- [ ] Distribute **only** `ca-trust.crt` to workstations — never email `ca.key` / `privkey.pem`
- [ ] Confirm HTTP → HTTPS redirect and HSTS in browser

## Local authentication / secrets

- [ ] `.env` mode `600`; `ADMIN_CREDENTIALS.txt` mode `600`
- [ ] Unique `JWT_SECRET`, `CLINIC_NODE_LICENSE_SECRET`, `CLINIC_NODE_UPDATE_SECRET`
- [ ] `ATTACHMENT_ENCRYPTION_KEY` (Fernet) set — PHI attachments encrypted at rest
- [ ] Demo/pilot seed flags are `false`
- [ ] First admin login forces password change

## Offline database

- [ ] Strong generated `POSTGRES_PASSWORD`
- [ ] Bridge mode: DB only on Docker network `clinic`
- [ ] No remote admin tools pointed at LAN `:5432`

## Local backups

- [ ] Schedule dumps under `data/backups/`
- [ ] Encrypt before off-box copy: `scripts/encrypt-backup.sh backup.sql.gz`
- [ ] Verify `.sha256` sidecar after encrypt
- [ ] Keep age identity / GPG passphrase offline (USB in sealed envelope)
- [ ] Quarterly restore drill (decrypt → restore to ephemeral DB)

## Physical theft response

- [ ] Power off / revoke workstation CA trust if CA key may be compromised
- [ ] Rotate JWT, license, update, attachment, and backup keys after recovery
- [ ] Restore from encrypted offsite backup onto a new encrypted disk

## Validation

```bash
bash deploy/clinic-node/scripts/validate-clinic-node-security.sh
python scripts/deploy/validate_security_wave4.py
```
