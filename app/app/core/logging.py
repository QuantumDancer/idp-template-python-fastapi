import logging

import structlog


def setup_logging(log_level: str, *, as_json: bool) -> None:
    """Configure structlog and stdlib logging with a shared processor chain.

    stdlib loggers (uvicorn, httpx, etc.) are routed through structlog's
    ProcessorFormatter so they produce output in the same format as application logs.

    merge_contextvars is first so every log record automatically inherits the
    correlation_id bound to structlog's context by CorrelationIdMiddleware.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if as_json
        else structlog.dev.ConsoleRenderer()
    )

    # Applied to every log record (both structlog-native and stdlib)
    shared_processors: list[structlog.types.Processor] = [
        # MUST be first: injects correlation_id (and any other bound context)
        # from asyncio contextvars into the event dict
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # ProcessorFormatter bridges structlog and stdlib logging so uvicorn, httpx, etc.
    # emit records in the same structured format as application code
    formatter = structlog.stdlib.ProcessorFormatter(
        # foreign_pre_chain: only runs for records from stdlib loggers
        foreign_pre_chain=[
            structlog.stdlib.ExtraAdder(),
            *shared_processors,
        ],
        # processors: runs on all records after the pre-chain
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    structlog.configure(
        processors=[
            *shared_processors,
            # Hands the event dict off to ProcessorFormatter for final rendering
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
