"""initial schema: enable pgvector + create core tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-21
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector must exist before the accounts.embedding column is created
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create all tables declared on the models' metadata
    from app import models  # noqa: F401  (registers tables)
    from app.db import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app import models  # noqa: F401
    from app.db import Base

    Base.metadata.drop_all(bind=op.get_bind())
    op.execute("DROP EXTENSION IF EXISTS vector")
