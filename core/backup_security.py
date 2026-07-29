"""
Backup encryption, integrity, and restore pre-validation — Security Wave 5.
"""

from __future__ import annotations

import gzip
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


MIN_VALID_BYTES = 200
BACKUP_MAGIC = b"\x00SGBKENC\x01"


@dataclass(frozen=True)
class BackupArtifact:
    path: Path
    sha256: str
    bytes: int
    encrypted: bool
    verified: bool
    message: str = ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256_sidecar(path: Path, digest: str | None = None) -> Path:
    value = digest or sha256_file(path)
    sidecar = path.with_suffix(path.suffix + ".sha256") if path.suffix else Path(str(path) + ".sha256")
    # Prefer path.sql.gz.sha256 style
    sidecar = Path(str(path) + ".sha256")
    sidecar.write_text(value + "\n", encoding="utf-8")
    try:
        os.chmod(sidecar, 0o600)
    except OSError:
        pass
    return sidecar


def verify_sha256_sidecar(path: Path) -> tuple[bool, str]:
    sidecar = Path(str(path) + ".sha256")
    if not sidecar.is_file():
        return False, "sidecar_missing"
    import hmac

    expected = sidecar.read_text(encoding="utf-8").strip().split()[0]
    actual = sha256_file(path)
    if not hmac.compare_digest(expected, actual):
        return False, "sha256_mismatch"
    return True, actual


def verify_gzip_sql_backup(path: Path, *, min_bytes: int = MIN_VALID_BYTES) -> dict[str, Any]:
    """Validate plaintext .sql.gz backup integrity (gzip CRC + SQL-ish header)."""
    result: dict[str, Any] = {
        "ok": False,
        "path": str(path),
        "bytes": 0,
        "sha256": None,
        "error": None,
    }
    if not path.is_file():
        result["error"] = "missing"
        return result
    size = path.stat().st_size
    result["bytes"] = size
    if size < min_bytes:
        result["error"] = "undersized"
        return result
    try:
        with gzip.open(path, "rb") as gz:
            header = gz.read(256)
            if not header:
                result["error"] = "empty_gzip"
                return result
            while gz.read(1024 * 1024):
                pass
            sqlish = (
                header.startswith(b"--")
                or header.startswith(b"PGDMP")
                or b"PostgreSQL" in header
                or header.startswith(b"SET ")
                or header.startswith(b"CREATE ")
            )
            if not sqlish:
                result["error"] = "unexpected_header"
                return result
    except Exception as exc:
        result["error"] = f"gzip_invalid:{exc}"
        return result

    digest = sha256_file(path)
    result["ok"] = True
    result["sha256"] = digest
    return result


def _fernet_from_env(key: str | None = None) -> Fernet:
    raw = (key if key is not None else os.getenv("BACKUP_ENCRYPTION_KEY") or "").strip()
    if not raw:
        # Fall back to attachment key for single-node appliances when dedicated key unset.
        raw = (os.getenv("ATTACHMENT_ENCRYPTION_KEY") or "").strip()
    if not raw:
        raise RuntimeError(
            "BACKUP_ENCRYPTION_KEY (or ATTACHMENT_ENCRYPTION_KEY) required for backup encryption"
        )
    return Fernet(raw.encode("utf-8"))


def encrypt_backup_file(
    src: Path,
    dest: Path | None = None,
    *,
    key: str | None = None,
) -> BackupArtifact:
    """Encrypt a verified .sql.gz backup with Fernet (portable, CI-friendly)."""
    verified = verify_gzip_sql_backup(src)
    if not verified["ok"]:
        raise RuntimeError(f"Cannot encrypt invalid backup: {verified.get('error')}")

    target = dest or Path(str(src) + ".enc")
    fernet = _fernet_from_env(key)
    ciphertext = BACKUP_MAGIC + fernet.encrypt(src.read_bytes())
    target.write_bytes(ciphertext)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    digest = sha256_file(target)
    write_sha256_sidecar(target, digest)
    return BackupArtifact(
        path=target,
        sha256=digest,
        bytes=target.stat().st_size,
        encrypted=True,
        verified=True,
        message="encrypted",
    )


