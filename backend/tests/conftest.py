"""Pytest test fixtures and configuration."""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import init_db
from app.main import create_app


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup temporary database for isolated test execution."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    settings.database_path = db_path
    settings.environment = "development"
    settings.demo_mode = True
    settings.oidc_enabled = False

    init_db(db_path)

    yield

    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    app = create_app()
    return TestClient(app)
