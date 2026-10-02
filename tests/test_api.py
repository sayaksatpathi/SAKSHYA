"""
SAKSHYA Tests — API Integration Tests

Tests for FastAPI endpoints: cases, evidence, chain, merkle, trust.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import Base, engine


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# =============================================================================
# Health
# =============================================================================

class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "operational"
        assert "version" in data


# =============================================================================
# Cases
# =============================================================================

class TestCases:
    def test_create_case(self, client):
        resp = client.post("/api/cases", json={
            "case_number": "CASE-2026-001",
            "title": "DVR Evidence Investigation",
            "description": "Test case",
            "investigator": "Test Investigator",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["case_number"] == "CASE-2026-001"
        assert data["status"] == "OPEN"
        assert "id" in data

    def test_duplicate_case_number(self, client):
        payload = {
            "case_number": "CASE-DUP",
            "title": "Test",
            "investigator": "Test",
        }
        resp1 = client.post("/api/cases", json=payload)
        assert resp1.status_code == 201

        resp2 = client.post("/api/cases", json=payload)
        assert resp2.status_code == 409

    def test_list_cases(self, client):
        client.post("/api/cases", json={
            "case_number": "C1",
            "title": "Case 1",
            "investigator": "Inv",
        })
        client.post("/api/cases", json={
            "case_number": "C2",
            "title": "Case 2",
            "investigator": "Inv",
        })

        resp = client.get("/api/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["cases"]) == 2

    def test_get_case(self, client):
        resp = client.post("/api/cases", json={
            "case_number": "C-GET",
            "title": "Get Test",
            "investigator": "Inv",
        })
        case_id = resp.json()["id"]

        resp = client.get(f"/api/cases/{case_id}")
        assert resp.status_code == 200
        assert resp.json()["case_number"] == "C-GET"

    def test_get_nonexistent_case(self, client):
        resp = client.get("/api/cases/nonexistent-id")
        assert resp.status_code == 404


# =============================================================================
# Chain of Custody
# =============================================================================

class TestChain:
    def _create_case(self, client) -> str:
        resp = client.post("/api/cases", json={
            "case_number": "CHAIN-TEST",
            "title": "Chain Test",
            "investigator": "Inv",
        })
        return resp.json()["id"]

    def test_chain_created_on_case(self, client):
        """Case creation should generate a chain event."""
        case_id = self._create_case(client)
        resp = client.get(f"/api/cases/{case_id}/chain")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        assert events[0]["event_type"] == "CASE_CREATED"

    def test_verify_valid_chain(self, client):
        """A fresh chain should verify as valid."""
        case_id = self._create_case(client)
        resp = client.post(f"/api/cases/{case_id}/verify-chain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True

    def test_chain_head(self, client):
        case_id = self._create_case(client)
        resp = client.get(f"/api/cases/{case_id}/chain-head")
        assert resp.status_code == 200
        data = resp.json()
        assert data["chain_head"] is not None
        assert len(data["chain_head"]) == 64


# =============================================================================
# Merkle Tree
# =============================================================================

class TestMerkle:
    def _create_case_with_evidence(self, client) -> str:
        """Create case and upload dummy evidence."""
        resp = client.post("/api/cases", json={
            "case_number": "MERKLE-TEST",
            "title": "Merkle Test",
            "investigator": "Inv",
        })
        case_id = resp.json()["id"]

        # Upload a small test file
        import io
        test_content = b"test evidence content for merkle"
        resp = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("test.mp4", io.BytesIO(test_content), "video/mp4")},
            data={"evidence_type": "video"},
        )
        assert resp.status_code == 201
        return case_id

    def test_build_merkle_tree(self, client):
        case_id = self._create_case_with_evidence(client)
        resp = client.post(f"/api/cases/{case_id}/merkle")
        assert resp.status_code == 201
        data = resp.json()
        assert "root_hash" in data
        assert data["leaf_count"] >= 1

    def test_no_evidence_merkle(self, client):
        resp = client.post("/api/cases", json={
            "case_number": "EMPTY-MERKLE",
            "title": "Empty",
            "investigator": "Inv",
        })
        case_id = resp.json()["id"]

        resp = client.post(f"/api/cases/{case_id}/merkle")
        assert resp.status_code == 400
