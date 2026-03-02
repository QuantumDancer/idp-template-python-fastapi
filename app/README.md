# python-fastapi

Production-ready FastAPI starter template. Provides structured logging, Prometheus metrics, distributed tracing (OTel), and Kubernetes health probes out of the box.

## Quick start

```bash
# Install dependencies (including dev tools)
uv sync --group dev

# Start the dev server with hot reload
uv run uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs> for the interactive API explorer (dev only).

## Endpoints

| Path                       | Description                   |
| -------------------------- | ----------------------------- |
| `GET /api/v1/health/live`  | Kubernetes liveness probe     |
| `GET /api/v1/health/ready` | Kubernetes readiness probe    |
| `GET /metrics`             | Prometheus scrape endpoint    |
| `GET /docs`                | Swagger UI (development only) |
| `GET /redoc`               | Redoc UI (development only)   |

## Adding a new resource

1. Create `app/api/v1/widgets.py` with a router:

   ```python
   from fastapi import APIRouter

   router = APIRouter()

   @router.get("/")
   async def list_widgets():
       return []
   ```

2. Mount it in `app/api/v1/router.py`:

   ```python
   from app.api.v1 import widgets
   v1_router.include_router(widgets.router, prefix="/widgets", tags=["widgets"])
   ```

Full URL: `/api/v1/widgets/`. Swagger docs, Prometheus metrics, and correlation IDs are included automatically.

## Configuration

Copy `.env.example` to `.env` and edit as needed.

| Variable                      | Default          | Description                                                                            |
| ----------------------------- | ---------------- | -------------------------------------------------------------------------------------- |
| `APP_NAME`                    | `python-fastapi` | Service name (appears in logs and traces)                                              |
| `APP_VERSION`                 | `0.1.0`          | Service version                                                                        |
| `ENVIRONMENT`                 | `development`    | `development` \| `staging` \| `production`. Controls log format and Swagger visibility |
| `LOG_LEVEL`                   | `INFO`           | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL`                                |
| `CORS_ORIGINS`                | `["*"]`          | JSON list of allowed CORS origins                                                      |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(unset)_        | OTLP/HTTP endpoint; tracing is disabled when unset                                     |

## Running tests

```bash
uv run pytest
```

## Enabling distributed tracing

Point `OTEL_EXPORTER_OTLP_ENDPOINT` at a running OpenTelemetry Collector:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces uv run uvicorn app.main:app
```

## Observability overview

| Signal         | Mechanism                         | Endpoint / format                                       |
| -------------- | --------------------------------- | ------------------------------------------------------- |
| Logs           | structlog + stdlib bridge         | stdout (JSON in non-dev)                                |
| Traces         | OTel SDK + OTLP/HTTP exporter     | configured via env var                                  |
| Metrics        | prometheus-fastapi-instrumentator | `GET /metrics`                                          |
| Correlation ID | asgi-correlation-id middleware    | `X-Correlation-ID` header; injected into every log line |
