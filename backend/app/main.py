"""FastAPI application entrypoint and route configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import pathlib

from app.core.config import settings
from app.core.database import init_db
from app.api.routes_auth import router as auth_router
from app.api.routes_sandbox import router as sandbox_router
from app.api.routes_search import router as search_router
from app.api.routes_sessions import router as sessions_router
from app.api.routes_analytics import router as analytics_router


def get_version_metadata() -> str:
    """Read version metadata from portfolio.json or pyproject.toml."""
    try:
        root_dir = pathlib.Path(__file__).resolve().parent.parent.parent
        portfolio_file = root_dir / "portfolio.json"
        if portfolio_file.exists():
            data = json.loads(portfolio_file.read_text())
            return data.get("version", "1.0.0")
    except Exception:
        pass
    return "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Ensure database tables and FTS5 indexes are initialized
    init_db()
    yield


def create_app() -> FastAPI:
    """Application factory for Lumen Station."""
    version = get_version_metadata()
    application = FastAPI(
        title="Lumen Station API",
        description="Context window optimization and tool sandboxing proxy for AI coding agents",
        version=version,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health")
    def health_check():
        return {
            "status": "healthy",
            "service": "lumen-station",
            "environment": settings.environment,
            "demo_mode": settings.demo_mode,
        }

    @application.get("/api/info")
    def info():
        return {
            "name": "lumen-station-alan-vo",
            "version": get_version_metadata(),
            "domain": "AI/ML developer tools",
            "auth": "oidc-keycloak-saml-broker",
        }

    # Mount API routers
    application.include_router(auth_router)
    application.include_router(sandbox_router)
    application.include_router(search_router)
    application.include_router(sessions_router)
    application.include_router(analytics_router)

    return application


app = create_app()
