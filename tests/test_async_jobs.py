import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.models import Evidence, Case, Job

@pytest.fixture(autouse=True)
def setup_jobs_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Clear overrides for auth or set them to investigator
    from backend.auth import get_current_user, get_current_investigator, get_current_auditor
    from backend.models import User
    
    mock_user = User(id="test", username="test", role="investigator", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_investigator] = lambda: mock_user
    app.dependency_overrides[get_current_auditor] = lambda: mock_user
    
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

def test_async_analysis_deduplication(monkeypatch):
    client = TestClient(app)
    
    # Mock background_analyze so it doesn't run synchronously in TestClient
    from backend.api.analysis import background_analyze
    monkeypatch.setattr("backend.api.analysis.background_analyze", lambda *args, **kwargs: None)
    
    db = SessionLocal()
    c = Case(id="c1", case_number="C1", title="T", investigator="test", investigator_id="test")
    e = Evidence(id="e1", case_id="c1", filename="v.mp4", original_filename="v.mp4", storage_path="/dev/null", sha256="hash", size=123)
    db.add(c)
    db.add(e)
    db.commit()
    db.close()
    
    # Request analysis
    res1 = client.post("/api/evidence/e1/analyze_async")
    assert res1.status_code == 200
    job1 = res1.json()
    assert job1["status"] == "QUEUED"
    
    # Request again - should return the same job since background_analyze didn't run
    res2 = client.post("/api/evidence/e1/analyze_async")
    assert res2.status_code == 200
    job2 = res2.json()
    assert job1["id"] == job2["id"]
    
def test_job_status_retrieval():
    client = TestClient(app)
    
    db = SessionLocal()
    j = Job(id="j1", evidence_id="e1", case_id="c1", job_type="AI_ANALYSIS", status="PROCESSING", progress=50.0)
    db.add(j)
    db.commit()
    db.close()
    
    res = client.get("/api/jobs/j1")
    assert res.status_code == 200
    assert res.json()["status"] == "PROCESSING"
    assert res.json()["progress"] == 50.0
