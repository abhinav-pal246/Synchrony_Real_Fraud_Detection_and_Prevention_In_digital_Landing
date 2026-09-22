# AWS PostgreSQL (RDS) — 39-day history store design

The fraud pipeline detects on the **40th day** using each customer's **prior 39 days** of
context. PostgreSQL is that history store; Redis holds hot/velocity state. This document is
the deployment design for running the same schema the app already uses on **Amazon RDS for
PostgreSQL** (with `pgvector`).

> **Status:** the schema, indexes and data-access flow below are **implemented and running**
> locally (Docker `pgvector/pgvector:pg16`). Moving to RDS is a **deployment step** — it needs
> the AWS console and incurs cost, so it is documented here rather than provisioned
> automatically. The app is already RDS-ready: it reads `DATABASE_URL`, so only the endpoint
> changes.

---

## 1. Why RDS for PostgreSQL

| Need | RDS capability |
|---|---|
| Durability / HA | Multi-AZ standby, automated backups, point-in-time recovery |
| Encryption at rest | KMS-managed, enable at create time |
| Encryption in transit | `sslmode=require` + RDS CA bundle |
| Access control | Security group locked to the app subnet; optional IAM DB auth |
| Vector search | `pgvector` available as an RDS extension |
| Ops | Managed patching, CloudWatch metrics, Performance Insights |

## 2. Sizing for the target workload

~1,000 customers × 39 days of history. Current prototype dataset = **52,260 transactions**
(~15–20 MB of table + index data), so the workload is tiny; the sizing below leaves large
headroom for real volumes.

| Parameter | Prototype value | Note |
|---|---|---|
| Instance class | `db.t4g.medium` (2 vCPU, 4 GB) | burstable; step up to `m6g.large` for production |
| Storage | `gp3`, 50 GB, 3000 IOPS | autoscaling on |
| Multi-AZ | on (prod) / off (dev) | |
| Engine | PostgreSQL 16 | matches local |
| Extensions | `vector`, `pgcrypto` | `pgcrypto` provides `gen_random_uuid()` |

## 3. Schema (as implemented — Alembic migrations `0001`–`0004`)

- **`accounts`** — customer/account identity + product line (PK `account_id`).
- **`transactions`** — the 40-day event history (PK `transaction_id`, FK `account_id`).
- **`fraud_alerts`** — detection output: risk score, severity, vector, actor, reason.
- **`case_vectors`** — `pgvector` embeddings (26-dim) with ground-truth labels.
- **`users`** — analyst login (bcrypt hash; no plaintext, no hardcoded credentials).

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

## 4. Indexing — efficient 39-day retrieval, never a full scan

```sql
-- one customer's chronological history (the 39-day context query)
CREATE INDEX ix_txn_account_time ON transactions (account_id, event_time);

-- fraud-account list: group alerts per account, newest first
CREATE INDEX ix_alert_account_created ON fraud_alerts (account_id, created_at);

-- approximate-nearest-neighbour for vector similarity at scale
CREATE INDEX ix_case_vectors_ann ON case_vectors
  USING hnsw (embedding vector_l2_ops);   -- or ivfflat with lists=100
```

`ix_txn_account_time` turns the context lookup into a single indexed range scan:

```sql
SELECT * FROM transactions
WHERE account_id = :aid AND event_time < DATE '2026-09-22'
ORDER BY event_time DESC;
```

## 5. Data-access flow (Redis + PostgreSQL → ML)

```
Kafka event ─▶ Fraud Detection Service
                 ├─ Redis   : hot velocity / recent-txn features (low latency)
                 ├─ Postgres: this account's prior-39-day rows (indexed, scoped)
                 └─ pgvector: kNN over labelled case vectors
                        │
                        ▼
             feature engineering ▶ ML score ▶ embedding ▶ decision
```

**Principle:** retrieve **only the relevant customer's** context (index-backed), compute the
baseline in-service, and pass that to features/embeddings — the full table is **never** handed
to the model. This keeps scoring fast and privacy-scoped.

## 6. Provisioning outline (run in your AWS account)

1. Create the RDS instance (console or IaC) in a **private** subnet group; enable
   **encryption at rest** (KMS) and **automated backups**.
2. Security group: inbound `5432` only from the app's security group / subnet.
3. `psql` in and run the two `CREATE EXTENSION` statements above.
4. Point the app at it: `DATABASE_URL=postgresql+psycopg://USER:***@<rds-endpoint>:5432/synchrony?sslmode=require`.
5. `alembic upgrade head` → creates schema + indexes.
6. `python -m scripts.load_postgres` → loads accounts + 40-day transactions + alerts.
7. `python -m scripts.build_vectors` → builds the `pgvector` case library, then create the
   HNSW/IVFFlat index.

## 7. Security notes

- **Secrets:** the app reads `DATABASE_URL` from the environment. The AWS Organization SCP on
  this account currently blocks Secrets Manager / SSM Parameter Store, so for the prototype the
  connection string is injected as an env var. On an unrestricted account, store it in
  **Secrets Manager** and grant the app role read access.
- **TLS:** always `sslmode=require` with the RDS CA bundle.
- **Least privilege:** the app connects as a role with DML on the five tables only — not a
  superuser.
- **Auditability:** enable RDS audit logging / `pgaudit` for the fraud-decision tables.

---

**Implemented:** schema, indexes, loaders, and the Redis+Postgres→ML access flow (local
`pgvector` container). **Deployment step (documented, not executed):** the RDS instance itself.
