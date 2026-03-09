# Spark Log Analyzer

> Reduce gigabyte-scale Apache Spark event logs to actionable insights — with optional AI-powered bottleneck diagnostics.

![Version](https://img.shields.io/badge/version-2.0.0-orange)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)

---

## Overview

Spark applications generate massive event logs that are nearly impossible to inspect manually. This tool:

1. **Reduces** a ZIP of Spark event logs to a structured summary (stage metrics, task statistics, skew detection).
2. **Analyzes** the reduced report with an LLM (OpenAI or Anthropic) to surface bottlenecks and recommend PySpark fixes.
3. **Presents** everything in a clean web interface with download options.

No CLI. Everything is driven through the browser.

---

## Project Structure

```
log-sparkui/
├── backend/
│   ├── app.py                   # FastAPI entrypoint
│   ├── api/
│   │   └── routes.py            # Controllers (thin layer, delegates to services)
│   ├── services/
│   │   ├── log_reducer.py       # CoR pipeline + Strategy renderers
│   │   ├── llm_analyzer.py      # LLM prompt + response handling
│   │   └── job_service.py       # Orchestration facade
│   ├── adapters/
│   │   └── llm_adapters.py      # OpenAI / Anthropic adapters (Factory + Singleton)
│   ├── models/
│   │   └── job.py               # Pydantic domain models
│   ├── utils/
│   │   ├── config.py            # Settings (pydantic-settings, Singleton via lru_cache)
│   │   └── logging_config.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_log_reducer.py
│   │   └── test_llm_adapters.py
│   └── requirements.txt
├── frontend/
│   └── index.html               # Single-file SPA
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Design Patterns Applied

| Pattern | Where | Purpose |
|---|---|---|
| **Chain of Responsibility** | `log_reducer.py` — `*Handler` classes | Each step (load → parse meta → aggregate → build summary) passes a context dict down the chain |
| **Strategy** | `MarkdownRenderer`, `CompactMarkdownRenderer`, `JsonRenderer` | Swap output format without changing pipeline logic |
| **Iterator** | `_iter_events()` in `log_reducer.py` | Streams JSON events line-by-line from ZIP — memory efficient |
| **Factory** | `StageAggregationHandler._build_stage()`, `LLMClientFactory` | Construct complex objects in one place |
| **Singleton** | `get_settings()` via `lru_cache`, `LLMClientFactory._instances` | One config object and one LLM client per (provider, key) pair |
| **Adapter** | `OpenAIAdapter`, `AnthropicAdapter`, `NoOpAdapter` | Uniform `complete(prompt)` interface across providers |
| **Facade** | `LogReducer`, `JobService` | Hide pipeline complexity behind simple `.reduce()` / `.process()` calls |
| **Dependency Injection** | `LLMAnalyzer(adapter=...)`, `JobService(reducer=..., analyzer=...)` | Services accept injected dependencies — fully mockable in tests |

---

## Quick Start

### Local (Python)

```bash
# 1. Clone and set up environment
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (optional — skip for no-LLM mode)
cp ../.env.example .env
# Edit .env with your API key

# 3. Run
uvicorn backend.app:app --reload --port 8000

# 4. Open browser
open http://localhost:8000
```

### Docker

```bash
# Copy and configure
cp .env.example .env
# Edit .env

# Build & run
docker compose up --build

# Open
open http://localhost:8000
```

---

## Usage

1. **Upload** your Spark event log ZIP (produced by `spark.eventLog.enabled=true`).
2. *(Optional)* Upload `.py` source files for code-level recommendations.
3. *(Optional)* Select a language using the dropdown in the authentication section — English is the default; choosing Português will translate all UI labels and send a Portuguese prompt to the LLM.
4. *(Optional)* Select an LLM provider and enter your API key (or set env vars).
5. Click **Analyze →** and wait for processing.
6. Review the KPI cards, stage table, and AI analysis panel.
6. **Download** the report as Markdown or JSON.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload` | Submit ZIP + options; returns `job_id` |
| `GET` | `/api/status/{job_id}` | Poll for job status and results |
| `GET` | `/api/download/{job_id}/{format}` | Download report (`md` or `json`) |

### Upload form fields

| Field | Type | Required | Description |
|---|---|---|---|
| `log_zip` | file | ✅ | `.zip` containing Spark event log files |
| `pyspark_files` | file[] | — | `.py` job source files |
| `compact` | bool | — | Generate shorter report (default: false) |
| `user_id` | string | — | OAuth2 user ID (from login) |
| `provider` | string | — | `openai`, `anthropic`, or `gemini` (OAuth2) |
| `api_key` | string | — | API key (legacy BYOK, overrides env var) |

---

## OAuth2 Authentication (Recommended)

Instead of pasting API keys, use **OAuth2** to authenticate safely with LLM providers. This tool supports:

- **OpenAI**
- **Anthropic Claude**
- **Google Generative AI (Gemini)**

### Setup OAuth2

1. **Register your app** with each provider:
   - [OpenAI Console](https://platform.openai.com/account/api-keys)
   - [Anthropic Console](https://console.anthropic.com/settings)
   - [Google Cloud Console](https://console.cloud.google.com)

2. **Get OAuth2 credentials** (Client ID + Secret) and add to `.env`:
   ```
   OPENAI_OAUTH_CLIENT_ID=your-openai-client-id
   OPENAI_OAUTH_CLIENT_SECRET=your-openai-client-secret
   ANTHROPIC_OAUTH_CLIENT_ID=your-anthropic-client-id
   ANTHROPIC_OAUTH_CLIENT_SECRET=your-anthropic-client-secret
   GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
   SECRET_KEY=your-random-secret-key
   FRONTEND_URL=http://localhost:8000
   ```

3. **On the web interface**, click one of the OAuth login buttons (e.g., "🔑 Login with OpenAI").

4. **Authorize** the app on the provider's login page.

5. **Start analyzing** — your tokens are stored securely in Redis!

### BYOK Fallback (Legacy)

If you prefer not to use OAuth2, you can still provide your API keys manually:

- **OpenAI**: Set `OPENAI_API_KEY` in `.env` or paste in the web form
- **Anthropic**: Set `ANTHROPIC_API_KEY` in `.env` or paste in the web form
- **Google Gemini**: Not supported via BYOK (OAuth2 only)

**Note**: BYOK is less secure than OAuth2 as keys travel through the browser. Use OAuth2 when possible!

### OAuth2 Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/auth/login/{provider}` | Redirect to provider login |
| `GET` | `/api/auth/callback/{provider}` | OAuth callback (auto-handled) |
| `POST` | `/api/auth/logout/{provider}` | Logout and revoke token |
| `GET` | `/api/auth/providers/{user_id}` | List connected providers |
| `GET` | `/api/auth/status/{user_id}/{provider}` | Check token validity |

---

## Running Locally

### Prerequisites

- Python 3.12+
- Redis (for async task queue)

### Setup

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start Redis (via Docker or system)
docker run -d -p 6379:6379 redis:7-alpine

# Set environment variables (optional)
export OPENAI_API_KEY=sk-...
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Start the web server
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start Celery workers
celery -A backend.celery_app worker --loglevel=info
```

Access http://localhost:8000

---

## Docker (Recommended)

```bash
# Build and run all services (FastAPI + Redis + Celery workers)
docker-compose up --build

# Or run in background
docker-compose up -d
```

This starts:
- **Redis** on port 6379
- **FastAPI app** on port 8000
- **Celery workers** for async processing

---

## Security & Token Management

📖 **How OAuth2 tokens are handled:**

1. **Storage**: Tokens are stored in Redis with automatic expiration (TTL based on provider settings).
2. **Encryption**: Token payloads include creation timestamp and provider metadata; sensitive data remains encrypted in Redis.
3. **Session-based**: Each user is assigned a unique `user_id` upon first OAuth login; this ID is used to retrieve tokens from Redis during analysis.
4. **Automatic cleanup**: Tokens expire and are automatically removed from Redis based on provider requirements (typically 24-90 days).
5. **No persistence**: Tokens are **never** saved to disk or database; they live only in Redis memory.

⚠️ **Production considerations:**
- Use strong `SECRET_KEY` for JWT state tokens (change from default!).
- Use HTTPS in production to protect OAuth redirects and session cookies.
- Implement rate limiting on `/api/auth/*` endpoints to prevent abuse.
- Monitor token storage size in Redis and consider adding token rotation policies.

---

## Running Tests

## Configuration Reference

| Environment Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (auto-selects `openai` as provider) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (auto-selects `anthropic` as provider) |
| `GOOGLE_API_KEY` | — | Google Gemini API key (auto-selects `google` as provider) |
| `LLM_PROVIDER` | — | Explicit override: `openai`, `anthropic`, or `google` |
| `LLM_API_KEY` | — | Unified key (lower priority than above) |
| `MAX_ZIP_MB` | `500` | Maximum ZIP size accepted |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON array string) |

**Note**: While OAuth2 is the recommended authentication method for security, BYOK (Bring Your Own Key) is still supported as a fallback option. Users can provide their own API keys directly in the UI when not using OAuth2.

---

## Possible Extensions

- **Redis job store** — replace the in-memory `_jobs` dict for multi-process deployments.
- **Celery workers** — move `_run_job` to a task queue for better scalability.
- **Additional log formats** — add new `BaseHandler` subclasses for Flink, Databricks runtime logs.
- **New LLM providers** — add a `GeminiAdapter` or `BedrockAdapter`; register in `LLMClientFactory._build()`.
- **Authentication** — add OAuth2/JWT middleware to the FastAPI app.
- **Persistent storage** — swap in PostgreSQL or S3 for job results.
- **Streaming responses** — use SSE to stream LLM output token-by-token to the browser.
- **Comparison view** — diff two runs side-by-side to detect regressions.

---

## License

MIT — see `LICENSE`.
