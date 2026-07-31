import logging

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure root logging for any entry point (web app, worker, init script).

    Output goes to stderr, which systemd captures into the journal. INFO in
    production, DEBUG otherwise. Idempotent: basicConfig is a no-op if the
    root logger already has handlers.
    """
    logging.basicConfig(
        level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # httpx logs a line per request at INFO; the worker makes many
    logging.getLogger("httpx").setLevel(logging.WARNING)
