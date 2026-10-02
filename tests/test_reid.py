import pytest
from backend.ai.registry import model_registry

def test_cross_camera_reid():
    # As OSNet is not installed, the registry should report UNAVAILABLE
    reid_info = model_registry.models.get("reid")
    if reid_info:
        assert reid_info.status == "UNAVAILABLE", "OSNet Re-ID model should be unavailable initially"
