"""
SAKSHYA Demo Seed Script

Creates a realistic sample case with evidence, AI results,
chain events, Merkle tree, and trust receipt for demonstration.

Usage:
    python scripts/seed_demo.py

This uses synthetic data — no real forensic evidence or biometric data.
"""

import sys
import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.database import init_db, SessionLocal
from backend.models import Case, Evidence, EvidenceSegment, AIResult, ChainEvent, MerkleRecord
from backend.services.ledger import LedgerService
from backend.crypto.hashing import sha256_string, sha256_bytes
from backend.crypto.merkle import MerkleTree


def create_demo_evidence_file(case_dir: Path, filename: str, content: bytes) -> Path:
    """Create a synthetic evidence file for the demo."""
    file_path = case_dir / filename
    file_path.write_bytes(content)
    return file_path


def seed():
    """Seed the database with a complete demo case."""
    print("=" * 60)
    print("SAKSHYA Demo Seeder")
    print("=" * 60)

    settings.ensure_directories()
    init_db()
    db = SessionLocal()
    ledger = LedgerService(db)

    try:
        # Check if demo case already exists
        existing = db.query(Case).filter(Case.case_number == "CASE-2026-001").first()
        if existing:
            print("Demo case CASE-2026-001 already exists. Skipping.")
            return

        # =====================================================================
        # 1. Create Case
        # =====================================================================
        print("\n[1/10] Creating demo case...")
        case = Case(
            case_number="CASE-2026-001",
            title="DVR Evidence Investigation — Sector 5 CCTV",
            description=(
                "Investigation of surveillance footage from Sector 5 junction. "
                "DVR recovered from premises. Potential deleted footage segments. "
                "Multiple cameras covering the junction area."
            ),
            investigator="Inspector Rajesh Kumar",
            investigator_id="INV-001",
            status="OPEN",
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        print(f"   Case ID: {case.id}")
        print(f"   Case Number: {case.case_number}")

        ledger.append_event(
            case_id=case.id,
            event_type="CASE_CREATED",
            actor=case.investigator,
            meta_data={"case_number": case.case_number, "title": case.title},
        )

        # =====================================================================
        # 2. Create Demo Evidence Files
        # =====================================================================
        print("\n[2/10] Creating demo evidence files...")
        evidence_dir = Path(settings.evidence_storage_path) / case.id
        evidence_dir.mkdir(parents=True, exist_ok=True)

        # Create synthetic "video" files (small files with structured content)
        evidence_items = []

        for i, (cam_name, duration, vendor) in enumerate([
            ("Camera_01_Front_Gate", 1800, "Generic DVR"),
            ("Camera_02_Parking", 1200, "Unknown"),
            ("Camera_03_Junction", 2400, "Generic NVR"),
        ]):
            # Create a synthetic file with identifiable content
            content = (
                f"SAKSHYA_DEMO_EVIDENCE_{cam_name}\n"
                f"Duration: {duration}s\n"
                f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
                f"This is synthetic demo evidence.\n"
            ).encode() + os.urandom(1024)  # Add random bytes to make hashes unique

            filename = f"demo_{cam_name.lower()}.mp4"
            file_path = create_demo_evidence_file(evidence_dir, filename, content)
            file_hash = sha256_bytes(content)

            evidence = Evidence(
                case_id=case.id,
                filename=filename,
                original_filename=f"{cam_name}_2026-09-15.mp4",
                source_device=cam_name,
                source_vendor=vendor,
                evidence_type="video",
                acquisition_method="file_upload",
                size=len(content),
                sha256=file_hash,
                mime_type="video/mp4",
                acquired_by=case.investigator,
                status="INGESTED",
                storage_path=str(file_path),
                codec="H.264",
                resolution="1920x1080",
                fps=25.0,
                duration=float(duration),
                has_audio=False,
                container_format="mp4",
                meta_data={
                    "demo": True,
                    "camera": cam_name,
                    "note": "Synthetic demo evidence file",
                },
            )
            db.add(evidence)
            db.commit()
            db.refresh(evidence)
            evidence_items.append(evidence)

            ledger.append_event(
                case_id=case.id,
                event_type="EVIDENCE_INGESTED",
                actor=case.investigator,
                evidence_id=evidence.id,
                meta_data={
                    "filename": filename,
                    "sha256": file_hash,
                    "size": len(content),
                },
            )
            print(f"   Evidence {i+1}: {filename} (SHA-256: {file_hash[:16]}...)")

        # =====================================================================
        # 3. Create Recovered Segments
        # =====================================================================
        print("\n[3/10] Simulating evidence recovery...")
        recovered_dir = evidence_dir / "recovered"
        recovered_dir.mkdir(exist_ok=True)

        for evidence in evidence_items[:2]:
            for j in range(2):
                seg_content = f"RECOVERED_SEGMENT_{j+1}_{evidence.filename}".encode() + os.urandom(512)
                seg_filename = f"recovered_{evidence.filename.replace('.mp4', '')}_{j+1}.mp4"
                seg_path = recovered_dir / seg_filename
                seg_path.write_bytes(seg_content)

                segment = EvidenceSegment(
                    evidence_id=evidence.id,
                    start_time=j * 30.0,
                    end_time=(j + 1) * 30.0,
                    file_path=str(seg_path),
                    sha256=sha256_bytes(seg_content),
                    size=len(seg_content),
                    recovery_method="demo_simulation",
                    source_offset=j * 65536,
                    confidence=0.85 + (j * 0.05),
                    validation_status="DEMO",
                    meta_data={"demo": True, "note": "Simulated recovery segment"},
                )
                db.add(segment)

            ledger.append_event(
                case_id=case.id,
                event_type="RECOVERY_COMPLETED",
                actor="SAKSHYA Recovery Engine",
                evidence_id=evidence.id,
                meta_data={"segments_recovered": 2, "method": "demo_simulation"},
            )

        db.commit()
        print("   Created 4 recovered segments")

        # =====================================================================
        # 4. Create Demo AI Results
        # =====================================================================
        print("\n[4/10] Creating demo AI detections...")

        demo_detections = [
            # Camera 1 detections
            (0, 30, "face", "face", 0.92, [120, 80, 60, 70], "T001"),
            (0, 30, "object", "person", 0.94, [100, 50, 120, 280], "T001"),
            (0, 60, "object", "car", 0.89, [300, 200, 180, 100], "T002"),
            (0, 60, "plate", "WB12AB1234", 0.91, [340, 280, 70, 25], None),
            (0, 120, "object", "motorcycle", 0.82, [400, 250, 80, 60], "T003"),
            (0, 150, "face", "face", 0.87, [200, 90, 55, 65], "T004"),
            (0, 150, "object", "person", 0.91, [180, 60, 110, 270], "T004"),
            (0, 210, "object", "car", 0.85, [350, 210, 170, 95], "T005"),
            (0, 210, "plate", "KA05CD5678", 0.78, [390, 285, 65, 22], None),
            # Camera 2 detections
            (1, 45, "object", "person", 0.88, [150, 70, 100, 250], "T006"),
            (1, 45, "face", "face", 0.79, [165, 75, 50, 60], "T006"),
            (1, 90, "object", "car", 0.92, [280, 190, 160, 110], "T007"),
            (1, 180, "object", "truck", 0.76, [250, 180, 200, 130], "T008"),
            # Camera 3 detections
            (2, 60, "object", "person", 0.93, [110, 55, 115, 275], "T009"),
            (2, 60, "face", "face", 0.84, [125, 60, 55, 65], "T009"),
            (2, 120, "object", "car", 0.91, [320, 200, 175, 105], "T010"),
            (2, 120, "plate", "DL01EF9012", 0.85, [360, 280, 72, 24], None),
            (2, 300, "object", "person", 0.86, [140, 65, 105, 260], "T011"),
        ]

        ai_count = 0
        for (ev_idx, frame, det_type, label, conf, bbox, track) in demo_detections:
            if ev_idx < len(evidence_items):
                fps = evidence_items[ev_idx].fps or 25.0
                result = AIResult(
                    evidence_id=evidence_items[ev_idx].id,
                    frame_number=frame,
                    timestamp=frame / fps,
                    detection_type=det_type,
                    label=label,
                    confidence=conf,
                    bounding_box=bbox,
                    track_id=track,
                    model_name="DEMO_MODEL",
                    model_version="demo-v1",
                    meta_data={
                        "demo": True,
                        "note": "Synthetic demo detection — not actual AI inference",
                    },
                )
                db.add(result)
                ai_count += 1

        db.commit()

        for evidence in evidence_items:
            ledger.append_event(
                case_id=case.id,
                event_type="DEMO_AI_ANALYSIS",
                actor="SAKSHYA Demo System",
                evidence_id=evidence.id,
                meta_data={"demo": True, "note": "Demo AI results"},
            )

        print(f"   Created {ai_count} AI detection results")

        # =====================================================================
        # 5. Build Merkle Tree
        # =====================================================================
        print("\n[5/10] Building Merkle tree...")
        leaves = [e.sha256 for e in evidence_items]
        tree = MerkleTree(leaves)

        merkle = MerkleRecord(
            case_id=case.id,
            root_hash=tree.root,
            leaf_count=tree.leaf_count,
            leaves=tree.leaves,
            algorithm="SHA-256",
        )
        db.add(merkle)
        db.commit()
        db.refresh(merkle)

        ledger.append_event(
            case_id=case.id,
            event_type="MERKLE_ROOT_CREATED",
            actor=case.investigator,
            meta_data={
                "merkle_root": tree.root,
                "leaf_count": tree.leaf_count,
            },
        )
        print(f"   Merkle Root: {tree.root[:32]}...")
        print(f"   Leaf Count: {tree.leaf_count}")

        # =====================================================================
        # 6. Final Summary
        # =====================================================================
        print("\n[6/10] Finalizing chain of custody...")
        ledger.append_event(
            case_id=case.id,
            event_type="CHAIN_SEALED",
            actor=case.investigator,
            meta_data={"note": "Demo chain sealed for demonstration"},
        )

        chain_head = ledger.get_chain_head(case.id)
        print(f"   Chain Head: {chain_head[:32]}...")

        # =====================================================================
        # 7. Verify chain integrity
        # =====================================================================
        print("\n[7/10] Verifying chain integrity...")
        verify_result = ledger.verify_chain(case.id)
        status = "OK: CHAIN VALID" if verify_result["valid"] else "FAIL: CHAIN INVALID"
        print(f"   {status} ({verify_result['verified_events']} events verified)")

        # =====================================================================
        # Summary
        # =====================================================================
        print("\n" + "=" * 60)
        print("DEMO SEED COMPLETE")
        print("=" * 60)
        print(f"Case: {case.case_number} — {case.title}")
        print(f"Evidence: {len(evidence_items)} files")
        print(f"Recovered Segments: 4")
        print(f"AI Detections: {ai_count}")
        print(f"Chain Events: {verify_result['total_events']}")
        print(f"Merkle Root: {tree.root[:32]}...")
        print(f"Chain Head: {chain_head[:32]}...")
        print()
        print("To start the application:")
        print("  python -m uvicorn backend.main:app --reload")
        print()
        print("API documentation:")
        print("  http://localhost:8000/docs")
        print()
        print("To start the trust service:")
        print("  python trust_service/app.py")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    seed()
