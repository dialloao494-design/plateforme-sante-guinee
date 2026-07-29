"""
Security Wave 5 — sync, delta, replay, backup encryption, restore, DR, updates, rollback.
"""

from __future__ import annotations

import gzip
import os
import time
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from core.backup_security import (
    BACKUP_MAGIC,
    decrypt_backup_file,
    disaster_recovery_checklist,
    encrypt_backup_file,
    pre_restore_validation,
    verify_gzip_sql_backup,
    write_sha256_sidecar,
)
from core.sync_security import (
    ReplayGuard,
    build_signed_envelope,
    delta_batch_integrity,
    require_sync_token,
    verify_signed_envelope,
)
from core.update_security import (
    UpdateSecurityError,
    load_and_verify_package,
    read_rollback_image,
    record_rollback_image,
    resolve_update_secret,
    write_signed_package,
)
from services.recovery_security_service import (
    build_encrypted_recovery_package,
    validate_recovery_scenarios,
)


SECRET = "wave5-sync-hmac-secret-" + ("S" * 24)
UPDATE_SECRET = "wave5-update-secret-" + ("U" * 24)


def _minimal_sql_gz(path: Path, payload: bytes | None = None) -> Path:
    # Compressed size must be >= MIN_VALID_BYTES (200); pad uncompressed content.
    body = payload or (
        b"--\n-- PostgreSQL database dump\n--\n"
        b"SET statement_timeout = 0;\n"
        b"CREATE TABLE patients (id int);\n"
        + (b"-- pad line for backup size validation\n" * 400)
    )
    with gzip.open(path, "wb", compresslevel=1) as gz:
        gz.write(body)
    if path.stat().st_size < 200:
        # Extremely compressible edge case — append incompressible noise via raw rewrite.
        with gzip.open(path, "wb", compresslevel=1) as gz:
            gz.write(body + os.urandom(512))
    return path


@pytest.fixture
def backup_key(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)
    return key


@pytest.fixture
def update_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "clinic-node")
    monkeypatch.setenv("CLINIC_NODE_UPDATE_SECRET", UPDATE_SECRET)
    monkeypatch.delenv("ALLOW_UPDATE_JWT_FALLBACK", raising=False)
    return UPDATE_SECRET


class TestSyncSignedEnvelopes:
    def test_build_and_verify_ok(self):
        env = build_signed_envelope(
            secret=SECRET,
            event_id="evt-1",
            clinic_id=42,
            entity_type="patient",
            operation="upsert",
            payload={"name": "Aissatou"},
        )
        ok, reason = verify_signed_envelope(env.to_dict(), secret=SECRET)
        assert ok and reason == "ok"
        assert len(env.content_sha256) == 64
        assert len(env.signature) == 64

    def test_tampered_payload_rejected(self):
        env = build_signed_envelope(
            secret=SECRET,
            event_id="evt-2",
            clinic_id=1,
            entity_type="visit",
            operation="create",
            payload={"ok": True},
        ).to_dict()
        env["payload"] = {"ok": False}
        ok, reason = verify_signed_envelope(env, secret=SECRET)
        assert not ok
        assert reason in {"content_sha256_mismatch", "signature_invalid"}

    def test_wrong_secret_rejected(self):
        env = build_signed_envelope(
            secret=SECRET,
            event_id="evt-3",
            clinic_id=1,
            entity_type="lab",
            operation="update",
            payload={},
        ).to_dict()
        ok, reason = verify_signed_envelope(env, secret="wrong-secret")
        assert not ok
        assert reason == "signature_invalid"

    def test_timestamp_skew_rejected(self):
        env = build_signed_envelope(
            secret=SECRET,
            event_id="evt-4",
            clinic_id=1,
            entity_type="rx",
            operation="create",
            payload={},
            timestamp=int(time.time()) - 10_000,
        ).to_dict()
        ok, reason = verify_signed_envelope(env, secret=SECRET, max_skew_seconds=300)
        assert not ok
        assert reason == "timestamp_skew"


