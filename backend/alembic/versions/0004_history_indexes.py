"""performance indexes for 39-day historical context retrieval

Revision ID: 0004_history_indexes
Revises: 0003_case_vectors
Create Date: 2026-09-22

The fraud pipeline retrieves ONE customer's prior-39-day history on the 40th day.
A composite (account_id, event_time DESC) index makes that a single indexed range
scan per account instead of a full-table scan, and keeps the lookup + detail
endpoints fast at 1,000 accounts x ~52k transactions.
"""

from alembic import op

revision = "0004_history_indexes"
down_revision = "0003_case_vectors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # per-customer chronological history (the 39-day context query)
    op.create_index(
        "ix_txn_account_time",
        "transactions",
        ["account_id", "event_time"],
        unique=False,
        postgresql_using="btree",
    )
    # fraud-account list: group alerts by account, newest first
    op.create_index(
        "ix_alert_account_created",
        "fraud_alerts",
        ["account_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_alert_account_created", table_name="fraud_alerts")
    op.drop_index("ix_txn_account_time", table_name="transactions")
