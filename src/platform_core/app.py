"""FastAPI application factory.

Stage 8.1 skeleton: shell + persona picker. No business logic, no DB I/O.
Database connectivity is wired up once Postgres is reachable (Stage 8.1 T-6003).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from platform_core.settings import get_settings
from platform_core.web.routes import findings, home, login, profile, reports


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ACEN Gravity (POC V1)",
        version="0.0.1",
        docs_url="/_internal/docs" if settings.app_env == "development" else None,
        redoc_url=None,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key,
        same_site="lax",
        https_only=False,  # POC runs on localhost
    )

    app.mount(
        "/static",
        StaticFiles(directory=str(settings.static_dir)),
        name="static",
    )

    app.include_router(login.router)
    app.include_router(home.router)
    app.include_router(profile.router)
    app.include_router(findings.router)
    app.include_router(reports.router)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
