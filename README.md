# Synchrony — Real-Time Fraud Detection & Prevention in Digital Lending

Hackathon project (**Synchrony PS-2**). A transaction-type-aware fraud-detection platform:
each event is classified into one of 8 product lines, only the applicable fraud vectors are
activated, and a blend of ML + vector similarity + rules produces an **explainable** decision,
surfaced in a React analyst workspace.

- **Frontend:** React + Vite + Tailwind (`my-react-app/`)
- **Backend:** FastAPI (`backend/`) — JWT auth, ML scoring, multi-agent orchestration, vector search
- **Data / streaming:** PostgreSQL + pgvector, Redis, Kafka (KRaft) — via Docker Compose
- **AI:** AWS Bedrock LLM for explanations (optional; falls back to a template if unavailable)
- **ML:** scikit-learn RandomForest + IsolationForest (pre-trained artifacts are committed)

Repo: https://github.com/abhinav-pal246/Synchrony_Real_Fraud_Detection_and_Prevention_In_digital_Landing

---

## What's implemented

- JWT login (bcrypt-hashed credential stored in Postgres — no hardcoded login)
- 40-day synthetic dataset loaded into Postgres: 1,000 accounts, 52,260 transactions, 250 labelled fraud
- ML scoring (RandomForest + IsolationForest) + deterministic rule signals
- pgvector case library (2,750 labelled cases) for kNN similarity + RAG
- 5 detector agents + LLM investigator + decision engine (approve / review / step-up / decline)
- Analyst dashboard: fraud-account list → detail (why flagged, indicators, ML score, actor, 39-day context), and a Fraud Lookup by primary key

---

## Prerequisites

| Tool | Notes |
|---|---|
| **Docker Desktop** | running — provides the Postgres / Redis / Kafka / backend containers |
| **Node.js 18+** and npm | for the React frontend |
| **AWS credentials** (optional) | only for the Bedrock LLM explanation layer; without them the system runs and the LLM step falls back to a template |

No local Python/Postgres install is needed — everything backend runs inside containers.

---

## Quick start (fresh machine)

```bash
# 1. clone
git clone https://github.com/abhinav-pal246/Synchrony_Real_Fraud_Detection_and_Prevention_In_digital_Landing.git
cd Synchrony_Real_Fraud_Detection_and_Prevention_In_digital_Landing

# 2. configure environment
cp .env.example .env
# then edit .env — at minimum set a real JWT_SECRET:
#   python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. build & start the stack (postgres, redis, kafka, backend)
#    the backend auto-runs DB migrations (alembic upgrade head) on start
docker compose up --build -d

# 4. wait until healthy, then confirm dependencies are reachable
curl -s http://localhost:8000/health/deps      # postgres / redis / kafka -> ok
```

### First-time data setup (run once)

The schema is created automatically, but the tables start empty. Populate them:

```bash
# a) create the analyst login (bcrypt-hashed into the users table)
docker compose exec backend python -m scripts.seed_user "you@example.com" "your-password"

# b) load accounts + 52,260 transactions + fraud alerts into Postgres
docker compose exec backend python -m scripts.load_postgres

# c) build the pgvector case library (fits the scaler + inserts 2,750 case vectors)
docker compose exec backend python -m scripts.build_vectors
```

> ML models are **pre-trained and committed** in `backend/ml/artifacts/`, so no training is
> required. To retrain from the dataset: `docker compose exec backend python -m ml.train`.

### Run the frontend

```bash
cd my-react-app
npm install
npm run dev          # http://localhost:5173
```

Open http://localhost:5173, click **Sign In**, and log in with the credentials you seeded in
step (a). The dashboard then loads live data from the backend.

> The frontend talks to `http://localhost:8000` by default. To point elsewhere, create
> `my-react-app/.env` with `VITE_API_BASE=http://your-host:8000`.

---

## Verify it's working

