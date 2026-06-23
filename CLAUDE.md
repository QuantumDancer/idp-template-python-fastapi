# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository role

This is a **Backstage software template** that scaffolds new Python FastAPI services. It has three parts:

- `app/` — the FastAPI application skeleton (templated with `${{ values.* }}` placeholders)
- `deployment/` — Helm chart for the GitOps/ArgoCD deployment repo
- `template.yaml` — the Backstage scaffolder definition (parameters, steps, outputs)

When Backstage runs the template, it renders each subdirectory and publishes them as separate repos. The `app/` directory is the primary focus for application logic.

## App (`app/`)

### Commands (run from `app/`)

```bash
uv sync --group dev                          # install all deps including dev
uv run uvicorn app.main:app --reload         # run dev server
uv run pytest                                # run all tests
uv run pytest tests/test_health.py           # run a single test file
uv run ruff check .                          # lint
uv run ruff format .                         # format
```

### Architecture

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

## Deployment (`deployment/`)

Helm chart published to a separate `-deployment` GitOps repo and managed by ArgoCD.

### Structure

The chart renders a single `idp.rottler.io/v1alpha1` WebService CR; the Crossplane composition
behind it produces the Deployment, Service, HTTPRoute, image-pull ExternalSecret, ServiceMonitor
and PodDisruptionBudget.

```
deployment/
├── Chart.yaml                  # Chart name and version (uses ${{ values.componentId }})
├── values.yaml                 # Per-environment base values: environment, image.tag, scaling
├── environments/
│   ├── homelab.yaml            # homelab overrides: image.tag (CI-managed), scaling.min: 1
│   ├── development.yaml        # development overrides: image.tag
│   └── production.yaml         # production overrides: scaling min 2 / max 10 (CPU HPA)
└── templates/
    ├── webservice.yaml         # the WebService CR — static config hard-coded, per-env templated
    └── NOTES.txt               # post-install hints
```

### Commands (run from `deployment/`)

```bash
helm lint . -f values.yaml -f environments/homelab.yaml          # validate
helm template <name> . -f values.yaml -f environments/homelab.yaml  # render
```

### Environment overlay pattern

`values.yaml` holds defaults. `environments/<env>.yaml` overrides are merged on top at deploy time.
CI writes only `image.tag` in the environment file on each push to `main`:

```bash
yq -i ".image.tag = \"${CI_COMMIT_SHORT_SHA}\"" environments/${ENVIRONMENT}.yaml
```

| Environment file                | Cluster env   | ArgoCD branch | Hostname pattern                        |
| ------------------------------- | ------------- | ------------- | --------------------------------------- |
| `environments/homelab.yaml`     | `homelab`     | `development` | `<hostname>.k8s.home.rottlr.de`         |
| `environments/development.yaml` | `development` | `development` | `<hostname>.dev.idp.rottlr.de`          |
| `environments/production.yaml`  | `production`  | `production`  | `<hostname>.prod.idp.rottlr.de`         |

### Image pull secret

The platform-standard group pull secret is composed automatically by the WebService composition
from Vault (`idp/platform/argocd/idp-group-pull-secret`); the chart no longer carries an
image-pull manifest.

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
| `values.hostname`    | Subdomain → the WebService `expose.hostname`         |
| `values.exposePath`  | `expose.path`: `/` (standalone) or `/api` (behind a frontend), from the `exposure` parameter |

These placeholders must remain valid in template files — do not replace them with literal values.

## Template authoring notes

- `app/` and `deployment/` are rendered separately by `fetch:template` and published as distinct repos.
- `deployment/CLAUDE.md` is written for Claude working in the scaffolded deployment repo — it uses `${{ values.* }}` so it renders with the concrete service name, vault path, etc.
- Helm template syntax (`{{ }}`) passes through unchanged; only `${{ }}` is processed by Backstage.
- `deployment/templates/webservice.yaml` mixes both: Helm `{{ .Release.* }}`/`{{ .Values.* }}` for per-environment values and `${{ values.* }}` for scaffolder-time identity (team, componentId, hostname, slug).

## TODO

- **Validate `app/uv.lock` before publishing.** A corrupt lockfile (e.g. a
  duplicated root `[[package]]` block) is invisible here because `${{ values.slug }}`
  is still abstract, but it breaks every scaffolded repo's `lint`/`test` jobs at
  `uv sync --frozen` with `Found duplicate package <slug>==0.1.0 @ virtual+.`. Add a
  template-level CI guard (no `.gitlab-ci.yml` exists at the template root yet) that
  renders the placeholders to a throwaway slug — e.g. `sed 's/${{ '"'"' values.slug
  }}/check-app/g'` over `app/pyproject.toml` and `app/uv.lock` — then runs
  `uv lock --check` (and ideally `uv sync --frozen`) in that rendered dir so a bad
  lock fails the template repo's own pipeline instead of the consumer's.
