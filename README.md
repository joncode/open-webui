# Jaco

AI chat that jams with you. Fork of [Open WebUI](https://github.com/open-webui/open-webui).

## Requirements

- Python 3.11 or 3.12
- Node.js 18+
- PostgreSQL with pgvector

## Setup

```bash
# Install Python dependencies
pip3 install -e '.[postgres]'

# Install frontend dependencies
npm install

# Copy and configure environment
cp .env.example .env
```

Edit `.env` with your database URL and API keys.

## Run (Dev)

```bash
# Backend + frontend together
make dev

# Or separately:
make dev-backend    # Python backend on :8080
make dev-frontend   # Vite frontend on :5173
```

Open http://localhost:8080 (backend only) or http://localhost:5173 (with Vite HMR).

## Run (Docker)

```bash
docker compose up -d
```

## Upstream

Original README preserved at [docs/README-WEBUI.md](docs/README-WEBUI.md).
