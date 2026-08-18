"""Regression guard for schema configuration supported by Pydantic 3."""

from pathlib import Path


def test_schemas_use_pydantic_config_dict():
    schema_root = Path(__file__).resolve().parents[1] / "schemas"
    offenders = []
    for path in schema_root.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "orm_mode" in source or "class Config:" in source:
            offenders.append(path.name)
    assert offenders == []
