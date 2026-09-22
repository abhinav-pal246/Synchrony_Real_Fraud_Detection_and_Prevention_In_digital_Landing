"""Feature engineering shared by training and serving (same function => no skew)."""

from datetime import datetime

CHANNELS = ["in_store", "e_commerce", "mobile"]
ENTRIES = ["chip", "contactless", "swipe", "manual", "cnp", "token"]
CASHLIKE_MCC = {"6051", "6540", "4829"}
GIFTCARD_MCC = {"5947"}
HEALTH_MCC = {"8011", "8021", "8042", "0742"}
ELECTRONICS_MCC = {"5732"}

FEATURE_ORDER = [
    "amount", "hour", "gift_card_amount",
    "card_present", "promo_financing",
    "is_small_amount", "is_high_amount",
    "cvv_no_match", "avs_no_match", "status_declined",
    *[f"chan_{c}" for c in CHANNELS],
    *[f"entry_{e}" for e in ENTRIES],
    "mcc_cashlike", "mcc_giftcard", "mcc_health", "mcc_electronics",
    "acct_txn_count", "acct_avg_amount", "amount_zscore",
]


def _truthy(v):
    return 1 if v in (True, "True", "true", 1, "1") else 0


def _hour(event_time):
    try:
        return datetime.fromisoformat(str(event_time).replace("Z", "")).hour
    except Exception:
        return 12


def build_features(txn, acct_stats=None):
    """Return a fixed-order numeric feature vector for one transaction."""
    amount = float(txn.get("amount") or 0)
    gca = float(txn.get("gift_card_amount") or 0)
    channel = txn.get("channel") or ""
    entry = txn.get("entry_method") or ""
    mcc = str(txn.get("mcc") or "")
    cvv = txn.get("cvv_result") or ""
    avs = str(txn.get("avs_result") or "")
    status = txn.get("status") or ""

    stats = acct_stats or {}
    avg = float(stats.get("mean", 0) or 0)
    std = float(stats.get("std", 0) or 0) or 1.0
    zscore = (amount - avg) / std if avg else 0.0

    row = {
        "amount": amount,
        "hour": _hour(txn.get("event_time", "")),
        "gift_card_amount": gca,
        "card_present": _truthy(txn.get("card_present")),
        "promo_financing": _truthy(txn.get("promo_financing")),
        "is_small_amount": 1 if amount < 3 else 0,
        "is_high_amount": 1 if amount > 1000 else 0,
        "cvv_no_match": 1 if cvv == "no_match" else 0,
        "avs_no_match": 1 if avs in ("N", "no_match") else 0,
        "status_declined": 1 if status == "declined" else 0,
        "mcc_cashlike": 1 if mcc in CASHLIKE_MCC else 0,
        "mcc_giftcard": 1 if mcc in GIFTCARD_MCC else 0,
        "mcc_health": 1 if mcc in HEALTH_MCC else 0,
        "mcc_electronics": 1 if mcc in ELECTRONICS_MCC else 0,
        "acct_txn_count": float(stats.get("count", 0) or 0),
        "acct_avg_amount": avg,
        "amount_zscore": zscore,
    }
    for c in CHANNELS:
        row[f"chan_{c}"] = 1 if channel == c else 0
    for e in ENTRIES:
        row[f"entry_{e}"] = 1 if entry == e else 0

    return [row[f] for f in FEATURE_ORDER]
