# CPFB — ARIA Dashboard

FastAPI + React app that scores roles for AI-augmentation/automation potential using BAML-driven LLM calls.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- Node.js 20+ and npm
- An [OpenRouter](https://openrouter.ai/) API key (used by BAML to call Claude)

## Backend

```bash
cd backend
export OPENROUTER_API_KEY=sk-or-...
uv sync
uv run uvicorn main:app --reload --port 8000
```

The API listens on `http://localhost:8000`. A SQLite database (`aria.db`) is created automatically on first run.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and is already whitelisted in the backend's CORS config.

## BAML (optional)

The generated BAML client is committed under `backend/baml_client/`. If you change anything in `baml_src/`, regenerate it:

```bash
cd backend
uv run baml-cli generate --from ../baml_src
```
