import pytest
from pathlib import Path
from backend.services.recovery import RecoveryEngine
from backend.models import Evidence

def test_recovery_engine_fixtures():
    from unittest.mock import MagicMock
    db = MagicMock()
    engine = RecoveryEngine(db)
    engine.ledger.append_event = MagicMock()
    
    # Check that generic strategy exists
    names = [s.name() for s in engine.strategies]
    assert "Validator" in names
    assert "MetadataRecovery" in names
    assert "raw_video_carver" in names
    
    # 1. Valid MP4 (with ftyp)
    valid_path = Path("tests/fixtures/recovery/valid.mp4")
    with open(valid_path, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42\x00\x00\x08\x00mdat")
        f.write(b"\x00" * 300 * 1024) # Ensure it's large enough (>256KB MIN_SEGMENT_SIZE)

    evidence_valid = Evidence(id="mock-valid", case_id="mock-case", storage_path=str(valid_path))
    results = engine.recover(evidence_valid, use_demo=False)
    assert len(results) > 0
    assert results[0].validation_status == "CANDIDATE"

    # 2. Random binary -> REJECTED (no segments recovered)
    random_path = Path("tests/fixtures/recovery/random.bin")
    with open(random_path, "wb") as f:
        import os
        f.write(os.urandom(300 * 1024))
    
    evidence_rand = Evidence(id="mock-rand", case_id="mock-case", storage_path=str(random_path))
    results_rand = engine.recover(evidence_rand, use_demo=False)
    assert len(results_rand) == 0

    # 3. Corrupt MP4 (ftyp but no moov, missing atoms, or corrupted payload)
    corrupt_path = Path("tests/fixtures/recovery/corrupt.mp4")
    with open(corrupt_path, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42")
        f.write(b"\xFF\xFF" * (150 * 1024)) # 300KB
    
    evidence_corrupt = Evidence(id="mock-corrupt", case_id="mock-case", storage_path=str(corrupt_path))
    results_corrupt = engine.recover(evidence_corrupt, use_demo=False)
    # The carver will find ftyp but confidence should be lower if no moov
    assert len(results_corrupt) > 0
    assert results_corrupt[0].confidence < 0.85
