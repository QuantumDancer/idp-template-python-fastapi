# ── Builder ───────────────────────────────────────────────────────────────────
# Uses the official uv image so we get uv without a separate COPY step.
# UV_PYTHON_DOWNLOADS=0 forces uv to use the interpreter bundled in the image
# rather than downloading a separate one, keeping the layer deterministic.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies before copying source so this expensive layer is
# reused on every build where only application code (not lockfile) changed.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy application source, then install the project itself into the venv.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# ── Runtime ───────────────────────────────────────────────────────────────────
# Minimal image: uv and all build tooling are left behind in the builder stage.
FROM python:3.14-slim-bookworm

# Fixed UID/GID (non-zero) makes bind-mounted volume permissions predictable
# across hosts and is required by some container security policies.
RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid 1001 --no-create-home appuser

WORKDIR /app

# Copy the virtualenv and compiled application from the builder.
COPY --from=builder --chown=appuser:appuser /app /app

# Prepend the venv so uvicorn/fastapi are on PATH without activating it.
# PYTHONUNBUFFERED ensures log output is not buffered in the container runtime.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

# Exec form (JSON array) is required so the process receives OS signals
# directly. This is critical for graceful shutdown in orchestrators like Kubernetes.
# Run one uvicorn process per container; scale with replicas, not --workers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
