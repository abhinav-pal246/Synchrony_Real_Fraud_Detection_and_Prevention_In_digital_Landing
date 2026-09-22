"""
Synchrony Analytics API — bootstrap application.

Phase: project initialization only. No fraud-detection logic yet.
This file exists to prove the Docker plumbing works end to end:
  - the API starts,
  - and it can reach Postgres, Redis, and Kafka.
"""

import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import analytics
from .agents import FraudOrchestrator
from .db import engine
from .embeddings import embeddings_ready, similar_cases
from .explain import explain as ai_explain
from .schemas import LoginIn, TokenOut, TransactionIn
from .scoring import models_ready, score_transaction
from .security import authenticate, create_access_token, get_current_user

_orchestrator = FraudOrchestrator()

# ── Connection config (defaults match docker-compose service names) ──
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://synchrony:synchrony@postgres:5432/synchrony"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")

app = FastAPI(title="Synchrony Analytics API", version="0.1.0")

# Allow the local React dev server to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "synchrony-analytics-api",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    """Liveness probe — does not touch any dependency."""
    return {"status": "ok"}


# ── Dependency connectivity checks (proves the stack is wired) ──
def _check_postgres() -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()


def _check_redis() -> None:
    import redis

    client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=5)
    if not client.ping():
        raise RuntimeError("PING returned falsy response")


def _check_kafka() -> None:
    from confluent_kafka.admin import AdminClient

    admin = AdminClient({"bootstrap.servers": KAFKA_BOOTSTRAP})
    admin.list_topics(timeout=5)


@app.get("/health/deps")
def health_deps():
    """Readiness probe — checks Postgres, Redis, and Kafka connectivity."""
    checks = (("postgres", _check_postgres), ("redis", _check_redis), ("kafka", _check_kafka))
    services = {}
    overall_ok = True

    for name, check in checks:
        try:
            check()
            services[name] = {"status": "ok"}
        except Exception as exc:  # noqa: BLE001 - report any failure per-service
            services[name] = {"status": "error", "detail": str(exc)[:200]}
            overall_ok = False

    return {"status": "ok" if overall_ok else "degraded", "services": services}


@app.get("/health/db")
def health_db():
    """Proves the schema exists: pgvector enabled + core tables present."""
    tables = {}
    with engine.connect() as conn:
        try:
            ext = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            pgvector_enabled = ext == 1
        except Exception:  # noqa: BLE001
            pgvector_enabled = False

        for table in ("accounts", "transactions", "fraud_alerts"):
            try:
                rows = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                tables[table] = {"exists": True, "rows": rows}
            except Exception as exc:  # noqa: BLE001
                tables[table] = {"exists": False, "detail": str(exc)[:120]}

    all_ok = pgvector_enabled and all(t["exists"] for t in tables.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "pgvector_enabled": pgvector_enabled,
        "tables": tables,
    }


# ─────────────────────────── Security layer ───────────────────────────
@app.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn):
    """Authenticate the analyst and return a JWT (bcrypt-verified, no plaintext stored)."""
    if not authenticate(body.email, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return TokenOut(access_token=create_access_token(body.email))


# ─────────────────────────── AI / ML layer ───────────────────────────
@app.get("/ml/status")
def ml_status():
    return {"models_ready": models_ready(), "model": "RandomForest+IsolationForest"}


@app.post("/score")
def score(txn: TransactionIn, user: str = Depends(get_current_user)):
    """Score a transaction with the local ML models (JWT-protected)."""
    if not models_ready():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Models not trained yet")
    return {"scored_by": user, **score_transaction(txn.model_dump())}


@app.post("/explain")
def explain_alert(txn: TransactionIn, user: str = Depends(get_current_user)):
    """Score + generate a human-readable reason (Bedrock, with template fallback)."""
    if not models_ready():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Models not trained yet")
    data = txn.model_dump()
    result = score_transaction(data)
    result["explanation"] = ai_explain(data, result)
    return result


@app.post("/investigate")
def investigate(txn: TransactionIn, user: str = Depends(get_current_user)):
    """Run the multi-agent fraud orchestrator (rule + ML + velocity + graph + vector + LLM)."""
    if not models_ready():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Models not trained yet")
    return {"analyst": user, **_orchestrator.run(txn.model_dump())}


@app.post("/similar")
def similar(txn: TransactionIn, user: str = Depends(get_current_user), k: int = 8):
    """Vector search: retrieve the k most similar historical cases (pgvector)."""
    if not embeddings_ready():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Vector store not built yet")
    return {"query_by": user, "k": k, "similar_cases": similar_cases(txn.model_dump(), k=k)}


# ─────────────────────── Investigation layer (Postgres history) ───────────────────────
import re

_ACCT_RE = re.compile(r"^ACC-\d{6}$")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                      r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


@app.get("/overview")
def overview(user: str = Depends(get_current_user)):
    """Real KPIs + fraud distributions computed from the Postgres history store."""
    return analytics.overview()


@app.get("/accounts/fraud")
def accounts_fraud(user: str = Depends(get_current_user)):
    """The detected-fraudulent-account list (one entry per account, aggregated)."""
    return {"accounts": analytics.fraud_accounts()}


@app.get("/accounts/{account_id}")
def account_detail(account_id: str, user: str = Depends(get_current_user)):
    """Why an account was flagged + its 39-day historical context."""
    if not _ACCT_RE.match(account_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "account_id must look like ACC-000123")
    detail = analytics.account_detail(account_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No account {account_id}")
    return detail


@app.get("/lookup")
def lookup(
    account_id: str | None = None,
    transaction_id: str | None = None,
    user: str = Depends(get_current_user),
):
    """Manual investigation by primary key — accounts.account_id OR transactions.transaction_id."""
    if not account_id and not transaction_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Provide a primary key: account_id or transaction_id")
    if account_id and not _ACCT_RE.match(account_id.strip()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "account_id must look like ACC-000123")
    if transaction_id and not _UUID_RE.match(transaction_id.strip()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "transaction_id must be a UUID")
    result = analytics.lookup(account_id=account_id, transaction_id=transaction_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No matching account or transaction")
    return result


@app.get("/vector/status")
def vector_status():
    ready = embeddings_ready()
    count = 0
    if ready:
        try:
            with engine.connect() as conn:
                count = conn.execute(text("SELECT count(*) FROM case_vectors")).scalar() or 0
        except Exception:
            count = 0
    return {"embeddings_ready": ready, "case_vectors": count}
