import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models import User
from backend.auth import get_password_hash

@pytest.fixture(autouse=True)
def setup_auth_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    # Create test users
    users = [
        User(username="investigator1", hashed_password=get_password_hash("pass123"), role="investigator"),
        User(username="auditor1", hashed_password=get_password_hash("pass123"), role="auditor"),
        User(username="admin1", hashed_password=get_password_hash("pass123"), role="admin"),
    ]
    db.add_all(users)
    db.commit()
    db.close()
    
    # Clear overrides so auth is actually tested!
    app.dependency_overrides.clear()
    
    yield
    Base.metadata.drop_all(bind=engine)

def get_token(client: TestClient, username: str) -> str:
    res = client.post("/api/auth/token", data={"username": username, "password": "pass123"})
    return res.json()["access_token"]

def test_registration_forces_investigator():
    client = TestClient(app)
    # Attempt to register as admin
    res = client.post("/api/auth/register", json={
        "username": "hacker",
        "password": "password123",
        "role": "admin"
    })
    assert res.status_code == 200
    assert res.json()["role"] == "investigator"
    
    # Duplicate should fail
    res2 = client.post("/api/auth/register", json={
        "username": "hacker",
        "password": "password123",
        "role": "investigator"
    })
    assert res2.status_code == 400

def test_login_success_and_fail():
    client = TestClient(app)
    # Fail
    res = client.post("/api/auth/token", data={"username": "admin1", "password": "wrong"})
    assert res.status_code == 401
    
    # Success
    res = client.post("/api/auth/token", data={"username": "admin1", "password": "pass123"})
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_rbac_investigator_access():
    client = TestClient(app)
    token = get_token(client, "investigator1")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Can access cases (Investigator route)
    res = client.get("/api/cases", headers=headers)
    assert res.status_code == 200
    
    # Can access chain (User route)
    res = client.get("/api/chain/evidence/123", headers=headers)
    assert res.status_code in [200, 404]  # 404 means route executed but no data, which is fine

def test_rbac_auditor_access():
    client = TestClient(app)
    token = get_token(client, "auditor1")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Cannot access cases (Requires Investigator)
    res = client.get("/api/cases", headers=headers)
    assert res.status_code == 403
    
    # Can access chain (User/Auditor route)
    res = client.get("/api/chain/evidence/123", headers=headers)
    assert res.status_code in [200, 404]

def test_unauthenticated():
    client = TestClient(app)
    # No auth header
    res = client.get("/api/cases")
    assert res.status_code == 401
    
    # Invalid token
    res = client.get("/api/cases", headers={"Authorization": "Bearer badtoken"})
    assert res.status_code == 401