def decrypt_backup_file(
    src: Path,
    dest: Path | None = None,
    *,
    key: str | None = None,
    verify_sidecar: bool = True,
) -> BackupArtifact:
    if verify_sidecar:
        ok, detail = verify_sha256_sidecar(src)
        if not ok and detail == "sha256_mismatch":
            raise RuntimeError("Encrypted backup integrity check failed (sha256 mismatch)")
        # sidecar_missing allowed for legacy

    payload = src.read_bytes()
    if not payload.startswith(BACKUP_MAGIC):
        raise RuntimeError("Not a Santé Guinée encrypted backup (missing magic)")
    fernet = _fernet_from_env(key)
    try:
        plaintext = fernet.decrypt(payload[len(BACKUP_MAGIC) :])
    except InvalidToken as exc:
        raise RuntimeError("Backup decryption failed — wrong key or corrupted file") from exc

    target = dest or Path(str(src).removesuffix(".enc"))
    if target == src:
        target = Path(str(src) + ".decrypted.sql.gz")
    target.write_bytes(plaintext)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass

    verified = verify_gzip_sql_backup(target)
    if not verified["ok"]:
        try:
            target.unlink()
        except OSError:
            pass
        raise RuntimeError(f"Decrypted backup failed validation: {verified.get('error')}")

    return BackupArtifact(
        path=target,
        sha256=verified["sha256"],
        bytes=verified["bytes"],
        encrypted=False,
        verified=True,
        message="decrypted_and_verified",
    )


def pre_restore_validation(
    backup_path: Path,
    *,
    require_encryption: bool = False,
    key: str | None = None,
) -> dict[str, Any]:
    """
    Validate a backup prior to restore drill / live restore.
    Accepts plaintext .sql.gz or .sql.gz.enc.
    """
    report: dict[str, Any] = {
        "ok": False,
        "path": str(backup_path),
        "encrypted": False,
        "checks": [],
        "error": None,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    path = Path(backup_path)
    if not path.is_file():
        report["error"] = "missing"
        return report

    encrypted = path.name.endswith(".enc") or path.read_bytes()[:9] == BACKUP_MAGIC
    report["encrypted"] = encrypted

    if require_encryption and not encrypted:
        report["error"] = "encryption_required"
        report["checks"].append({"name": "encryption", "ok": False})
        return report

    working = path
    tmp_decrypted: Path | None = None
    try:
        if encrypted:
            sidecar_ok, sidecar_detail = verify_sha256_sidecar(path)
            report["checks"].append(
                {"name": "encrypted_sha256", "ok": sidecar_ok or sidecar_detail == "sidecar_missing", "detail": sidecar_detail}
            )
            if sidecar_detail == "sha256_mismatch":
                report["error"] = "sha256_mismatch"
                return report
            artifact = decrypt_backup_file(path, key=key, verify_sidecar=False)
            working = artifact.path
            tmp_decrypted = working
            report["checks"].append({"name": "decrypt", "ok": True})

        verified = verify_gzip_sql_backup(working)
        report["checks"].append(
            {"name": "gzip_sql", "ok": verified["ok"], "detail": verified.get("error") or verified.get("sha256")}
        )
        if not verified["ok"]:
            report["error"] = verified.get("error")
            return report

        # Optional plaintext sidecar
        plain_sidecar = Path(str(working) + ".sha256")
        if plain_sidecar.is_file():
            ok, detail = verify_sha256_sidecar(working)
            report["checks"].append({"name": "plaintext_sha256", "ok": ok, "detail": detail})
            if not ok:
                report["error"] = detail
                return report

        report["ok"] = True
        report["sha256"] = verified["sha256"]
        report["bytes"] = verified["bytes"]
        return report
    finally:
        if tmp_decrypted and tmp_decrypted.exists() and tmp_decrypted != path:
            # Keep decrypted only if caller needs it — for validation we clean up.
            try:
                tmp_decrypted.unlink()
            except OSError:
                pass


def disaster_recovery_checklist() -> list[dict[str, str]]:
    """Machine-readable DR checklist for evidence / runbooks."""
    return [
        {"id": "DR-01", "item": "Identify latest verified encrypted backup (SHA-256 OK)"},
        {"id": "DR-02", "item": "Isolate restore target network (no production traffic)"},
        {"id": "DR-03", "item": "Take pre-restore snapshot of current DB volume"},
        {"id": "DR-04", "item": "Run restore-drill (ephemeral) before live restore"},
        {"id": "DR-05", "item": "Live restore with dual-control / break-glass approval"},
        {"id": "DR-06", "item": "Rotate JWT, sync, update, attachment, and backup keys post-restore"},
        {"id": "DR-07", "item": "Verify /health/ready and sample clinical read paths"},
        {"id": "DR-08", "item": "Document RPO/RTO achieved and close incident ticket"},
    ]
