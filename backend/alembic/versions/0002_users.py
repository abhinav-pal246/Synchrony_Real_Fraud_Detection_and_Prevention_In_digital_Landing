"""create users table (analyst login credential)

Revision ID: 0002_users
Revises: 0001_initial
Create Date: 2026-09-22
"""

from alembic import op

revision = "0002_users"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app import models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # creates the new users table (idempotent)


def downgrade() -> None:
    op.drop_table("users")
