"""Complete ward, room, bed, placement, and turnover foundations.

Revision ID: 20260824_0035_ward_beds
Revises: 20260824_0034_staff_shifts
"""
from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op

revision = "20260824_0035_ward_beds"
down_revision = "20260824_0034_staff_shifts"
branch_labels = None
depends_on = None


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    return cleaned[:24] or "WARD"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    # Recovery tests and some legacy stamped databases intentionally contain a
    # minimal subset of the schema. Do not invent an incomplete hospitalization
    # graph when its foundational tables are absent.
    required = {"hospital_rooms", "hospital_beds", "admissions", "patient_stays", "clinics", "users"}
    if not required.issubset(tables):
        return

    if "hospital_wards" not in tables:
        op.create_table(
            "hospital_wards",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("code", sa.String(32), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("service_type", sa.String(64), nullable=False, server_default="general"),
            sa.Column("status", sa.String(24), nullable=False, server_default="active"),
            sa.Column("location", sa.String(128), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("clinic_id", "code", name="uq_hospital_wards_clinic_code"),
            sa.UniqueConstraint("clinic_id", "name", name="uq_hospital_wards_clinic_name"),
        )
        op.create_index("ix_hospital_wards_clinic_id", "hospital_wards", ["clinic_id"])
        op.create_index("ix_hospital_wards_status", "hospital_wards", ["status"])

    inspector = sa.inspect(bind)
    room_columns = _columns(inspector, "hospital_rooms")
    room_additions = {
        "ward_id": sa.Column("ward_id", sa.Integer(), sa.ForeignKey("hospital_wards.id"), nullable=True),
        "isolation_capable": sa.Column("isolation_capable", sa.Boolean(), nullable=False, server_default=sa.false()),
        "accessible": sa.Column("accessible", sa.Boolean(), nullable=False, server_default=sa.false()),
        "sex_policy": sa.Column("sex_policy", sa.String(24), nullable=False, server_default="mixed"),
    }
    for name, column in room_additions.items():
        if name not in room_columns:
            op.add_column("hospital_rooms", column)
    if "ward_id" not in room_columns:
        op.create_index("ix_hospital_rooms_ward_id", "hospital_rooms", ["ward_id"])

    # Preserve existing deployments by creating one real ward per legacy ward name.
    rows = bind.execute(sa.text("SELECT DISTINCT clinic_id, ward_name FROM hospital_rooms")).fetchall()
    used: set[tuple[int, str]] = set()
    for clinic_id, ward_name in rows:
        base = _slug(ward_name)
        code = base
        suffix = 2
        while (clinic_id, code) in used:
            code = f"{base[:27]}-{suffix}"
            suffix += 1
        used.add((clinic_id, code))
        bind.execute(
            sa.text(
                "INSERT INTO hospital_wards (clinic_id, code, name, service_type, status, created_at, updated_at) "
                "VALUES (:clinic_id, :code, :name, 'general', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"clinic_id": clinic_id, "code": code, "name": ward_name},
        )
    bind.execute(
        sa.text(
            "UPDATE hospital_rooms SET ward_id = (SELECT w.id FROM hospital_wards w "
            "WHERE w.clinic_id = hospital_rooms.clinic_id AND w.name = hospital_rooms.ward_name) "
            "WHERE ward_id IS NULL"
        )
    )
    with op.batch_alter_table("hospital_rooms") as batch:
        batch.create_unique_constraint("uq_hospital_rooms_location", ["clinic_id", "ward_name", "room_number"])

    inspector = sa.inspect(bind)
    bed_columns = _columns(inspector, "hospital_beds")
    bed_additions = {
        "stable_code": sa.Column("stable_code", sa.String(64), nullable=True),
        "accommodation_type": sa.Column("accommodation_type", sa.String(24), nullable=False, server_default="regular_bed"),
        "pediatric_suitable": sa.Column("pediatric_suitable", sa.Boolean(), nullable=False, server_default=sa.false()),
        "newborn_suitable": sa.Column("newborn_suitable", sa.Boolean(), nullable=False, server_default=sa.false()),
        "isolation_suitable": sa.Column("isolation_suitable", sa.Boolean(), nullable=False, server_default=sa.false()),
        "accessible": sa.Column("accessible", sa.Boolean(), nullable=False, server_default=sa.false()),
        "status_reason": sa.Column("status_reason", sa.Text(), nullable=True),
        "version": sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        "reserved_for_admission_id": sa.Column("reserved_for_admission_id", sa.Integer(), sa.ForeignKey("admissions.id"), nullable=True),
        "reserved_until": sa.Column("reserved_until", sa.DateTime(), nullable=True),
        "last_cleaned_at": sa.Column("last_cleaned_at", sa.DateTime(), nullable=True),
    }
    for name, column in bed_additions.items():
        if name not in bed_columns:
            op.add_column("hospital_beds", column)
    bind.execute(sa.text("UPDATE hospital_beds SET stable_code = 'BED-' || room_id || '-' || id WHERE stable_code IS NULL"))
    with op.batch_alter_table("hospital_beds") as batch:
        batch.alter_column("stable_code", existing_type=sa.String(64), nullable=False)
        batch.create_unique_constraint("uq_hospital_beds_room_number", ["room_id", "bed_number"])
        batch.create_unique_constraint("uq_hospital_beds_stable_code", ["stable_code"])
    bed_indexes = {item["name"] for item in sa.inspect(bind).get_indexes("hospital_beds")}
    if "ix_hospital_beds_stable_code" not in bed_indexes:
        op.create_index("ix_hospital_beds_stable_code", "hospital_beds", ["stable_code"])
    if "ix_hospital_beds_reserved_for_admission_id" not in bed_indexes:
        op.create_index("ix_hospital_beds_reserved_for_admission_id", "hospital_beds", ["reserved_for_admission_id"])

    admission_columns = _columns(sa.inspect(bind), "admissions")
    for name, column in {
        "expected_discharge_at": sa.Column("expected_discharge_at", sa.DateTime(), nullable=True),
        "placement_age_group": sa.Column("placement_age_group", sa.String(16), nullable=False, server_default="adult"),
        "requires_isolation": sa.Column("requires_isolation", sa.Boolean(), nullable=False, server_default=sa.false()),
        "requires_accessible": sa.Column("requires_accessible", sa.Boolean(), nullable=False, server_default=sa.false()),
    }.items():
        if name not in admission_columns:
            op.add_column("admissions", column)

    if "bed_status_events" not in tables:
        op.create_table(
            "bed_status_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("bed_id", sa.Integer(), sa.ForeignKey("hospital_beds.id"), nullable=False),
            sa.Column("admission_id", sa.Integer(), sa.ForeignKey("admissions.id"), nullable=True),
            sa.Column("from_status", sa.String(32), nullable=True),
            sa.Column("to_status", sa.String(32), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        for column in ("clinic_id", "bed_id", "admission_id", "created_at"):
            op.create_index(f"ix_bed_status_events_{column}", "bed_status_events", [column])

    # Database enforcement closes races even when two app workers allocate simultaneously.
    stay_indexes = {item["name"] for item in sa.inspect(bind).get_indexes("patient_stays")}
    if "uq_patient_stays_current_bed" not in stay_indexes:
        op.create_index(
            "uq_patient_stays_current_bed", "patient_stays", ["bed_id"], unique=True,
            postgresql_where=sa.text("is_current = true"), sqlite_where=sa.text("is_current = 1"),
        )
    if "uq_patient_stays_current_admission" not in stay_indexes:
        op.create_index(
            "uq_patient_stays_current_admission", "patient_stays", ["admission_id"], unique=True,
            postgresql_where=sa.text("is_current = true"), sqlite_where=sa.text("is_current = 1"),
        )


def downgrade() -> None:
    op.drop_index("uq_patient_stays_current_admission", table_name="patient_stays")
    op.drop_index("uq_patient_stays_current_bed", table_name="patient_stays")
    op.drop_table("bed_status_events")
    for name in ("requires_accessible", "requires_isolation", "placement_age_group", "expected_discharge_at"):
        op.drop_column("admissions", name)
    with op.batch_alter_table("hospital_beds") as batch:
        batch.drop_constraint("uq_hospital_beds_stable_code", type_="unique")
        batch.drop_constraint("uq_hospital_beds_room_number", type_="unique")
    for name in (
        "last_cleaned_at", "reserved_until", "reserved_for_admission_id", "version", "status_reason",
        "accessible", "isolation_suitable", "newborn_suitable", "pediatric_suitable", "accommodation_type", "stable_code",
    ):
        op.drop_column("hospital_beds", name)
    with op.batch_alter_table("hospital_rooms") as batch:
        batch.drop_constraint("uq_hospital_rooms_location", type_="unique")
    for name in ("sex_policy", "accessible", "isolation_capable", "ward_id"):
        op.drop_column("hospital_rooms", name)
    op.drop_table("hospital_wards")