class TestReplayProtection:
    def test_nonce_and_event_replay_rejected(self):
        guard = ReplayGuard(ttl_seconds=600)
        env = build_signed_envelope(
            secret=SECRET,
            event_id="evt-replay",
            clinic_id=9,
            entity_type="patient",
            operation="upsert",
            payload={"n": 1},
        ).to_dict()
        ok, _ = verify_signed_envelope(env, secret=SECRET)
        assert ok
        first, reason1 = guard.consume_envelope(env)
        second, reason2 = guard.consume_envelope(env)
        assert first and reason1 == "ok"
        assert not second
        assert reason2 == "replay_nonce"

    def test_event_id_replay_independent_of_nonce(self):
        guard = ReplayGuard(ttl_seconds=600)
        assert guard.consume("event:same")
        assert not guard.consume("event:same")


class TestSyncTokenAndDelta:
    def test_require_sync_token(self):
        ok, reason = require_sync_token("abc", "abc")
        assert ok and reason == "ok"
        ok, reason = require_sync_token("abc", "xyz")
        assert not ok and reason == "sync_token_invalid"
        ok, reason = require_sync_token("abc", None)
        assert not ok and reason == "sync_token_not_configured"

    def test_delta_batch_integrity_stable(self):
        a = build_signed_envelope(
            secret=SECRET,
            event_id="a",
            clinic_id=1,
            entity_type="x",
            operation="c",
            payload={"i": 1},
            nonce="n1",
            timestamp=1_700_000_000,
        ).to_dict()
        b = build_signed_envelope(
            secret=SECRET,
            event_id="b",
            clinic_id=1,
            entity_type="x",
            operation="c",
            payload={"i": 2},
            nonce="n2",
            timestamp=1_700_000_001,
        ).to_dict()
        h1 = delta_batch_integrity([a, b])
        h2 = delta_batch_integrity([a, b])
        h3 = delta_batch_integrity([b, a])
        assert h1 == h2
        assert h1 != h3


