"""
Multi-agent fraud detection.

Several specialized *detector agents* each analyze a transaction from their own
angle and return a structured verdict. An *orchestrator* fuses those verdicts into
a final risk + decision, and — for high-risk cases — an *LLM investigator agent*
(AWS Bedrock) synthesizes all findings into a recommended action.

This is the "collection of specialists, not one model" design: each agent is
independent and configuration-driven, so new agents can be added without touching
the others.
"""

import json
from dataclasses import asdict, dataclass, field

from sqlalchemy import text

from .db import engine
from .embeddings import similar_cases
from .explain import BEDROCK_MODEL, _invoke, redact
from .ml_features import _hour
from .scoring import account_stats, detect_signals, map_vectors, score_transaction


@dataclass
class Verdict:
    agent: str
    risk: float
    weight: float
    signals: list = field(default_factory=list)
    rationale: str = ""


# ─────────────────────────── detector agents ───────────────────────────
class RuleEngineAgent:
    """Fast deterministic rules (card-testing, AVS/CVV mismatch, cash-like MCC…)."""
    name, weight = "RuleEngineAgent", 1.0

    def analyze(self, txn, ctx) -> Verdict:
        signals = detect_signals(txn)
        vectors = map_vectors(signals, txn)
        risk = min(1.0, 0.25 * len(signals))
        rationale = (f"{len(signals)} rule(s) fired" +
                     (f"; matches {', '.join(vectors)}" if vectors else "; no vector match"))
        return Verdict(self.name, round(risk, 4), self.weight, signals, rationale)


class MLScoringAgent:
    """Supervised RandomForest + unsupervised IsolationForest."""
    name, weight = "MLScoringAgent", 1.6

    def analyze(self, txn, ctx) -> Verdict:
        s = score_transaction(txn)
        risk = max(s["fraud_probability"], s["anomaly_score"] * 0.6)
        return Verdict(
            self.name, round(risk, 4), self.weight,
            [f"proba={s['fraud_probability']}", f"anomaly={s['anomaly_score']}"],
            f"ML fraud_probability={s['fraud_probability']}, anomaly={s['anomaly_score']}")


class VelocityAgent:
    """Behavioral deviation vs the account's historical baseline."""
    name, weight = "VelocityAgent", 1.2

    def analyze(self, txn, ctx) -> Verdict:
        z = ctx.get("amount_zscore", 0.0)
        signals = []
        risk = 0.0
        if z and abs(z) > 2:
            signals.append(f"amount_zscore={round(z, 1)}")
            risk = min(1.0, (abs(z) - 2) / 4)
        hour = _hour(txn.get("event_time", ""))
        if hour is not None and (hour < 5):
            signals.append("off_hour")
            risk = min(1.0, risk + 0.15)
        rationale = (f"amount deviates {round(z, 1)}σ from account baseline"
                     if z else "no baseline available for this account")
        return Verdict(self.name, round(risk, 4), self.weight, signals, rationale)


class GraphAgent:
    """Shared-PII / fraud-ring signal — how many accounts share this device/IP."""
    name, weight = "GraphAgent", 1.4

    def analyze(self, txn, ctx) -> Verdict:
        dev, ip = txn.get("device_fingerprint"), txn.get("ip_address")
        shared_dev = shared_ip = 0
        try:
            with engine.connect() as c:
                if dev:
                    shared_dev = c.execute(text(
                        "SELECT count(DISTINCT account_id) FROM transactions "
                        "WHERE device_fingerprint = :d"), {"d": dev}).scalar() or 0
                if ip:
                    shared_ip = c.execute(text(
                        "SELECT count(DISTINCT account_id) FROM transactions "
                        "WHERE ip_address = :i"), {"i": ip}).scalar() or 0
        except Exception:
            pass
        shared = max(shared_dev, shared_ip)
        signals, risk = [], 0.0
        if shared > 1:
            signals.append(f"accounts_sharing_pii={shared}")
            risk = min(1.0, 0.3 * (shared - 1))
        rationale = (f"{shared} accounts share this device/IP (possible ring)"
                     if shared > 1 else "no shared-PII cluster found")
        return Verdict(self.name, round(risk, 4), self.weight, signals, rationale)


