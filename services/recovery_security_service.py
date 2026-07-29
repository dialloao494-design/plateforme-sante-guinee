"""
Wave 5 — recovery orchestration (encrypt → integrity → restore gate → DR checklist).

Does not start Postgres restore; validates packages and returns a pass/fail report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.backup_security import (
    disaster_recovery_checklist,
    encrypt_backup_file,
    pre_restore_validation,
    verify_sha256_sidecar,
    write_sha256_sidecar,
)


def build_encrypted_recovery_package(
    plain_path: Path,
    *,
    out_dir: Path | None = None,
    key: str | None = None,
) -> dict[str, Any]:
    """Gzip/SQL dump → SHA-256 sidecar → Fernet package."""
    plain = Path(plain_path)
    if not plain.is_file():
        raise FileNotFoundError(str(plain))
    target_dir = Path(out_dir) if out_dir is not None else plain.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    sha_path = write_sha256_sidecar(plain)
    enc_path = target_dir / f"{plain.name}.enc"
    artifact = encrypt_backup_file(plain, enc_path, key=key)
    sidecar_ok, _ = verify_sha256_sidecar(artifact.path)
    return {
        "plain": str(plain),
        "sha256_sidecar": str(sha_path),
        "encrypted": str(artifact.path),
        "encrypted_sha256": artifact.sha256,
        "sha256_ok": sidecar_ok,
    }


def validate_recovery_scenarios(
    *,
    plain_backup: Path | None = None,
    encrypted_backup: Path | None = None,
    require_encryption: bool = False,
    key: str | None = None,
) -> dict[str, Any]:
    """
    Run the Wave 5 recovery scenario matrix.

    Scenarios:
      S1 — plaintext dump passes gzip/SQL precheck
      S2 — SHA-256 sidecar matches when present
      S3 — encrypted package decrypts and passes precheck
      S4 — disaster-recovery checklist is complete
    """
    scenarios: list[dict[str, Any]] = []

    if plain_backup is not None:
        s1 = pre_restore_validation(
            Path(plain_backup),
            require_encryption=False,
            key=key,
        )
        scenarios.append({"id": "S1_plain_precheck", **s1})
        sidecar = Path(str(plain_backup) + ".sha256")
        if sidecar.is_file():
            ok, detail = verify_sha256_sidecar(Path(plain_backup))
            scenarios.append({"id": "S2_sha256_match", "ok": ok, "detail": detail})

    if encrypted_backup is not None:
        s3 = pre_restore_validation(
            Path(encrypted_backup),
            require_encryption=require_encryption or True,
            key=key,
        )
        scenarios.append({"id": "S3_encrypted_restore_gate", **s3})

    checklist = disaster_recovery_checklist()
    scenarios.append(
        {
            "id": "S4_dr_checklist",
            "ok": len(checklist) >= 8 and all(item.get("id") for item in checklist),
            "items": checklist,
        }
    )

    all_ok = all(bool(s.get("ok")) for s in scenarios)
    return {"ok": all_ok, "scenarios": scenarios}
