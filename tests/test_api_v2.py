import pytest
from fastapi.testclient import TestClient
import io
import json

from backend.main import app
from backend.database import Base, engine

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    # Provide a new test client to ensure state isolation
    return TestClient(app)

class TestVideoStreaming:
    def _create_case_and_evidence(self, client) -> tuple[str, str]:
        resp = client.post("/api/cases", json={
            "case_number": "STREAM-TEST-001",
            "title": "Stream Test",
            "investigator": "Test",
        })
        case_id = resp.json()["id"]

        test_content = b"fake video data 0123456789"
        resp = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("test.mp4", io.BytesIO(test_content), "video/mp4")},
            data={"evidence_type": "video"},
        )
        evidence_id = resp.json()["id"]
        return case_id, evidence_id

    def test_stream_endpoint_full(self, client):
        _, evidence_id = self._create_case_and_evidence(client)
        resp = client.get(f"/api/evidence/{evidence_id}/stream")
        print(resp.json() if resp.status_code != 200 else resp.content)
        assert resp.status_code == 200
        assert resp.content == b"fake video data 0123456789"

    def test_stream_endpoint_range(self, client):
        _, evidence_id = self._create_case_and_evidence(client)
        headers = {"Range": "bytes=5-15"}
        resp = client.get(f"/api/evidence/{evidence_id}/stream", headers=headers)
        assert resp.status_code == 206
        assert resp.content == b"video data "
        
    def test_stream_invalid_evidence(self, client):
        resp = client.get("/api/evidence/nonexistent-id/stream")
        assert resp.status_code == 404

class TestTimeline:
    def test_timeline_aggregation(self, client):
        resp = client.post("/api/cases", json={
            "case_number": "TIMELINE-001",
            "title": "Timeline Test",
            "investigator": "Test",
        })
        case_id = resp.json()["id"]
        
        # Test timeline has case creation event
        resp = client.get(f"/api/cases/{case_id}/timeline")
        print(resp.json() if resp.status_code != 200 else resp.content)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(e["type"] == "CASE_CREATED" for e in data["events"])
        
        # Add evidence
        test_content = b"fake video data"
        resp = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("test.mp4", io.BytesIO(test_content), "video/mp4")},
            data={"evidence_type": "video"},
        )
        
        # Check timeline again
        resp = client.get(f"/api/cases/{case_id}/timeline")
        data = resp.json()
        assert any(e["type"] == "EVIDENCE_INGESTED" for e in data["events"])

class TestReportsAndTrust:
    def test_report_generation(self, client):
        resp = client.post("/api/cases", json={
            "case_number": "REPORT-TEST-001",
            "title": "Report Test",
            "investigator": "Test",
        })
        case_id = resp.json()["id"]
        
        resp = client.post(f"/api/cases/{case_id}/report")
        print(resp.json() if resp.status_code != 200 else resp.content)
        assert resp.status_code == 200
        data = resp.json()
        assert "download_url" in data
        assert "sha256" in data
        
        # Test download
        resp = client.get(data["download_url"])
        print(resp.json() if resp.status_code != 200 else resp.content)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
