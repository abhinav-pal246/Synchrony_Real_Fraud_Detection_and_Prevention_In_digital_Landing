"""
Investigation queries over the PostgreSQL history store.

These power the analyst dashboard:
  - overview()              : real KPIs + fraud distributions
  - fraud_accounts()        : the detected-fraudulent-account list
  - account_detail(id)      : why an account was flagged + its 39-day context
  - lookup(pk)              : manual investigation by primary key

The 40th day (2026-09-22) is "current"; the prior 39 days are the historical
context. Retrieval is per-account and index-backed (ix_txn_account_time) — we
never scan the whole table, and never hand the full DB to the model.
"""

from datetime import datetime, timezone

from sqlalchemy import text

from .db import engine
from .scoring import detect_signals, score_transaction, models_ready

DAY40 = datetime(2026, 9, 22, tzinfo=timezone.utc)  # the detection day

ACTOR_LABEL = {
    "B": "First-party (cardholder)",
    "3P": "Third-party fraudster",
    "S": "Synthetic / ring",
    "M": "Merchant / associate",
}


def _severity(risk_100: int) -> str:
    if risk_100 >= 85:
        return "critical"
    if risk_100 >= 60:
        return "high"
    if risk_100 >= 40:
        return "medium"
    return "low"


def _txn_dict(row) -> dict:
    """Shape a transactions row into the dict the ML/rule layer expects."""
    return {
        "account_id": row["account_id"],
        "amount": float(row["amount"] or 0),
        "event_time": row["event_time"].isoformat() if row["event_time"] else "",
        "channel": row["channel"],
        "entry_method": row["entry_method"],
        "mcc": row["merchant_category_code"],
        "cvv_result": row["cvv_result"],
        "avs_result": row["avs_result"],
        "status": row["status"],
        "card_present": row["card_present"],
        "promo_financing": bool(row["promo_plan_id"]),
        "gift_card_amount": 0,
    }


def _live_score(txn: dict) -> dict:
    """Recompute the ML decision + indicators on demand (for evidence panels)."""
    signals = detect_signals(txn)
    out = {"signals": signals, "likely_vectors": []}
    if models_ready():
        try:
            s = score_transaction(txn)
            out.update({
                "risk_score": s["risk_score"],
                "fraud_probability": s["fraud_probability"],
                "anomaly_score": s["anomaly_score"],
                "likely_vectors": s["likely_vectors"],
                "model": s["model"],
            })
        except Exception:
            pass
    return out


# ─────────────────────────────── overview ───────────────────────────────
def overview() -> dict:
    with engine.connect() as c:
        accounts = c.execute(text("SELECT count(*) FROM accounts")).scalar() or 0
        txns = c.execute(text("SELECT count(*) FROM transactions")).scalar() or 0
        alerts = c.execute(text("SELECT count(*) FROM fraud_alerts")).scalar() or 0
        fraud_accounts = c.execute(
            text("SELECT count(DISTINCT account_id) FROM fraud_alerts")).scalar() or 0
        by_actor = [
            {"code": r.actor_code, "label": ACTOR_LABEL.get(r.actor_code, r.actor_code),
             "count": r.n}
            for r in c.execute(text(
                "SELECT actor_code, count(*) n FROM fraud_alerts "
                "GROUP BY actor_code ORDER BY n DESC"))
        ]
        by_vector = [
            {"vector": r.vector_id, "count": r.n}
            for r in c.execute(text(
                "SELECT vector_id, count(*) n FROM fraud_alerts "
                "GROUP BY vector_id ORDER BY n DESC LIMIT 8"))
        ]
        by_sev = {r.severity: r.n for r in c.execute(text(
            "SELECT severity, count(*) n FROM fraud_alerts GROUP BY severity"))}
    return {
        "accounts": accounts,
        "transactions": txns,
        "alerts": alerts,
        "fraud_accounts": fraud_accounts,
        "fraud_rate_pct": round(100 * alerts / txns, 2) if txns else 0,
        "by_actor": by_actor,
        "by_vector": by_vector,
        "by_severity": by_sev,
    }


