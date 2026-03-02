from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging

logger = structlog.get_logger(__name__)


def _setup_otel(settings: Settings) -> None:
    """Initialize OpenTelemetry tracing. No-op when endpoint is not configured.

    OTel SDK imports are lazy so importing this module never installs a global
    tracer provider when tracing is disabled, avoiding side effects in tests
    and environments that don't need tracing.
    """
    if not settings.otel_exporter_otlp_endpoint:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({SERVICE_NAME: settings.app_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument()
    logger.info("otel_tracing_enabled", endpoint=settings.otel_exporter_otlp_endpoint)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(settings.log_level, as_json=settings.log_as_json)
    _setup_otel(settings)
    logger.info(
        "app_startup",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.environment,
    )
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    # Swagger UI and ReDoc are disabled in production to avoid exposing the API surface
    docs_url = None if settings.environment == "production" else "/docs"
    redoc_url = None if settings.environment == "production" else "/redoc"

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_tags=[
            {
                "name": "health",
                "description": "Kubernetes liveness and readiness probes",
            },
        ],
        lifespan=lifespan,
    )

    app.include_router(api_router)

    # Middleware is applied LIFO: last-registered = outermost (first to handle requests).
    # CORS must be outermost to handle preflight OPTIONS before anything else runs.
    # Prometheus is innermost so it measures route handler time, not middleware overhead.
    Instrumentator().instrument(app).expose(app)  # innermost
    app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")
    app.add_middleware(  # outermost
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
