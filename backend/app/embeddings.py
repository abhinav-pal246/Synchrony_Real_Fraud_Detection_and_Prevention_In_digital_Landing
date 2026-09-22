"""
Behavioral embeddings + pgvector similarity search.

An embedding is the account-normalized feature vector of a transaction (fit with a
StandardScaler so L2 distance reflects behavioral similarity). We store labeled
historical embeddings in `case_vectors` and query nearest neighbours for:
  - kNN fraud detection (VectorSimilarityAgent), and
  - retrieval-augmented explanations (RAG for the LLM investigator).
"""

import functools
from pathlib import Path

import joblib
from sqlalchemy import text

from .db import engine
from .ml_features import build_features
from .scoring import account_stats

ART = Path(__file__).resolve().parent.parent / "ml" / "artifacts"


@functools.lru_cache(maxsize=1)
def _scaler():
    return joblib.load(ART / "scaler.joblib")


def embeddings_ready() -> bool:
    return (ART / "scaler.joblib").exists()


def embed(txn: dict):
    """Return the normalized behavioral embedding for a transaction."""
    feats = build_features(txn, account_stats(txn.get("account_id")))
    vec = _scaler().transform([feats])[0]
    return [round(float(x), 6) for x in vec]


def _vector_literal(vec) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def similar_cases(txn: dict, k: int = 8):
    """Top-k nearest historical cases (by L2 distance in embedding space)."""
    try:
        vec = embed(txn)
    except Exception:
        return []  # scaler/case library not built yet → graceful
    lit = _vector_literal(vec)
    sql = text(
        "SELECT transaction_id, is_fraud, fraud_vector, actor, "
        "amount, mcc, channel, summary, "
        f"round((embedding <-> '{lit}'::vector)::numeric, 4) AS distance "
        "FROM case_vectors "
        f"ORDER BY embedding <-> '{lit}'::vector LIMIT :k"
    )
    try:
        with engine.connect() as conn:
            return [dict(r) for r in conn.execute(sql, {"k": k}).mappings()]
    except Exception:
        return []
