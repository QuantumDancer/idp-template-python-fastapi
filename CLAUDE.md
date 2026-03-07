# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository role

This is a **Backstage software template** that scaffolds new Python FastAPI services. It has three parts:

- `app/` — the FastAPI application skeleton (templated with `${{ values.* }}` placeholders)
- `deployment/` — Helm chart for the GitOps/ArgoCD deployment repo (coming soon)
- `template.yaml` — the Backstage scaffolder definition (parameters, steps, outputs)

When Backstage runs the template, it renders each subdirectory and publishes them as separate repos. The `app/` directory is the primary focus for application logic.

## Commands (run from `app/`)

```bash
uv sync --group dev                          # install all deps including dev
uv run uvicorn app.main:app --reload         # run dev server
uv run pytest                                # run all tests
uv run pytest tests/test_health.py           # run a single test file
uv run ruff check .                          # lint
uv run ruff format .                         # format
```

## Architecture

**Entry point:** `app/app/main.py` — `create_app()` factory returns the FastAPI instance; module-level `app = create_app()` is the ASGI target for uvicorn.

**Routing:** `app/app/api/router.py` mounts `v1_router` at `/api/v1`. Add new resources in `app/app/api/v1/` as separate router files, then register them in `app/app/api/v1/router.py`.

**Config:** `app/app/core/config.py` — `Settings(BaseSettings)` reads env vars and `.env`. Retrieved via `get_settings()` (lru_cache singleton). In tests, override with `app.dependency_overrides[get_settings] = lambda: my_test_settings`.

**Logging:** `app/app/core/logging.py` — `setup_logging()` configures structlog with `ProcessorFormatter` bridging stdlib loggers (uvicorn, httpx, etc.) into the same structured output. Called during lifespan startup. Dev: pretty console. Non-dev: JSON.

**Middleware order (LIFO — last added = outermost):**

1. `CORSMiddleware` — outermost (handles preflight before anything else)
2. `CorrelationIdMiddleware(header_name="X-Correlation-ID")` — injects correlation ID into structlog context
3. `Instrumentator` — innermost (measures handler time, not middleware overhead)

**OpenTelemetry:** Initialized lazily in `_setup_otel()` — imports only happen when `otel_exporter_otlp_endpoint` is set, so there are no side effects in tests.

**Schemas:** `app/app/schemas/__init__.py` — Pydantic response models live here.

## Backstage template variables

Files in `app/` and `deployment/` use `${{ values.* }}` syntax. Key values:

| Variable             | Source                                               |
| -------------------- | ---------------------------------------------------- |
| `values.name`        | Service display name                                 |
| `values.slug`        | Lowercased, hyphenated name                          |
| `values.componentId` | `<system>-<slug>`                                    |
| `values.description` | Short description                                    |
| `values.owner`       | Backstage group ref                                  |
| `values.system`      | Backstage system name                                |
| `values.teamName`    | Bare team name (stripped of `group:default/` prefix) |

These placeholders must remain valid in template files — do not replace them with literal values.
