"""Add platform_owner role and user is_active flag."""

from alembic import op
import sqlalchemy as sa

revision = "20260624_0016_platform_owner"
down_revision = "20260623_0015_multi_tenant_patients"
branch_labels = None
depends_on = None

_NEW_ROLES = (
    "'patient', 'doctor', 'platform_owner', 'platform_admin', 'clinic_admin', 'admin', "
    "'receptionist', 'cashier', 'lab_technician', 'pharmacist'"
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)

    user_cols = {c["name"] for c in insp.get_columns("users")} if insp.has_table("users") else set()
    if "is_active" not in user_cols:
        if dialect == "sqlite":
            with op.batch_alter_table("users") as batch:
                batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
        else:
            op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_users_role_allowed", type_="check")
            batch.create_check_constraint("ck_users_role_allowed", f"role IN ({_NEW_ROLES})")
    else:
        op.drop_constraint("ck_users_role_allowed", "users", type_="check")
        op.create_check_constraint("ck_users_role_allowed", "users", f"role IN ({_NEW_ROLES})")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    _OLD = (
        "'patient', 'doctor', 'platform_admin', 'clinic_admin', 'admin', "
        "'receptionist', 'cashier', 'lab_technician', 'pharmacist'"
    )
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_users_role_allowed", type_="check")
            batch.create_check_constraint("ck_users_role_allowed", f"role IN ({_OLD})")
    else:
        op.drop_constraint("ck_users_role_allowed", "users", type_="check")
        op.create_check_constraint("ck_users_role_allowed", "users", f"role IN ({_OLD})")