class VectorSimilarityAgent:
    """kNN over the pgvector case library — how many nearest historical cases are fraud."""
    name, weight = "VectorSimilarityAgent", 1.5

    def analyze(self, txn, ctx) -> Verdict:
        cases = ctx.get("similar_cases") or []
        if not cases:
            return Verdict(self.name, 0.0, self.weight, [], "no case library / no neighbours")
        frauds = [c for c in cases if c.get("is_fraud")]
        risk = round(len(frauds) / len(cases), 4)
        top = None
        if frauds:
            from collections import Counter
            top = Counter(c.get("fraud_vector") for c in frauds).most_common(1)[0][0]
        signals = [f"{len(frauds)}/{len(cases)}_nearest_fraud"]
        if top:
            signals.append(f"nearest_pattern={top}")
        rationale = (f"{len(frauds)} of {len(cases)} nearest historical cases are fraud"
                     + (f", mostly {top}" if top else ""))
        return Verdict(self.name, risk, self.weight, signals, rationale)


# ─────────────────────────── LLM investigator agent ───────────────────────────
class LLMInvestigatorAgent:
    name = "LLMInvestigatorAgent"

    def investigate(self, txn, verdicts, final_risk, cases=None):
        ctx = redact(txn)
        findings = "\n".join(
            f"- {v.agent}: risk={v.risk} ({v.rationale})" for v in verdicts)

        # RAG: ground the explanation in the nearest historical cases (pgvector)
        cases = cases or []
        if cases:
            precedent = "\n".join(
                f"- dist {c.get('distance')}: "
                f"{'FRAUD ' + str(c.get('fraud_vector')) if c.get('is_fraud') else 'legitimate'} "
                f"({c.get('summary')})"
                for c in cases[:5])
        else:
            precedent = "(no case library available)"

        prompt = (
            "You are a senior fraud investigator. Several detection agents analyzed one "
            "transaction, and vector search retrieved the most similar historical cases. In "
            "3-4 sentences: synthesize the findings, cite the precedent where relevant, state the "
            "single most likely fraud type, and recommend ONE action (approve / step-up "
            "authentication / decline / manual review). Do not invent data.\n\n"
            f"Transaction (redacted): {json.dumps(ctx)}\n"
            f"Final aggregated risk: {final_risk}\n"
            f"Agent findings:\n{findings}\n"
            f"Most similar past cases (vector search):\n{precedent}\n"
        )
        try:
            return {"summary": _invoke(prompt, BEDROCK_MODEL), "source": "bedrock", "model": BEDROCK_MODEL}
        except Exception:
            top = max(verdicts, key=lambda v: v.risk)
            return {
                "summary": (f"Aggregated risk {final_risk}. Strongest signal from {top.agent} "
                            f"({top.rationale})."),
                "source": "template", "model": "rule-based-fallback",
            }


# ─────────────────────────── orchestrator ───────────────────────────
def _decision(risk: float) -> str:
    if risk >= 0.85:
        return "decline"
    if risk >= 0.60:
        return "step_up_authentication"
    if risk >= 0.40:
        return "manual_review"
    return "approve"


class FraudOrchestrator:
    def __init__(self):
        self.detectors = [
            RuleEngineAgent(), MLScoringAgent(), VelocityAgent(),
            GraphAgent(), VectorSimilarityAgent(),
        ]
        self.investigator = LLMInvestigatorAgent()

    def _context(self, txn):
        stats = account_stats(txn.get("account_id"))
        z = 0.0
        if stats and stats.get("mean"):
            std = float(stats.get("std") or 0) or 1.0
            z = (float(txn.get("amount") or 0) - float(stats["mean"])) / std
        cases = similar_cases(txn, k=8)  # pgvector nearest-neighbour retrieval
        return {"amount_zscore": z, "acct_stats": stats, "similar_cases": cases}

    def run(self, txn: dict) -> dict:
        ctx = self._context(txn)
        verdicts = [a.analyze(txn, ctx) for a in self.detectors]

        wsum = sum(v.weight for v in verdicts) or 1.0
        agg = sum(v.risk * v.weight for v in verdicts) / wsum
        consensus = sum(1 for v in verdicts if v.risk >= 0.5)
        final = round(min(1.0, agg + (0.10 if consensus >= 2 else 0.0)), 4)

        cases = ctx.get("similar_cases") or []
        result = {
            "final_risk": final,
            "decision": _decision(final),
            "consensus_agents": consensus,
            "agents": [asdict(v) for v in verdicts],
            "similar_cases": cases[:5],  # retrieved precedent (vector search)
        }
        if final >= 0.5:
            result["investigation"] = self.investigator.investigate(txn, verdicts, final, cases)
        return result
