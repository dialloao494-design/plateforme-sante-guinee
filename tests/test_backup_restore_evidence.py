"""Safety and artifact checks for the backup/restore evidence runner."""

from __future__ import annotations

import gzip
import importlib.util
import os
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "db" / "backup_restore_evidence.py"
SPEC = importlib.util.spec_from_file_location("backup_restore_evidence", MODULE_PATH)
backup_evidence = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(backup_evidence)


def write_dump(path: Path) -> None:
    sql = "-- PostgreSQL database dump\nCREATE TABLE patients (id integer);\n" + "".join(
        f"INSERT INTO patients VALUES ({index}); -- fixture-{index:04d}\n" for index in range(300)
    )
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        stream.write(sql)


def test_inspect_backup_produces_checksum_and_rpo_evidence(tmp_path):
    backup = tmp_path / "clinic.sql.gz"
    write_dump(backup)

    report = backup_evidence.inspect_backup(backup, rpo_target_minutes=60)

    assert len(report["sha256"]) == 64
    assert report["gzip_integrity"] is True
    assert report["sql_signature"] is True
    assert report["expanded_bytes"] > report["compressed_bytes"]
    assert report["rpo_met"] is True


def test_inspect_backup_reports_missed_rpo_without_hiding_valid_archive(tmp_path):
    backup = tmp_path / "old.sql.gz"
    write_dump(backup)
    old = time.time() - 7200
    os.utime(backup, (old, old))

    report = backup_evidence.inspect_backup(backup, rpo_target_minutes=30)

    assert report["gzip_integrity"] is True
    assert report["rpo_met"] is False
    assert report["rpo_seconds"] >= 7100


def test_inspect_backup_rejects_corrupt_or_non_sql_archives(tmp_path):
    corrupt = tmp_path / "corrupt.sql.gz"
    corrupt.write_bytes(b"not gzip" * 100)
    with pytest.raises(ValueError, match="gzip integrity"):
        backup_evidence.inspect_backup(corrupt, rpo_target_minutes=60)

    unknown = tmp_path / "unknown.sql.gz"
    with gzip.open(unknown, "wb") as stream:
        stream.write(os.urandom(1000))
    with pytest.raises(ValueError, match="recognizable PostgreSQL"):
        backup_evidence.inspect_backup(unknown, rpo_target_minutes=60)


def test_restore_target_must_be_distinct_and_explicitly_isolated():
    source = "postgresql://user:secret@db.example/sante"
    target = "postgresql://user:secret@db.example/sante_restore_verify"
    assert backup_evidence.validate_isolated_target(source, target) == "sante_restore_verify"

    with pytest.raises(ValueError, match="must end"):
        backup_evidence.validate_isolated_target(source, "postgresql://db/sante_copy")
    with pytest.raises(ValueError, match="must differ"):
        backup_evidence.validate_isolated_target(
            "postgresql://db/sante_restore_verify",
            "postgresql://db/sante_restore_verify",
        )
    with pytest.raises(ValueError, match="System databases"):
        backup_evidence.validate_isolated_target(None, "postgresql://db/postgres")
