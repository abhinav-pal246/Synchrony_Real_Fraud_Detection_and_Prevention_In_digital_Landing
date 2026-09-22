"""Load the local ML models and score a transaction (rule signals + ML blend)."""

import functools
import json
from pathlib import Path

import joblib

from .ml_features import build_features

ART = Path(__file__).resolve().parent.parent / "ml" / "artifacts"


@functools.lru_cache(maxsize=1)
def _load():
    clf = joblib.load(ART / "clf.joblib")
    iso = joblib.load(ART / "iso.joblib")
    acct_stats = json.loads((ART / "acct_stats.json").read_text())
    return clf, iso, acct_stats


def models_ready() -> bool:
    return (ART / "clf.joblib").exists()


def account_stats(account_id):
    """Return the trained baseline stats for an account (count/mean/std), or None."""
    try:
        _, _, acct_stats = _load()
        return acct_stats.get(account_id)
    except Exception:
        return None


# ── deterministic rule signals (the fast rule-engine layer) ──
def detect_signals(txn):
    sig = []
    amt = float(txn.get("amount") or 0)
    if txn.get("cvv_result") == "no_match":
        sig.append("cvv_mismatch")
    if str(txn.get("avs_result")) in ("N", "no_match"):
        sig.append("avs_mismatch")
    if txn.get("status") == "declined" and amt < 3:
        sig.append("small_amount_decline")
    if amt > 1000:
        sig.append("high_amount")
    if float(txn.get("gift_card_amount") or 0) > 0:
        sig.append("gift_card_purchase")
    if str(txn.get("mcc") or "") in {"6051", "6540", "4829"}:
        sig.append("cash_like_mcc")
    if txn.get("entry_method") == "swipe":
        sig.append("magstripe_fallback")
    return sig


def map_vectors(signals, txn):
    v, s = [], set(signals)
    if "small_amount_decline" in s:
        v.append("CB-2")
    if {"cvv_mismatch", "avs_mismatch"} & s and txn.get("channel") == "e_commerce":
        v.append("EC-1")
    if "cash_like_mcc" in s:
        v.append("CB-3")
    if "gift_card_purchase" in s:
        v.append("PL-2")
    if "magstripe_fallback" in s:
        v.append("CB-1")
    if "high_amount" in s and txn.get("channel") in ("e_commerce", "mobile"):
        v.append("X-1/DW-1")
    return v


def score_transaction(txn: dict) -> dict:
    clf, iso, acct_stats = _load()
    feats = build_features(txn, acct_stats.get(txn.get("account_id")))

    proba = float(clf.predict_proba([feats])[0][1])
    iso_raw = float(iso.score_samples([feats])[0])       # lower = more anomalous
    anomaly = max(0.0, min(1.0, -iso_raw))               # rough normalize to 0..1

    signals = detect_signals(txn)
    vectors = map_vectors(signals, txn)

    # blend ML probability, anomaly, and a small rule bump
    rule_bump = min(0.3, 0.1 * len(signals))
    risk = round(min(1.0, 0.65 * proba + 0.2 * anomaly + rule_bump), 4)

    return {
        "risk_score": risk,
        "fraud_probability": round(proba, 4),
        "anomaly_score": round(anomaly, 4),
        "signals": signals,
        "likely_vectors": vectors,
        "model": "RandomForest+IsolationForest",
        "model_version": "0.1.0",
    }
