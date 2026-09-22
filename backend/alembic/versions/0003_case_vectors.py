"""create case_vectors table (pgvector case library)

Revision ID: 0003_case_vectors
Revises: 0002_users
Create Date: 2026-09-22
"""

from alembic import op

revision = "0003_case_vectors"
down_revision = "0002_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app import models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())  # creates case_vectors (idempotent)


def downgrade() -> None:
    op.drop_table("case_vectors")
