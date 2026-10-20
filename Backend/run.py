"""Entrypoint script to run the CineBot FastAPI server with Uvicorn."""

from __future__ import annotations

import uvicorn

from app.config import get_settings


def main() -> None:
    """Start Uvicorn server with settings from environment."""
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
