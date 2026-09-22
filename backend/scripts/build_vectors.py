"""
Build the pgvector case library.

Fits a StandardScaler on the 40-day dataset, then embeds all fraud cases + a sample
of legitimate transactions and inserts them (with labels) into `case_vectors`.
Run inside the backend container:  python -m scripts.build_vectors
"""

import csv
import random
import statistics
from collections import defaultdict
from pathlib import Path

import joblib
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from app.db import engine
from app.ml_features import build_features

DATA = Path("/data")
ART = Path(__file__).resolve().parent.parent / "ml" / "artifacts"
SAMPLE_LEGIT = 2500


def main():
    gt = {}
    with (DATA / "synchrony_40day_ground_truth.csv").open() as f:
        for r in csv.DictReader(f):
            gt[r["transaction_id"]] = (r["fraud_vector"], r["actor"])

    rows = []
    with (DATA / "synchrony_40day_all.csv").open() as f:
        rows = list(csv.DictReader(f))

    amounts = defaultdict(list)
    for r in rows:
        amounts[r["account_id"]].append(float(r["amount"]))
    acct_stats = {
        aid: {"count": len(xs), "mean": sum(xs) / len(xs),
              "std": statistics.pstdev(xs) if len(xs) > 1 else 0.0}
        for aid, xs in amounts.items()
    }

    # fit the embedding scaler on all transactions
    X = [build_features(r, acct_stats.get(r["account_id"])) for r in rows]
    scaler = StandardScaler().fit(X)
    joblib.dump(scaler, ART / "scaler.joblib")

    fraud_rows = [r for r in rows if r["transaction_id"] in gt]
    legit_rows = [r for r in rows if r["transaction_id"] not in gt]
    random.seed(1)
    sample_legit = random.sample(legit_rows, min(SAMPLE_LEGIT, len(legit_rows)))
    selected = fraud_rows + sample_legit

    inserted = 0
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM case_vectors"))
        for r in selected:
            feats = build_features(r, acct_stats.get(r["account_id"]))
            vec = scaler.transform([feats])[0]
            lit = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
            fv, actor = gt.get(r["transaction_id"], (None, None))
            summary = (f"{r['channel']} mcc={r['mcc']} ${r['amount']} "
                       f"entry={r['entry_method']} status={r['status']}")
            conn.execute(text(
                "INSERT INTO case_vectors "
                "(id, transaction_id, embedding, is_fraud, fraud_vector, actor, amount, mcc, channel, summary) "
                f"VALUES (gen_random_uuid(), :tid, '{lit}'::vector, :isf, :fv, :actor, :amt, :mcc, :chan, :sum)"),
                {"tid": r["transaction_id"],
                 "isf": r["transaction_id"] in gt, "fv": fv, "actor": actor,
                 "amt": float(r["amount"]), "mcc": r["mcc"], "chan": r["channel"], "sum": summary})
            inserted += 1

    print(f"scaler saved; inserted {inserted} case vectors "
          f"({len(fraud_rows)} fraud + {len(sample_legit)} legit)")


if __name__ == "__main__":
    main()
