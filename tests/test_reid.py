import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.ai.recognition.person_reid import PersonReIdentifier
from backend.ai.registry import model_registry
from backend.api.investigation import _cosine, _stored_embedding
from backend.database import Base, engine
from backend.main import app


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_cross_camera_reid_registry_default():
    # As OSNet is not installed, the registry should report UNAVAILABLE
    reid_info = model_registry.models.get("reid")
    if reid_info:
        assert reid_info.status == "UNAVAILABLE", "OSNet Re-ID model should be unavailable initially"


def test_person_reidentifier_graceful_without_model():
    """A missing model file must degrade to UNAVAILABLE, never crash or fake."""
    reid = PersonReIdentifier(model_path="models/does_not_exist.onnx")
    assert reid.is_available() is False
    assert reid.compute_embedding(np.zeros((256, 128, 3), dtype=np.uint8), [0, 0, 64, 128]) is None
    assert reid.name() == "OSNet"


def test_cosine_and_stored_embedding_helpers():
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert _cosine(a, b) == pytest.approx(1.0, abs=1e-5)

    class _Row:
        meta_data = {"embedding": [0.1, 0.2, 0.3]}
        embedding_reference = None

    emb = _stored_embedding(_Row())
    assert emb is not None and emb.shape == (3,)

    class _Empty:
        meta_data = None
        embedding_reference = None

    assert _stored_embedding(_Empty()) is None


def test_cross_camera_search_unavailable_without_model(client):
    """Honesty contract: endpoint must report UNAVAILABLE, not fabricate matches."""
    resp = client.post(
        "/api/investigation/cross-camera-search",
        params={"case_id": "x", "track_id": "t1", "evidence_id": "e1"},
    )
    assert resp.status_code == 503
    assert "MODEL UNAVAILABLE" in resp.json()["detail"]


def test_investigation_search_returns_payload(client):
    """Regression: unified search previously fell through without returning."""
    resp = client.get(
        "/api/investigation/search",
        params={"case_id": "no-such-case", "q": "person"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["results"] == []
    assert body["case_id"] == "no-such-case"
