import pytest
from fastapi.testclient import TestClient
from apps.graph_api.main import app


@pytest.fixture
def client():
    return TestClient(app)
