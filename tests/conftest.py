import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import get_current_user, get_current_investigator, get_current_auditor
from backend.models import User
from backend.database import Base, engine, SessionLocal

@pytest.fixture(autouse=True)
def reset_db_conftest():
    # Allow tests to drop/create
    yield

@pytest.fixture
def mock_investigator():
    return User(id="test-inv", username="testuser", role="investigator", is_active=True)

@pytest.fixture
def mock_auditor():
    return User(id="test-aud", username="auditor", role="auditor", is_active=True)

@pytest.fixture
def mock_admin():
    return User(id="test-adm", username="admin", role="admin", is_active=True)

@pytest.fixture(autouse=True)
def override_auth_dependencies(mock_investigator):
    """
    By default, make all endpoints pass authentication for backward compatibility
    with existing tests that do not expect 401s.
    Specific auth tests can clear these overrides using `app.dependency_overrides.clear()`.
    """
    app.dependency_overrides[get_current_user] = lambda: mock_investigator
    app.dependency_overrides[get_current_investigator] = lambda: mock_investigator
    app.dependency_overrides[get_current_auditor] = lambda: mock_investigator
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client():
    return TestClient(app)