# ─────────────────────────── fraud-account list ───────────────────────────
def fraud_accounts() -> list[dict]:
    sql = text("""
        SELECT a.account_id,
               ac.product_type,
               ac.masked_pan,
               count(*)                                    AS alerts,
               max(a.risk_score)                           AS max_risk,
               max(a.created_at)                           AS last_alert,
               coalesce(sum(t.amount), 0)                  AS flagged_amount,
               mode() WITHIN GROUP (ORDER BY a.vector_id)  AS top_vector,
               mode() WITHIN GROUP (ORDER BY a.actor_code) AS top_actor
        FROM fraud_alerts a
        JOIN accounts ac       ON ac.account_id = a.account_id
        LEFT JOIN transactions t ON t.transaction_id = a.transaction_id
        GROUP BY a.account_id, ac.product_type, ac.masked_pan
        ORDER BY max_risk DESC, alerts DESC
    """)
    out = []
    with engine.connect() as c:
        for r in c.execute(sql).mappings():
            out.append({
                "account_id": r["account_id"],
                "product_type": r["product_type"],
                "masked_pan": r["masked_pan"],
                "alerts": r["alerts"],
                "max_risk": r["max_risk"],
                "severity": _severity(r["max_risk"]),
                "flagged_amount": round(float(r["flagged_amount"]), 2),
                "top_vector": r["top_vector"],
                "top_actor": r["top_actor"],
                "top_actor_label": ACTOR_LABEL.get(r["top_actor"], r["top_actor"]),
                "last_alert": r["last_alert"].isoformat() if r["last_alert"] else None,
            })
    return out


# ─────────────────────────── account detail ───────────────────────────
def _history_context(c, account_id: str) -> dict:
    """The prior-39-day behavioral baseline for one account (index-backed)."""
    row = c.execute(text("""
        SELECT count(*) n, coalesce(avg(amount),0) avg_amt, coalesce(sum(amount),0) tot,
               min(event_time) first_seen, max(event_time) last_seen
        FROM transactions
        WHERE account_id = :aid AND event_time < :day40
    """), {"aid": account_id, "day40": DAY40}).mappings().first()
    channels = [
        {"channel": r.channel, "count": r.n}
        for r in c.execute(text("""
            SELECT channel, count(*) n FROM transactions
            WHERE account_id = :aid AND event_time < :day40
            GROUP BY channel ORDER BY n DESC
        """), {"aid": account_id, "day40": DAY40})
    ]
    return {
        "window": "39 days (prior to 2026-09-22)",
        "transactions": row["n"],
        "avg_amount": round(float(row["avg_amt"]), 2),
        "total_amount": round(float(row["tot"]), 2),
        "first_seen": row["first_seen"].isoformat() if row["first_seen"] else None,
        "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
        "channel_mix": channels,
    }


