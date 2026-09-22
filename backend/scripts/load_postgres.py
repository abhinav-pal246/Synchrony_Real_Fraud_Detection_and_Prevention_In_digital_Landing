"""
Load the 40-day dataset into PostgreSQL — the historical context store.

  accounts       : one row per customer (1,000), derived from the transaction feed
  transactions   : the full 40-day event history (~52k) — days 1-39 are the
                   historical context, day 40 (2026-09-22) is the "current" day
  fraud_alerts   : the detection output — one alert per ground-truth fraud txn,
                   scored with the real ML model so each carries a genuine
                   risk score + reason (not just a "fraud" flag)

Run inside the backend container:  python -m scripts.load_postgres
Idempotent: it truncates and reloads.
"""

import csv
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.db import engine
from app.scoring import score_transaction, detect_signals, map_vectors

DATA = Path("/data")
ALL_CSV = DATA / "synchrony_40day_all.csv"
GT_CSV = DATA / "synchrony_40day_ground_truth.csv"

# BIN -> product line (mirrors the dataset generator's BIN_BY_PRODUCT)
BIN_PRODUCT = {
    "603571": "private_label", "521000": "private_label",
    "414720": "co_branded", "546616": "co_branded",
    "601160": "carecredit", "603572": "promotional",
}

ACTOR_LABEL = {
    "B": "First-party (cardholder)",
    "3P": "Third-party fraudster",
    "S": "Synthetic / ring",
    "M": "Merchant / associate",
}


def _dt(s):
    """Parse a naive ISO timestamp from the feed as UTC."""
    try:
        return datetime.fromisoformat(str(s)).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _bool(s):
    return str(s).strip().lower() in ("true", "1", "yes")


def _severity(risk_100):
    if risk_100 >= 85:
        return "critical"
    if risk_100 >= 60:
        return "high"
    if risk_100 >= 40:
        return "medium"
    return "low"


def main():
    # ── ground truth: transaction_id -> (fraud_vector, actor) ──
    gt = {}
    with GT_CSV.open() as f:
        for r in csv.DictReader(f):
            gt[r["transaction_id"]] = (r["fraud_vector"], r["actor"])

    rows = list(csv.DictReader(ALL_CSV.open()))
    print(f"read {len(rows)} transactions, {len(gt)} labelled fraud")

    # ── derive accounts from the feed ──
    accounts = {}
    for r in rows:
        aid = r["account_id"]
        if aid not in accounts:
            accounts[aid] = {
                "account_id": aid,
                "masked_pan": r["masked_pan"],
                "product_type": BIN_PRODUCT.get(r["bin"], "unknown"),
                "status": "active",
            }
    print(f"derived {len(accounts)} accounts")

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE fraud_alerts, transactions, accounts RESTART IDENTITY CASCADE"))

        # accounts
        conn.execute(
            text("INSERT INTO accounts (account_id, masked_pan, product_type, status) "
                 "VALUES (:account_id, :masked_pan, :product_type, :status)"),
            list(accounts.values()),
        )

        # transactions (batched)
        ins_txn = text(
            "INSERT INTO transactions "
            "(transaction_id, account_id, masked_pan, event_time, amount, currency, "
            " merchant_id, merchant_name, merchant_category_code, terminal_id, channel, "
            " entry_method, card_present, cvv_result, avs_result, three_ds_result, status, "
            " ip_address, device_fingerprint, promo_plan_id) "
            "VALUES (:tid, :aid, :pan, :et, :amt, 'USD', :mid, :mname, :mcc, :term, :chan, "
            " :entry, :cp, :cvv, :avs, :tds, :status, :ip, :dev, :promo)"
        )
        batch, B = [], 2000
        for r in rows:
            batch.append({
                "tid": r["transaction_id"], "aid": r["account_id"], "pan": r["masked_pan"],
                "et": _dt(r["event_time"]), "amt": float(r["amount"] or 0),
                "mid": r["merchant_id"] or None, "mname": r["merchant_name"] or None,
                "mcc": r["mcc"] or None, "term": r["terminal_id"] or None,
                "chan": r["channel"] or None, "entry": r["entry_method"] or None,
                "cp": _bool(r["card_present"]), "cvv": r["cvv_result"] or None,
                "avs": r["avs_result"] or None, "tds": r["three_ds"] or None,
                "status": r["status"] or None, "ip": r["ip_address"] or None,
                "dev": r["device_fingerprint"] or None,
                "promo": (r["promo_type"] or None) if _bool(r["promo_financing"]) else None,
            })
            if len(batch) >= B:
                conn.execute(ins_txn, batch)
                batch = []
        if batch:
            conn.execute(ins_txn, batch)
        print(f"inserted {len(rows)} transactions")

        # ── fraud_alerts: score each labelled fraud txn with the real ML model ──
        ins_alert = text(
            "INSERT INTO fraud_alerts "
            "(alert_id, transaction_id, account_id, vector_id, actor_code, risk_score, severity, "
            " status, detection_method, reason) "
            "VALUES (gen_random_uuid(), :tid, :aid, :vec, :actor, :risk, :sev, 'open', :method, :reason)"
        )
        alerts = []
        for r in rows:
            if r["transaction_id"] not in gt:
                continue
            fv, actor = gt[r["transaction_id"]]
            scored = score_transaction(r)
            risk_100 = int(round(scored["risk_score"] * 100))
            signals = detect_signals(r)
            vecs = map_vectors(signals, r) or [fv]
            reason = (
                f"{ACTOR_LABEL.get(actor, actor)} · vector {fv}. "
                f"ML fraud probability {scored['fraud_probability']:.2f}, "
                f"anomaly {scored['anomaly_score']:.2f}. "
                f"Indicators: {', '.join(signals) if signals else 'behavioral deviation'}. "
                f"Rule map -> {', '.join(vecs)}."
            )
            alerts.append({
                "tid": r["transaction_id"], "aid": r["account_id"], "vec": fv,
                "actor": actor, "risk": risk_100, "sev": _severity(risk_100),
                "method": "ml_model+rule", "reason": reason,
            })
        conn.execute(ins_alert, alerts)
        print(f"inserted {len(alerts)} fraud alerts "
              f"across {len(set(a['aid'] for a in alerts))} accounts")


if __name__ == "__main__":
    main()
