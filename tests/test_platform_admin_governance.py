"""Regression gates for unified platform/clinic administration controls."""

from __future__ import annotations

from datetime import datetime

import models
from core.provisioning_context import provisioning_channel
from services.auth_session_service import issue_refresh_token
from services.user_provisioning import create_staff_user


def _clinic_with_admin(db, suffix: str):
    clinic = models.Clinic(name=f"Governance Clinic {suffix}", city="Conakry", is_active=True)
    db.add(clinic); db.flush()
    with provisioning_channel("test_fixture"):
        admin = create_staff_user(
            db, email=f"governance.admin.{suffix}@real.gn", password="AdminPass12!",
            role="clinic_admin", clinic_id=clinic.id, channel="test_fixture",
        ).user
    db.commit()
    return clinic, admin


def test_platform_account_inventory_classifies_clinic_bound_test_accounts(client, db_session, admin_headers):
    clinic, _ = _clinic_with_admin(db_session, "classify")
    with provisioning_channel("test_fixture"):
        probe = create_staff_user(
            db_session, email="field.verify.receptionist@aasma-clinic.gn", password="ProbePass12!",
            role="receptionist", clinic_id=clinic.id, channel="test_fixture",
        ).user
    db_session.commit()
    response = client.get("/platform/accounts", params={"category": "test"}, headers=admin_headers)
    assert response.status_code == 200, response.text
    row = next(item for item in response.json() if item["id"] == probe.id)
    assert row["category"] == "test"
    assert row["clinic_id"] == clinic.id
    assert row["created_at"] is not None


def test_platform_lifecycle_revokes_sessions_membership_and_audits_reason(client, db_session, admin_headers):
    clinic, _ = _clinic_with_admin(db_session, "lifecycle")
    with provisioning_channel("test_fixture"):
        nurse = create_staff_user(
            db_session, email="governance.nurse@real.gn", password="NursePass12!",
            role="nurse", clinic_id=clinic.id, channel="test_fixture",
        ).user
    db_session.commit(); issue_refresh_token(db_session, user=nurse)
    response = client.patch(
        f"/platform/clinics/{clinic.id}/staff/{nurse.id}/deactivate",
        json={"reason": "Fin de contrat vérifiée"}, headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    db_session.expire_all()
    assert db_session.get(models.User, nurse.id).is_active is False
    assert db_session.query(models.ClinicStaff).filter_by(clinic_id=clinic.id, user_id=nurse.id).one().is_active is False
    from models.refresh_token import RefreshToken
    assert db_session.query(RefreshToken).filter_by(user_id=nurse.id, revoked_at=None).count() == 0
    audit = db_session.query(models.ClinicalAuditLog).filter_by(resource_type="staff", resource_id=nurse.id, action="deactivate").order_by(models.ClinicalAuditLog.id.desc()).first()
    assert audit.reason == "Fin de contrat vérifiée"
    assert '"is_active": true' in audit.before_json
    assert '"is_active": false' in audit.after_json


def test_platform_lifecycle_preserves_last_clinic_admin(client, db_session, admin_headers):
    clinic, only_admin = _clinic_with_admin(db_session, "last-admin")
    response = client.patch(
        f"/platform/clinics/{clinic.id}/staff/{only_admin.id}/deactivate",
        json={"reason": "Test du garde-fou"}, headers=admin_headers,
    )
    assert response.status_code == 409
    assert db_session.get(models.User, only_admin.id).is_active is True


def test_clinic_configuration_state_health_and_audit_exports(client, db_session, admin_headers):
    clinic, _ = _clinic_with_admin(db_session, "control-room")
    config = client.patch(
        f"/platform/clinics/{clinic.id}/configuration",
        json={"payment_methods": ["cash"], "enabled_modules": ["reception", "billing"], "offline_workstations_enabled": False, "data_retention_days": 365},
        headers=admin_headers,
    )
    assert config.status_code == 200, config.text
    assert config.json()["configuration"]["payment_methods"] == ["cash"]

    health = client.get(f"/platform/clinics/{clinic.id}/health", headers=admin_headers)
    assert health.status_code == 200, health.text
    assert health.json()["database"] == "connected"
    assert set(health.json()["sync"]) >= {"pending", "dead", "conflicts"}

    suspended = client.post(
        f"/platform/clinics/{clinic.id}/state",
        json={"action": "suspend", "reason": "Maintenance planifiée du site", "confirmation": clinic.name},
        headers=admin_headers,
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["is_active"] is False

    csv_export = client.get(f"/platform/audit-logs/export.csv?clinic_id={clinic.id}", headers=admin_headers)
    pdf_export = client.get(f"/platform/audit-logs/export.pdf?clinic_id={clinic.id}", headers=admin_headers)
    assert csv_export.status_code == 200 and "reason" in csv_export.text
    assert pdf_export.status_code == 200 and pdf_export.content.startswith(b"%PDF")


def test_data_governance_requires_backup_or_explicit_waiver(client, db_session, admin_headers):
    clinic, _ = _clinic_with_admin(db_session, "reset-gate")
    inventory = client.get(f"/platform/clinics/{clinic.id}/data-governance", headers=admin_headers)
    assert inventory.status_code == 200
    assert "counts" in inventory.json() and "duplicate_candidates" in inventory.json()
    blocked = client.post(
        f"/platform/clinics/{clinic.id}/data-reset",
        json={"confirmation": clinic.name, "reason": "Préparation contrôlée du démarrage clinique", "acknowledge_irreversible": True, "waive_backup": False},
        headers=admin_headers,
    )
    assert blocked.status_code == 409
    assert "sauvegarde" in blocked.json()["detail"].lower()
