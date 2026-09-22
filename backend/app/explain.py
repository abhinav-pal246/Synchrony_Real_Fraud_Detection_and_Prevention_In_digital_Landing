"""
AI layer — human-readable alert explanation.

Primary path: AWS Bedrock (Claude) generates the reason.
Guardrails: PII is redacted before anything leaves the service; if Bedrock is
unreachable or model access isn't enabled, we fall back to a deterministic
template so the pipeline never breaks. No secrets are hardcoded (region/model
come from env; AWS creds come from the IAM role / env, never the code).
"""

import json
import os

# Default to Amazon Nova — works on new AWS accounts with no verification/payment.
# Switch to an anthropic.* id once the account is verified for Claude.
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def redact(txn: dict) -> dict:
    """Strip/anonymize PII before sending context to the LLM (guardrail)."""
    safe = dict(txn)
    if safe.get("masked_pan"):
        safe["masked_pan"] = str(safe["masked_pan"])[-4:]  # keep last4 only
    if safe.get("ip_address"):
        safe["ip_address"] = "***redacted***"
    if safe.get("device_fingerprint"):
        safe["device_fingerprint"] = "dev_***"
    return safe


def build_prompt(ctx: dict, score: dict) -> str:
    return (
        "You are a fraud-analyst assistant. In 2-3 sentences, explain whether this "
        "transaction is suspicious and why. Cite the concrete signals. Do not invent data.\n\n"
        f"Transaction (redacted): {json.dumps(ctx)}\n"
        f"Risk score: {score['risk_score']}\n"
        f"Triggered signals: {', '.join(score['signals']) or 'none'}\n"
        f"Likely fraud vectors: {', '.join(score['likely_vectors']) or 'none'}\n"
    )


def _invoke(prompt: str, model_id: str) -> str:
    """Invoke a Bedrock model, adapting the request/response to the model family."""
    import boto3

    rt = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    if model_id.startswith("amazon.nova"):
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": 300, "temperature": 0.3},
        }
        resp = rt.invoke_model(modelId=model_id, body=json.dumps(body))
        data = json.loads(resp["body"].read())
        return data["output"]["message"]["content"][0]["text"].strip()

    if model_id.startswith("meta.llama"):
        formatted = (
            "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
            + prompt
            + "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        )
        body = {"prompt": formatted, "max_gen_len": 300, "temperature": 0.3}
        resp = rt.invoke_model(modelId=model_id, body=json.dumps(body))
        data = json.loads(resp["body"].read())
        return data["generation"].strip()

    # anthropic.* (Claude — once the account is verified)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = rt.invoke_model(modelId=model_id, body=json.dumps(body))
    data = json.loads(resp["body"].read())
    return data["content"][0]["text"].strip()


def _bedrock_reason(prompt: str):
    try:
        return _invoke(prompt, BEDROCK_MODEL)
    except Exception:
        return None  # graceful fallback (no access / no creds / no network)


def _template_reason(score: dict) -> str:
    if score["risk_score"] < 0.4 and not score["likely_vectors"]:
        return ("No strong fraud indicators; the transaction is consistent with the "
                "account's normal behavior.")
    parts = []
    if score["signals"]:
        parts.append("triggered signals: " + ", ".join(score["signals"]))
    if score["likely_vectors"]:
        parts.append("consistent with " + ", ".join(score["likely_vectors"]))
    return f"Elevated risk ({score['risk_score']}) — " + "; ".join(parts) + "."


def explain(txn: dict, score: dict) -> dict:
    ctx = redact(txn)
    reason = _bedrock_reason(build_prompt(ctx, score))
    if reason:
        return {"reason": reason, "source": "bedrock", "model": BEDROCK_MODEL}
    return {"reason": _template_reason(score), "source": "template", "model": "rule-based-fallback"}
