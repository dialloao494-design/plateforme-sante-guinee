"""Add email_verified_at and email_verification_tokens.

Idempotent for production DBs where columns/tables already exist.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260627_0019_email_verification"
down_revision = "20260626_0018_visit_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    user_cols = (
        {c["name"] for c in insp.get_columns("users")} if "users" in insp.get_table_names() else set()
    )
    if "email_verified_at" not in user_cols:
        op.add_column(
            "users",
            sa.Column("email_verified_at", sa.DateTime(), nullable=True),
        )

    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "email_verification_tokens" not in tables:
        op.create_table(
            "email_verification_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        insp = sa.inspect(bind)

    if "email_verification_tokens" in set(insp.get_table_names()):
        existing = {idx["name"] for idx in insp.get_indexes("email_verification_tokens")}
        if "ix_email_verification_tokens_token_hash" not in existing:
            op.create_index(
                "ix_email_verification_tokens_token_hash",
                "email_verification_tokens",
                ["token_hash"],
                unique=True,
            )
        if "ix_email_verification_tokens_user_id" not in existing:
            op.create_index(
                "ix_email_verification_tokens_user_id",
                "email_verification_tokens",
                ["user_id"],
                unique=False,
            )

    # Existing accounts treated as verified (avoid lockout on deploy)
    op.execute(
        sa.text(
            "UPDATE users SET email_verified_at = CURRENT_TIMESTAMP "
            "WHERE email_verified_at IS NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "email_verification_tokens" in tables:
        existing = {idx["name"] for idx in insp.get_indexes("email_verification_tokens")}
        if "ix_email_verification_tokens_user_id" in existing:
            op.drop_index(
                "ix_email_verification_tokens_user_id",
                table_name="email_verification_tokens",
            )
        if "ix_email_verification_tokens_token_hash" in existing:
            op.drop_index(
                "ix_email_verification_tokens_token_hash",
                table_name="email_verification_tokens",
            )
        op.drop_table("email_verification_tokens")
    user_cols = (
        {c["name"] for c in insp.get_columns("users")} if "users" in insp.get_table_names() else set()
    )
    if "email_verified_at" in user_cols:
        op.drop_column("users", "email_verified_at")