class TestBackupEncryption:
    def test_encrypt_decrypt_roundtrip(self, backup_key, tmp_path):
        plain = _minimal_sql_gz(tmp_path / "dump.sql.gz")
        write_sha256_sidecar(plain)
        enc = encrypt_backup_file(plain, tmp_path / "dump.sql.gz.enc")
        assert enc.encrypted
        assert enc.path.read_bytes().startswith(BACKUP_MAGIC)
        out = decrypt_backup_file(enc.path, tmp_path / "out.sql.gz")
        assert out.verified
        assert verify_gzip_sql_backup(out.path)["ok"]

    def test_tampered_ciphertext_fails(self, backup_key, tmp_path):
        plain = _minimal_sql_gz(tmp_path / "dump.sql.gz")
        enc = encrypt_backup_file(plain, tmp_path / "dump.sql.gz.enc")
        data = bytearray(enc.path.read_bytes())
        data[-5] ^= 0xFF
        enc.path.write_bytes(bytes(data))
        # rewrite matching sidecar so decrypt reaches Fernet
        write_sha256_sidecar(enc.path)
        with pytest.raises(RuntimeError, match="decryption failed|wrong key|corrupted"):
            decrypt_backup_file(enc.path, tmp_path / "bad.sql.gz")

    def test_sha256_mismatch_blocks_decrypt(self, backup_key, tmp_path):
        plain = _minimal_sql_gz(tmp_path / "dump.sql.gz")
        enc = encrypt_backup_file(plain, tmp_path / "dump.sql.gz.enc")
        Path(str(enc.path) + ".sha256").write_text("0" * 64 + "\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="integrity|sha256"):
            decrypt_backup_file(enc.path, tmp_path / "bad.sql.gz")


class TestRestoreValidation:
    def test_pre_restore_plain_and_encrypted(self, backup_key, tmp_path):
        plain = _minimal_sql_gz(tmp_path / "dump.sql.gz")
        write_sha256_sidecar(plain)
        r1 = pre_restore_validation(plain)
        assert r1["ok"]
        enc = encrypt_backup_file(plain, tmp_path / "dump.sql.gz.enc")
        r2 = pre_restore_validation(enc.path, require_encryption=True)
        assert r2["ok"]
        assert r2["encrypted"]

    def test_require_encryption_rejects_plain(self, backup_key, tmp_path):
        plain = _minimal_sql_gz(tmp_path / "dump.sql.gz")
        r = pre_restore_validation(plain, require_encryption=True)
        assert not r["ok"]
        assert r["error"] == "encryption_required"


class TestDisasterRecovery:
    def test_checklist_complete(self):
        items = disaster_recovery_checklist()
        assert len(items) >= 8
        ids = {i["id"] for i in items}
        assert {"DR-01", "DR-04", "DR-06", "DR-08"} <= ids

    def test_recovery_scenarios_matrix(self, backup_key, tmp_path):
        plain = _minimal_sql_gz(tmp_path / "dump.sql.gz")
        pkg = build_encrypted_recovery_package(plain, out_dir=tmp_path / "pkg")
        assert pkg["sha256_ok"]
        report = validate_recovery_scenarios(
            plain_backup=Path(pkg["plain"]),
            encrypted_backup=Path(pkg["encrypted"]),
            require_encryption=True,
            key=backup_key,
        )
        assert report["ok"], report
        ids = [s["id"] for s in report["scenarios"]]
        assert "S1_plain_precheck" in ids
        assert "S3_encrypted_restore_gate" in ids
        assert "S4_dr_checklist" in ids


class TestUpdateSecurity:
    def test_signed_package_roundtrip(self, update_env, tmp_path):
        root = tmp_path / "pkg"
        (root / "images").mkdir(parents=True)
        (root / "images" / "note.txt").write_text("payload\n", encoding="utf-8")
        pkg = write_signed_package(
            root,
            {"version": "1.0.1", "backup_required": True},
            secret=update_env,
        )
        loaded = load_and_verify_package(root, secret=update_env)
        assert loaded.version == "1.0.1"
        assert "images/note.txt" in loaded.claims["files"]
        assert pkg.signature == loaded.signature

    def test_bad_signature_rejected(self, update_env, tmp_path):
        root = tmp_path / "pkg"
        write_signed_package(root, {"version": "9.9.9"}, secret=update_env)
        (root / "manifest.sig").write_text("deadbeef" * 8 + "\n", encoding="utf-8")
        with pytest.raises(UpdateSecurityError, match="SIGNATURE_INVALID"):
            load_and_verify_package(root, secret=update_env)

    def test_file_digest_mismatch_rejected(self, update_env, tmp_path):
        root = tmp_path / "pkg"
        (root / "images").mkdir(parents=True)
        f = root / "images" / "a.bin"
        f.write_bytes(b"abc")
        write_signed_package(root, {"version": "1.0.0"}, secret=update_env)
        f.write_bytes(b"tampered")
        with pytest.raises(UpdateSecurityError, match="file_digest_mismatch"):
            load_and_verify_package(root, secret=update_env)

    def test_jwt_fallback_refused_in_clinic_node(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "clinic-node")
        monkeypatch.delenv("CLINIC_NODE_UPDATE_SECRET", raising=False)
        monkeypatch.setenv("JWT_SECRET", "jwt-only-secret-" + ("J" * 24))
        monkeypatch.delenv("ALLOW_UPDATE_JWT_FALLBACK", raising=False)
        with pytest.raises(UpdateSecurityError, match="CLINIC_NODE_UPDATE_SECRET"):
            resolve_update_secret(allow_jwt_fallback=True)

    def test_rollback_image_tag(self, tmp_path):
        tag = tmp_path / "update-previous-backend.image"
        record_rollback_image(tag, "sha256:abc123")
        assert read_rollback_image(tag) == "sha256:abc123"


class TestScriptsPresent:
    def test_wave5_scripts_and_docs_exist(self):
        root = Path(__file__).resolve().parents[1]
        assert (root / "docs" / "DISASTER_RECOVERY_SECURITY.md").is_file()
        assert (root / "scripts" / "security" / "encrypt_backup.py").is_file()
        assert (root / "scripts" / "security" / "decrypt_backup.py").is_file()
        assert (root / "scripts" / "security" / "restore_validate.py").is_file()
        assert (root / "scripts" / "security" / "sign_update_package.py").is_file()
        assert (root / "scripts" / "security" / "apply_update.sh").is_file()
        assert (root / "scripts" / "deploy" / "validate_security_wave5.py").is_file()
