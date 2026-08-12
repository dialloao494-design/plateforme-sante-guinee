"""Schema startup authority — Alembic-only in deployed/Railway environments."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_alembic_only_schema_false_in_local_dev(monkeypatch):
    import main
    from core.settings import get_settings

    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    assert main._alembic_only_schema() is False


def test_alembic_only_schema_true_for_production(monkeypatch):
    import main
    from core.settings import get_settings

    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    assert main._alembic_only_schema() is True


def test_alembic_only_schema_true_for_railway_without_environment(monkeypatch):
    import main
    from core.settings import get_settings

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    get_settings.cache_clear()
    assert main._alembic_only_schema() is True


def test_run_schema_startup_skips_create_all_when_alembic_only():
    import main

    create_all = MagicMock()
    fake_base = MagicMock()
    fake_base.metadata.create_all = create_all
    fake_engine = MagicMock()
    fake_session = MagicMock()

    with (
        patch.object(main, "_alembic_only_schema", return_value=True),
        patch("database.engine", fake_engine),
        patch("database.Base", fake_base),
        patch("database.SessionLocal", return_value=fake_session),
        patch("database_migrations.run_alembic_upgrade_head") as alembic_upgrade,
        patch("services.user_provisioning.bootstrap_platform_owner"),
        patch("services.user_provisioning.bootstrap_initial_admin"),
        patch("sqlalchemy.inspect") as inspect_mock,
    ):
        inspector = MagicMock()
        inspector.get_table_names.return_value = [
            "users",
            "clinics",
            "patients",
            "doctors",
            "rendezvous",
            "messages",
            "clinical_visits",
            "invoices",
            "clinical_audit_logs",
        ]
        inspector.get_columns.side_effect = lambda table: {
            "users": [
                {"name": "role"},
                {"name": "clinic_id"},
                {"name": "session_version"},
                {"name": "token_version"},
                {"name": "must_change_password"},
            ],
            "patients": [
                {"name": "clinic_id"},
                {"name": "user_id"},
                {"name": "is_archived"},
                {"name": "patient_number"},
            ],
            "rendezvous": [
                {"name": "clinic_id"},
                {"name": "patient_id"},
                {"name": "doctor_id"},
                {"name": "status"},
            ],
        }[table]
        inspect_mock.return_value = inspector

        main._run_schema_and_seed_startup()

    create_all.assert_not_called()
    alembic_upgrade.assert_called_once_with(fail_closed=True)
