"""
Update package signing, verification, and rollback metadata — Security Wave 5.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class UpdateSecurityError(RuntimeError):
    pass


def _canonical_manifest(claims: dict[str, Any]) -> bytes:
    return json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")


def resolve_update_secret(*, allow_jwt_fallback: bool = False) -> str:
    """
    Prefer CLINIC_NODE_UPDATE_SECRET. JWT fallback is forbidden for clinic-node /
    production unless explicitly allowed (lab only).
    """
    update_secret = (os.getenv("CLINIC_NODE_UPDATE_SECRET") or "").strip()
    if update_secret:
        return update_secret
    jwt = (os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "").strip()
    env = (os.getenv("ENVIRONMENT") or "").lower().strip()
    if jwt and allow_jwt_fallback and env not in {"clinic-node", "clinic_node", "production"}:
        return jwt
    if jwt and allow_jwt_fallback and os.getenv("ALLOW_UPDATE_JWT_FALLBACK", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return jwt
    raise UpdateSecurityError(
        "CLINIC_NODE_UPDATE_SECRET is required for update signing/verification "
        "(JWT_SECRET fallback is not allowed in production/clinic-node)"
    )


def sign_manifest(claims: dict[str, Any], *, secret: str | None = None) -> str:
    key = (secret or resolve_update_secret()).encode("utf-8")
    return hmac.new(key, _canonical_manifest(claims), hashlib.sha256).hexdigest()


def verify_manifest(
    claims: dict[str, Any],
    signature_hex: str,
    *,
    secret: str | None = None,
) -> bool:
    expected = sign_manifest(claims, secret=secret)
    return hmac.compare_digest(expected, (signature_hex or "").strip())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class UpdatePackage:
    root: Path
    claims: dict[str, Any]
    signature: str

    @property
    def version(self) -> str:
        return str(self.claims.get("version") or "unknown")

    @property
    def backup_required(self) -> bool:
        return bool(self.claims.get("backup_required", True))


def load_and_verify_package(package_dir: Path, *, secret: str | None = None) -> UpdatePackage:
    root = Path(package_dir)
    manifest = root / "manifest.json"
    sigfile = root / "manifest.sig"
    if not manifest.is_file():
        raise UpdateSecurityError("manifest.json missing")
    if not sigfile.is_file():
        raise UpdateSecurityError("manifest.sig missing — refusing unsigned package")

    claims = json.loads(manifest.read_text(encoding="utf-8"))
    signature = sigfile.read_text(encoding="utf-8").strip()
    if not verify_manifest(claims, signature, secret=secret):
        raise UpdateSecurityError("SIGNATURE_INVALID")

    # Optional file digests listed in manifest["files"] = {"rel/path": "sha256"}
    files = claims.get("files") or {}
    if isinstance(files, dict):
        for rel, expected in files.items():
            path = root / str(rel)
            if not path.is_file():
                raise UpdateSecurityError(f"missing_file:{rel}")
            actual = sha256_file(path)
            if not hmac.compare_digest(actual, str(expected).strip()):
                raise UpdateSecurityError(f"file_digest_mismatch:{rel}")

    return UpdatePackage(root=root, claims=claims, signature=signature)


def write_signed_package(
    package_dir: Path,
    claims: dict[str, Any],
    *,
    secret: str | None = None,
) -> UpdatePackage:
    root = Path(package_dir)
    root.mkdir(parents=True, exist_ok=True)
    # Auto-hash files under images/ if present and not already listed
    files = dict(claims.get("files") or {})
    images = root / "images"
    if images.is_dir():
        for path in sorted(images.rglob("*")):
            if path.is_file():
                rel = str(path.relative_to(root)).replace("\\", "/")
                files[rel] = sha256_file(path)
    claims = {**claims, "files": files}
    (root / "manifest.json").write_text(
        json.dumps(claims, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    signature = sign_manifest(claims, secret=secret)
    (root / "manifest.sig").write_text(signature + "\n", encoding="utf-8")
    return UpdatePackage(root=root, claims=claims, signature=signature)


def record_rollback_image(tag_file: Path, image_id: str) -> None:
    tag_file.parent.mkdir(parents=True, exist_ok=True)
    tag_file.write_text(image_id.strip() + "\n", encoding="utf-8")
    try:
        os.chmod(tag_file, 0o600)
    except OSError:
        pass


def read_rollback_image(tag_file: Path) -> str | None:
    if not tag_file.is_file():
        return None
    value = tag_file.read_text(encoding="utf-8").strip()
    return value or None