| Check | URL |
|---|---|
| API liveness | http://localhost:8000/health |
| Dependency connectivity | http://localhost:8000/health/deps |
| Schema + row counts | http://localhost:8000/health/db |
| Interactive API docs (Swagger) | http://localhost:8000/docs |

Quick end-to-end test:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"your-password"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/overview -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/accounts/fraud -H "Authorization: Bearer $TOKEN"
```

---

## Service ports

| Service | In-network address | From host machine |
|---|---|---|
| Postgres | `postgres:5432` | `localhost:5433` |
| Redis | `redis:6379` | `localhost:6379` |
| Kafka | `kafka:9092` | `localhost:29092` |
| Backend API | `backend:8000` | `localhost:8000` |
| Frontend (dev) | — | `localhost:5173` |

> Postgres is exposed on host port **5433** (not 5432) to avoid clashing with a local Postgres.

---

## Key API endpoints (all JWT-protected except health/auth)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | authenticate → JWT |
| GET | `/overview` | KPIs + fraud distributions |
| GET | `/accounts/fraud` | detected fraudulent-account list |
| GET | `/accounts/{account_id}` | account detail: why flagged, indicators, 39-day context |
| GET | `/lookup?account_id=` / `?transaction_id=` | investigate by primary key |
| POST | `/score` | ML score for a transaction |
| POST | `/investigate` | full pipeline: 5 agents + vector + Bedrock LLM |
| POST | `/similar` | pgvector nearest cases |

---

## Project structure

```
.
├── docker-compose.yml         # postgres + redis + kafka + backend
├── .env.example               # copy to .env
├── backend/                   # FastAPI service
│   ├── app/                   # main, models, scoring, agents, embeddings, analytics, security…
│   ├── ml/                    # train.py + committed artifacts/
│   ├── scripts/               # seed_user, load_postgres, build_vectors
│   └── alembic/versions/      # DB migrations (0001–0004)
├── my-react-app/              # React + Vite + Tailwind frontend
├── data/                      # 40-day synthetic dataset + generator
├── docs/aws-postgres.md       # AWS RDS deployment design
└── presentation/              # hackathon deck (HTML + PDF)
```

---

## Useful commands

```bash
docker compose logs -f backend            # tail backend logs
docker compose exec postgres psql -U synchrony -d synchrony   # DB shell
docker compose restart backend            # restart API after code changes
docker compose down                       # stop (keeps data)
docker compose down -v                    # stop AND wipe data — re-run first-time setup after this
```

---

## Troubleshooting

- **`/health/db` shows 0 rows** — run the first-time data setup (seed_user → load_postgres → build_vectors).
- **Login returns 401** — the user isn't seeded, or the password differs. Re-run `scripts.seed_user`.
- **LLM explanation is generic / templated** — AWS credentials aren't reaching Bedrock, or the
  model isn't enabled in your account. This is non-fatal; the rest of the pipeline works. See the
  Bedrock note below.
- **Port already in use** — another Postgres/Redis is bound. Adjust the host port mappings in
  `docker-compose.yml`.
- **`docker compose up` fails building ML wheels** — transient PyPI timeout; re-run (the build
  already uses generous retries/timeouts).

### AWS Bedrock note

The compose file mounts your host `~/.aws` into the backend (read-only) so boto3 can find your
credentials. Set `AWS_REGION` and `BEDROCK_MODEL_ID` in `.env`. On this project's AWS account,
Anthropic Claude requires account verification, so `meta.llama3-8b-instruct-v1:0` is the
recommended working model. Without AWS access the explanation layer falls back to a template and
everything else is unaffected.

---

## Deploying PostgreSQL on AWS (RDS)

See [`docs/aws-postgres.md`](docs/aws-postgres.md) for the RDS schema, indexing, sizing, and the
Redis + PostgreSQL → ML data-access design. The app is RDS-ready: point `DATABASE_URL` at the RDS
endpoint and run `alembic upgrade head` + the loader scripts.
