import pytest
from fastapi.testclient import TestClient
from apps.backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)
