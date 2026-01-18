"""add profile fields sessions and password reset

Revision ID: e56e7137342b
Revises: ab3249b83db3
Create Date: 2026-01-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "e56e7137342b"
down_revision: Union[str, None] = "ab3249b83db3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------- helpers (MySQL) ----------
def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    q = text(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name = :t
        """
    )
    return bind.execute(q, {"t": table_name}).scalar() > 0


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    q = text(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = :t
          AND column_name = :c
        """
    )
    return bind.execute(q, {"t": table_name, "c": column_name}).scalar() > 0


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    q = text(
        """
        SELECT COUNT(*)
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = :t
          AND index_name = :i
        """
    )
    return bind.execute(q, {"t": table_name, "i": index_name}).scalar() > 0


# ---------- migration ----------
def upgrade() -> None:
    # --- users: add profile fields + updated_at safely ---
    with op.batch_alter_table("users") as batch_op:
        if not _column_exists("users", "full_name"):
            batch_op.add_column(sa.Column("full_name", sa.String(length=255), nullable=True))

        if not _column_exists("users", "phone"):
            batch_op.add_column(sa.Column("phone", sa.String(length=50), nullable=True))

        if not _column_exists("users", "updated_at"):
            # NOTE: MySQL default timestamp
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )
            )

    # --- refresh_tokens: add session + telemetry safely ---
    with op.batch_alter_table("refresh_tokens") as batch_op:
        if not _column_exists("refresh_tokens", "session_id"):
            batch_op.add_column(sa.Column("session_id", sa.String(length=64), nullable=False, server_default=""))

        if not _column_exists("refresh_tokens", "last_used_at"):
            batch_op.add_column(sa.Column("last_used_at", sa.DateTime(), nullable=True))

        if not _column_exists("refresh_tokens", "user_agent"):
            batch_op.add_column(sa.Column("user_agent", sa.String(length=255), nullable=True))

        if not _column_exists("refresh_tokens", "ip"):
            batch_op.add_column(sa.Column("ip", sa.String(length=64), nullable=True))

    # index for session_id (create outside batch so we can safely check existence)
    if not _index_exists("refresh_tokens", "ix_refresh_tokens_session_id"):
        op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"], unique=False)

    # --- password_reset_tokens table + indexes safely ---
    if not _table_exists("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )

    # indexes (create only if missing)
    if not _index_exists("password_reset_tokens", "ix_password_reset_tokens_user_id"):
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"], unique=False)

    if not _index_exists("password_reset_tokens", "ux_password_reset_tokens_token_hash"):
        op.create_index("ux_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    # Downgrade in drifted DBs is tricky; do best-effort & safe checks

    if _table_exists("password_reset_tokens"):
        if _index_exists("password_reset_tokens", "ux_password_reset_tokens_token_hash"):
            op.drop_index("ux_password_reset_tokens_token_hash", table_name="password_reset_tokens")
        if _index_exists("password_reset_tokens", "ix_password_reset_tokens_user_id"):
            op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
        op.drop_table("password_reset_tokens")

    if _index_exists("refresh_tokens", "ix_refresh_tokens_session_id"):
        op.drop_index("ix_refresh_tokens_session_id", table_name="refresh_tokens")

    with op.batch_alter_table("refresh_tokens") as batch_op:
        if _column_exists("refresh_tokens", "ip"):
            batch_op.drop_column("ip")
        if _column_exists("refresh_tokens", "user_agent"):
            batch_op.drop_column("user_agent")
        if _column_exists("refresh_tokens", "last_used_at"):
            batch_op.drop_column("last_used_at")
        if _column_exists("refresh_tokens", "session_id"):
            batch_op.drop_column("session_id")

    with op.batch_alter_table("users") as batch_op:
        if _column_exists("users", "updated_at"):
            batch_op.drop_column("updated_at")
        if _column_exists("users", "phone"):
            batch_op.drop_column("phone")
        if _column_exists("users", "full_name"):
            batch_op.drop_column("full_name")
