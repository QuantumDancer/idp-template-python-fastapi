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

```
deployment/
├── Chart.yaml                  # Chart name and version (uses ${{ values.componentId }})
├── values.yaml                 # Base values: image repo, probes, ESO vault path, httpRoute
├── environments/
│   ├── homelab.yaml            # homelab overrides: image.tag (CI-managed), hostname, replicas
│   ├── development.yaml        # development overrides
│   └── production.yaml         # production overrides: autoscaling enabled, higher replicas
└── templates/
    ├── _helpers.tpl            # fullname, labels, selectorLabels, serviceAccountName
    ├── deployment.yaml         # Deployment; replica count suppressed when HPA is enabled
    ├── service.yaml            # ClusterIP Service on port 8000
    ├── serviceaccount.yaml     # ServiceAccount (no RBAC — app doesn't need cluster access)
    ├── httproute.yaml          # Gateway API HTTPRoute; parent ref: external/gateway
    ├── hpa.yaml                # HPA (only rendered when autoscaling.enabled: true)
    └── image-pull-secret.yaml  # ESO ExternalSecret pulling registry creds from Vault
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

`templates/image-pull-secret.yaml` creates an ESO `ExternalSecret` backed by the `vault-backend`
ClusterSecretStore. The Vault path is set in `values.yaml` under `imagePullSecret.vaultPath` and
must expose three keys: `registry`, `username`, `password`.

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

## Template authoring notes

- `app/` and `deployment/` are rendered separately by `fetch:template` and published as distinct repos.
- `deployment/CLAUDE.md` is written for Claude working in the scaffolded deployment repo — it uses `${{ values.* }}` so it renders with the concrete service name, vault path, etc.
- Helm template syntax (`{{ }}`) passes through unchanged; only `${{ }}` is processed by Backstage.
- Named templates in `deployment/templates/_helpers.tpl` are prefixed with `${{ values.componentId }}` so they render to a chart-specific prefix (e.g. `orders-my-service.fullname`).
