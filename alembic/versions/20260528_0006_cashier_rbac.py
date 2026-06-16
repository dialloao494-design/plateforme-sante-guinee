"""Add cashier role and production RBAC role constraint."""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0006_cashier_rbac"
down_revision = "20260527_0005_clinic_billing_audit"
branch_labels = None
depends_on = None

_NEW_ROLES = (
    "'patient', 'doctor', 'platform_admin', 'clinic_admin', 'admin', "
    "'receptionist', 'cashier', 'lab_technician', 'pharmacist'"
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_users_role_allowed", type_="check")
            batch.create_check_constraint(
                "ck_users_role_allowed",
                f"role IN ({_NEW_ROLES})",
            )
    else:
        op.drop_constraint("ck_users_role_allowed", "users", type_="check")
        op.create_check_constraint(
            "ck_users_role_allowed",
            "users",
            f"role IN ({_NEW_ROLES})",
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    _OLD_ROLES = (
        "'patient', 'doctor', 'admin', "
        "'receptionist', 'lab_technician', 'pharmacist'"
    )
    if dialect == "sqlite":
        op.execute(
            "UPDATE users SET role = 'receptionist' WHERE role = 'cashier'"
        )
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_users_role_allowed", type_="check")
            batch.create_check_constraint(
                "ck_users_role_allowed",
                f"role IN ({_OLD_ROLES})",
            )
    else:
        op.execute(
            "UPDATE users SET role = 'receptionist' WHERE role = 'cashier'"
        )
        op.drop_constraint("ck_users_role_allowed", "users", type_="check")
        op.create_check_constraint(
            "ck_users_role_allowed",
            "users",
            f"role IN ({_OLD_ROLES})",
        )