def account_detail(account_id: str) -> dict | None:
    with engine.connect() as c:
        acct = c.execute(text(
            "SELECT account_id, masked_pan, product_type, status FROM accounts "
            "WHERE account_id = :aid"), {"aid": account_id}).mappings().first()
        if not acct:
            return None

        alerts = list(c.execute(text("""
            SELECT a.account_id, a.transaction_id, a.vector_id, a.actor_code, a.risk_score,
                   a.severity, a.reason, a.detection_method, a.created_at,
                   t.amount, t.event_time, t.channel, t.merchant_name,
                   t.merchant_category_code, t.entry_method, t.cvv_result,
                   t.avs_result, t.status, t.card_present, t.promo_plan_id,
                   t.device_fingerprint, t.ip_address
            FROM fraud_alerts a
            LEFT JOIN transactions t ON t.transaction_id = a.transaction_id
            WHERE a.account_id = :aid
            ORDER BY a.risk_score DESC
        """), {"aid": account_id}).mappings())

        flagged = []
        indicator_set = set()
        for a in alerts:
            live = _live_score(_txn_dict(a))
            indicator_set.update(live.get("signals", []))
            flagged.append({
                "transaction_id": str(a["transaction_id"]),
                "amount": float(a["amount"]) if a["amount"] is not None else None,
                "event_time": a["event_time"].isoformat() if a["event_time"] else None,
                "channel": a["channel"],
                "entry_method": a["entry_method"],
                "merchant_name": a["merchant_name"],
                "mcc": a["merchant_category_code"],
                "cvv_result": a["cvv_result"],
                "avs_result": a["avs_result"],
                "status": a["status"],
                "device_fingerprint": a["device_fingerprint"],
                "ip_address": a["ip_address"],
                "vector": a["vector_id"],
                "actor": a["actor_code"],
                "actor_label": ACTOR_LABEL.get(a["actor_code"], a["actor_code"]),
                "risk_score": a["risk_score"],
                "severity": a["severity"],
                "reason": a["reason"],
                "detection_method": a["detection_method"],
                "ml": live,
            })

        recent = [
            {
                "transaction_id": str(r["transaction_id"]),
                "amount": float(r["amount"]) if r["amount"] is not None else None,
                "event_time": r["event_time"].isoformat() if r["event_time"] else None,
                "channel": r["channel"],
                "merchant_name": r["merchant_name"],
                "mcc": r["merchant_category_code"],
                "status": r["status"],
                "is_flagged": r["is_flagged"],
            }
            for r in c.execute(text("""
                SELECT t.transaction_id, t.amount, t.event_time, t.channel,
                       t.merchant_name, t.merchant_category_code, t.status,
                       (fa.transaction_id IS NOT NULL) AS is_flagged
                FROM transactions t
                LEFT JOIN fraud_alerts fa ON fa.transaction_id = t.transaction_id
                WHERE t.account_id = :aid
                ORDER BY t.event_time DESC
                LIMIT 15
            """), {"aid": account_id}).mappings()
        ]

        max_risk = max((a["risk_score"] for a in alerts), default=0)
        context = _history_context(c, account_id)

    return {
        "account": dict(acct),
        "classification": "fraudulent" if alerts else "non-fraudulent",
        "max_risk": max_risk,
        "severity": _severity(max_risk) if alerts else None,
        "alert_count": len(alerts),
        "indicators": sorted(indicator_set),
        "flagged_transactions": flagged,
        "history_context": context,
        "recent_transactions": recent,
    }


# ─────────────────────────── lookup by primary key ───────────────────────────
def lookup_transaction(transaction_id: str) -> dict | None:
    with engine.connect() as c:
        r = c.execute(text("""
            SELECT t.*, (fa.transaction_id IS NOT NULL) AS is_flagged,
                   fa.vector_id, fa.actor_code, fa.risk_score, fa.severity, fa.reason
            FROM transactions t
            LEFT JOIN fraud_alerts fa ON fa.transaction_id = t.transaction_id
            WHERE t.transaction_id = :tid
        """), {"tid": transaction_id}).mappings().first()
    if not r:
        return None
    live = _live_score(_txn_dict(r))
    return {
        "key_type": "transaction_id",
        "transaction_id": str(r["transaction_id"]),
        "account_id": r["account_id"],
        "classification": "fraudulent" if r["is_flagged"] else "non-fraudulent",
        "transaction": {
            "amount": float(r["amount"]) if r["amount"] is not None else None,
            "event_time": r["event_time"].isoformat() if r["event_time"] else None,
            "channel": r["channel"], "entry_method": r["entry_method"],
            "merchant_name": r["merchant_name"], "mcc": r["merchant_category_code"],
            "cvv_result": r["cvv_result"], "avs_result": r["avs_result"],
            "status": r["status"], "card_present": r["card_present"],
            "device_fingerprint": r["device_fingerprint"], "ip_address": r["ip_address"],
        },
        "evidence": {
            "vector": r["vector_id"],
            "actor": r["actor_code"],
            "actor_label": ACTOR_LABEL.get(r["actor_code"], r["actor_code"]),
            "risk_score": r["risk_score"],
            "severity": r["severity"],
            "reason": r["reason"],
            "ml": live,
        },
    }


def lookup(account_id: str | None = None, transaction_id: str | None = None) -> dict | None:
    """Investigate by primary key — accounts.account_id or transactions.transaction_id."""
    if transaction_id:
        return lookup_transaction(transaction_id.strip())
    if account_id:
        detail = account_detail(account_id.strip())
        if detail:
            detail["key_type"] = "account_id"
        return detail
    return None
