"""
Train local fraud-detection models on the 40-day synthetic dataset.

Two models (justifies FastAPI/Python over Spring Boot):
  - RandomForestClassifier  (supervised, uses ground-truth labels) → fraud probability
  - IsolationForest         (unsupervised anomaly)                  → anomaly score

Artifacts are written to ml/artifacts/ (bind-mounted to the host) and loaded by the API.
Run inside the backend container:  python -m ml.train
Reads the dataset from /data (mounted read-only).
"""

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report

from app.ml_features import FEATURE_ORDER, build_features

DATA = Path("/data")
ART = Path(__file__).resolve().parent / "artifacts"
ART.mkdir(parents=True, exist_ok=True)


def main():
    # ground-truth labels (kept OUTSIDE the workbook; used only for training/eval)
    fraud_ids = set()
    with (DATA / "synchrony_40day_ground_truth.csv").open() as f:
        for row in csv.DictReader(f):
            fraud_ids.add(row["transaction_id"])

    rows = []
    with (DATA / "synchrony_40day_all.csv").open() as f:
        for row in csv.DictReader(f):
            rows.append(row)

    # per-account baseline stats (for amount z-score / behavioral deviation)
    amounts = defaultdict(list)
    for r in rows:
        amounts[r["account_id"]].append(float(r["amount"]))
    acct_stats = {}
    for aid, xs in amounts.items():
        mean = sum(xs) / len(xs)
        std = statistics.pstdev(xs) if len(xs) > 1 else 0.0
        acct_stats[aid] = {"count": len(xs), "mean": round(mean, 2), "std": round(std, 2)}

    X, y = [], []
    for r in rows:
        X.append(build_features(r, acct_stats.get(r["account_id"])))
        y.append(1 if r["transaction_id"] in fraud_ids else 0)

    print(f"training on {len(y)} txns, {sum(y)} fraud ({100*sum(y)/len(y):.2f}%)")

    clf = RandomForestClassifier(
        n_estimators=200, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    clf.fit(X, y)

    iso = IsolationForest(n_estimators=200, contamination=0.02, random_state=42, n_jobs=-1)
    iso.fit(X)

    joblib.dump(clf, ART / "clf.joblib")
    joblib.dump(iso, ART / "iso.joblib")
    (ART / "acct_stats.json").write_text(json.dumps(acct_stats))
    (ART / "meta.json").write_text(json.dumps({
        "feature_order": FEATURE_ORDER,
        "n_train": len(y),
        "n_fraud": int(sum(y)),
        "models": ["RandomForestClassifier", "IsolationForest"],
        "version": "0.1.0",
    }, indent=2))

    print(classification_report(y, clf.predict(X), digits=3, zero_division=0))
    print("saved:", sorted(p.name for p in ART.iterdir()))


if __name__ == "__main__":
    main()
