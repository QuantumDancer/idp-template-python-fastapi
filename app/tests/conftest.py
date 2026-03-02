import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(environment="testing", log_level="WARNING")


@pytest.fixture(scope="session")
def client(test_settings: Settings) -> TestClient:
    """Session-scoped TestClient to avoid re-running lifespan on every test.

    dependency_overrides makes test_settings available to any route handler
    that depends on get_settings(), such as handlers added by template consumers.
    """
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as c:
        yield c
