"""
SQLAlchemy models — core data layer.

Maps the briefing's data tiers to tables:
  - Account       → Tier T2 (account data) + PII used for graph linking (T6)
  - Transaction   → Tier T1 (the Kafka `raw-transactions` payload, §7b)
  - FraudAlert    → scored alerts produced by the detection pipeline

No fraud logic here — this is the persistence schema only.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .db import Base
from .ml_features import FEATURE_ORDER

EMBEDDING_DIM = len(FEATURE_ORDER)  # behavioral embedding dimension


class Account(Base):
    """A customer credit account (Tier T2)."""

    __tablename__ = "accounts"

    account_id = Column(String, primary_key=True)
    masked_pan = Column(String)
    product_type = Column(String, index=True)  # private_label, co_branded, carecredit, ...

    # PII — synthetic; used later for fraud-ring graph linking (Tier T6)
    holder_name = Column(String)
    email = Column(String, index=True)
    phone = Column(String, index=True)
    device_fingerprint = Column(String, index=True)
    home_street = Column(String)
    home_city = Column(String)
    home_state = Column(String)
    home_zip = Column(String, index=True)

    # Account financials / status (Tier T2)
    balance = Column(Numeric(14, 2), default=0)
    credit_limit = Column(Numeric(14, 2), default=0)
    account_age_days = Column(Integer, default=0)
    promo_plan_id = Column(String, nullable=True)
    promo_plan_type = Column(String, nullable=True)
    days_past_due = Column(Integer, default=0)
    status = Column(String, default="active", index=True)  # active, frozen, closed

    # Graph / semantic embedding (pgvector) — populated in a later phase
    embedding = Column(Vector(64), nullable=True)

    opened_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Transaction(Base):
    """A transaction event — the full `raw-transactions` payload (Tier T1, §7b)."""

    __tablename__ = "transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String, ForeignKey("accounts.account_id"), index=True)
    masked_pan = Column(String)
    event_time = Column(DateTime(timezone=True), index=True)

    amount = Column(Numeric(14, 2))
    currency = Column(String, default="USD")

    merchant_id = Column(String, index=True)
    merchant_name = Column(String)
    merchant_category_code = Column(String, index=True)  # MCC
    terminal_id = Column(String, nullable=True)

    transaction_type = Column(String)  # purchase, refund, cash_advance, auth_only, void
    channel = Column(String, index=True)  # in_store, online, mobile_app, phone, digital_wallet
    entry_method = Column(String)  # chip, contactless, swipe, manual, cnp, token
    card_present = Column(Boolean, default=False)

    cvv_result = Column(String, nullable=True)  # match, no_match, not_provided
    avs_result = Column(String, nullable=True)  # full, zip_only, no_match, not_provided
    three_ds_result = Column(String, nullable=True)  # authenticated, attempted, failed, not_enrolled

    status = Column(String, index=True)  # approved, declined, partial
    decline_reason_code = Column(String, nullable=True)

    ip_address = Column(String, nullable=True, index=True)
    device_fingerprint = Column(String, nullable=True, index=True)
    user_agent = Column(String, nullable=True)
    session_id = Column(String, nullable=True)

    shipping_address = Column(JSONB, nullable=True)
    shipping_name = Column(String, nullable=True)
    billing_address = Column(JSONB, nullable=True)
    expedited_shipping = Column(Boolean, default=False)

    token_id = Column(String, nullable=True)
    wallet_provider = Column(String, nullable=True)  # apple, google, samsung
    token_provisioning_date = Column(DateTime(timezone=True), nullable=True)

    promo_plan_id = Column(String, nullable=True)
    installment_loan_id = Column(String, nullable=True)
    associate_id = Column(String, nullable=True)
    store_id = Column(String, nullable=True)
    refund_original_txn_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FraudAlert(Base):
    """A scored fraud alert produced by the detection pipeline."""

    __tablename__ = "fraud_alerts"

    alert_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(
        UUID(as_uuid=True), ForeignKey("transactions.transaction_id"), nullable=True, index=True
    )
    account_id = Column(String, ForeignKey("accounts.account_id"), index=True)

    vector_id = Column(String, index=True)  # fraud vector code, e.g. EC-1, APP-2
    actor_code = Column(String, index=True)  # B, 3P, S, M
    risk_score = Column(Integer)  # 0-100
    severity = Column(String, index=True)  # critical, high, medium, low
    status = Column(String, default="open", index=True)  # open, reviewing, confirmed, dismissed
    detection_method = Column(String)  # rule_engine, ml_model, graph
    reason = Column(Text, nullable=True)  # human-readable explanation (Bedrock, later)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class User(Base):
    """Analyst login credential — bcrypt-hashed, stored in Postgres (not in code/.env)."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CaseVector(Base):
    """
    Vector store (pgvector) of historical transactions as behavioral embeddings,
    with their ground-truth labels. Powers similarity search: kNN fraud detection
    and retrieval-augmented explanations.
    """

    __tablename__ = "case_vectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String, index=True)
    embedding = Column(Vector(EMBEDDING_DIM))
    is_fraud = Column(Boolean, default=False, index=True)
    fraud_vector = Column(String, nullable=True)
    actor = Column(String, nullable=True)
    amount = Column(Numeric(14, 2))
    mcc = Column(String)
    channel = Column(String)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
