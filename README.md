# Synchrony Analytics — Real-Time Fraud Detection

Hackathon project (Synchrony PS-2): real-time fraud detection and prevention
across the digital lending ecosystem.

- **Frontend:** React + Vite + Tailwind (`my-react-app/`)
- **Backend:** FastAPI (`backend/`)
- **Data / streaming:** PostgreSQL + pgvector, Redis, Kafka (via Docker Compose)
- **Cloud (deploy):** single EC2 running this same Docker stack, plus AWS Bedrock, S3, CloudWatch, Cognito/IAM

> Status: **project initialization**. The backend currently only proves the
> plumbing works (API up + Postgres/Redis/Kafka reachable). Fraud-detection
> logic is added in later phases.

---

## Prerequisites

- Docker Desktop (running)
- AWS CLI (for deployment) — `aws configure` with an IAM user
- Node 18+ and npm (for the frontend)

## Run the backend stack (local)

```bash
cp .env.example .env
docker compose up --build
```

This starts four containers: `postgres`, `redis`, `kafka`, `backend`.

Verify once everything is healthy:

| Check | URL |
|---|---|
| API liveness | http://localhost:8000/health |
| Dependency connectivity | http://localhost:8000/health/deps |
| API docs (Swagger) | http://localhost:8000/docs |

`/health/deps` should report `postgres`, `redis`, and `kafka` all `ok`.

Stop the stack (keeps data):

```bash
docker compose down
```

Wipe data volumes too:

```bash
docker compose down -v
```

## Run the frontend (local)

```bash
cd my-react-app
npm install
npm run dev
```

Opens at http://localhost:5173.

---

## Service ports

| Service | In-network address | From host machine |
|---|---|---|
| Postgres | `postgres:5432` | `localhost:5433` |
| Redis | `redis:6379` | `localhost:6379` |
| Kafka | `kafka:9092` | `localhost:29092` |
| Backend | `backend:8000` | `localhost:8000` |
