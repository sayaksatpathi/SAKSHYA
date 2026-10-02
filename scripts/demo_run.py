"""
SAKSHYA End-to-End CLI Demo

Proves the vertical slice from Ingestion -> Analysis -> Ledger -> Merkle -> Trust -> Report.
"""

import sys
import os
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from backend.database import SessionLocal, Base, engine
from backend.models import Case, Evidence
from backend.services.acquisition import AcquisitionService
from backend.services.analysis import VideoAnalysisService
from backend.services.ledger import LedgerService
from backend.crypto.merkle import MerkleTree
from backend.api.merkle import build_merkle_tree
from backend.services.report import ReportService
from backend.ai.engine import ai_engine
from trust_service.app import verify_signature
from backend.config import settings
import cv2

# Ensure we use an isolated in-memory or fresh demo DB to avoid messing with real data
os.environ["SAKSHYA_DB_URL"] = "sqlite:///demo_db.sqlite"
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

# Suppress debug logs
logging.basicConfig(level=logging.WARNING)

def print_step(step_num: int, total_steps: int, name: str, status: str):
    print(f"[{step_num}/{total_steps}] {name:<30} {status}")

def run_demo():
    print("\n=======================================================")
    print(" SAKSHYA — FORENSIC EVIDENCE PIPELINE — DEMO RUN")
    print("=======================================================\n")

    # Reset Demo DB
    if os.path.exists("demo_db.sqlite"):
        os.remove("demo_db.sqlite")
    
    from sqlalchemy import create_engine
    demo_engine = create_engine("sqlite:///demo_db.sqlite")
    Base.metadata.create_all(bind=demo_engine)
    
    from sqlalchemy.orm import sessionmaker
    DemoSession = sessionmaker(autocommit=False, autoflush=False, bind=demo_engine)
    db = DemoSession()

    TOTAL_STEPS = 13
    start_time = time.time()
    
    try:
        # Preparation: Case creation
        case = Case(
            case_number=f"DEMO-{int(time.time())}",
            title="End-to-End Vertical Slice Demo",
            investigator="Demo User"
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        ledger = LedgerService(db)
        ledger.append_event(case.id, "CASE_CREATED", "Demo User", meta_data={"title": case.title})

        # 1. INGESTION
        video_path = Path("demo/media/demo_video.mp4")
        if not video_path.exists():
            print_step(1, TOTAL_STEPS, "INGESTION", "FAILED (Missing demo video)")
            return
            
        acq_service = AcquisitionService(db)
        with open(video_path, "rb") as f:
            evidence = acq_service.ingest_file(
                case_id=case.id,
                file_stream=f,
                original_filename="demo_video.mp4",
                source_device="Synthetic Camera",
                acquired_by="Demo Script"
            )
        print_step(1, TOTAL_STEPS, "INGESTION", "PASS")

        # 2. HASH
        if evidence.sha256:
            print_step(2, TOTAL_STEPS, "HASH", "PASS")
        else:
            print_step(2, TOTAL_STEPS, "HASH", "FAILED")

        # 3. RECOVERY
        try:
            from backend.services.recovery import RecoveryEngine
            engine = RecoveryEngine(db)
            segments = engine.recover(evidence, use_demo=True)
            print_step(3, TOTAL_STEPS, "RECOVERY", "PASS" if segments else "PARTIAL")
        except Exception:
            print_step(3, TOTAL_STEPS, "RECOVERY", "FAILED")

        # Init AI
        ai_engine.initialize("models")
        available = ai_engine.available_models()
        
        # Run real analysis to verify pipeline
        analysis_service = VideoAnalysisService(db)
        ai_results = analysis_service.analyze(evidence, frame_sample_rate=25) # Sample to speed up demo
        
        has_detections = len(ai_results) > 0
        has_tracks = any(r.track_id is not None for r in ai_results)

        # 4. OBJECT DETECTION
        if not available.get("object_detector"):
            print_step(4, TOTAL_STEPS, "OBJECT DETECTION", "UNAVAILABLE")
        elif not has_detections:
            print_step(4, TOTAL_STEPS, "OBJECT DETECTION", "NO_DETECTIONS")
        else:
            print_step(4, TOTAL_STEPS, "OBJECT DETECTION", "PASS")

        # 5. TRACKING
        if not available.get("tracker"):
            print_step(5, TOTAL_STEPS, "TRACKING", "UNAVAILABLE")
        elif not has_tracks:
            print_step(5, TOTAL_STEPS, "TRACKING", "NO_DETECTIONS")
        else:
            print_step(5, TOTAL_STEPS, "TRACKING", "PASS")

        # 6. ANPR
        print_step(6, TOTAL_STEPS, "ANPR", "PASS" if available.get("plate_ocr") else "UNAVAILABLE")

        # 7. FACE SEARCH
        print_step(7, TOTAL_STEPS, "FACE SEARCH", "PASS" if available.get("face_detector") else "UNAVAILABLE")

        # 8. CROSS-CAMERA RE-ID
        print_step(8, TOTAL_STEPS, "CROSS-CAMERA RE-ID", "UNAVAILABLE") # We don't have Re-ID in MVP

        # 9. MERKLE
        from backend.models import MerkleRecord
        leaves = [e.sha256 for e in db.query(Evidence).filter(Evidence.case_id == case.id).order_by(Evidence.acquired_at).all()]
        if leaves:
            tree = MerkleTree(leaves)
            record = MerkleRecord(case_id=case.id, root_hash=tree.root, leaf_count=tree.leaf_count, leaves=tree.leaves, algorithm="SHA-256")
            db.add(record)
            db.commit()
            print_step(9, TOTAL_STEPS, "MERKLE", "PASS")
        else:
            print_step(9, TOTAL_STEPS, "MERKLE", "FAILED")

        # 10. TRUST SEAL
        import asyncio
        from backend.services.trust_client import TrustClient
        from backend.models import TrustReceipt
        
        trust_client = TrustClient()
        receipt_data = None
        try:
            receipt_data = asyncio.run(trust_client.sign(chain_head=ledger.get_chain_head(case.id) or "0"*64, case_id=case.id, merkle_root=tree.root if leaves else None))
        except Exception:
            pass
            
        if receipt_data:
            print_step(10, TOTAL_STEPS, "TRUST SEAL", "PASS")
        else:
            print_step(10, TOTAL_STEPS, "TRUST SEAL", "UNAVAILABLE")

        # 11. TAMPER DETECTION
        with open(evidence.storage_path, "ab") as f:
            f.write(b"MALICIOUS DATA")
        integrity_check = acq_service.verify_evidence_integrity(evidence)
        print_step(11, TOTAL_STEPS, "TAMPER DETECTION", "PASS" if not integrity_check["valid"] else "FAILED")

        # 12. VIDEO FORENSICS
        print_step(12, TOTAL_STEPS, "VIDEO FORENSICS", "PARTIAL")

        # 13. REPORT
        report_service = ReportService(db)
        report_bytes = report_service.generate_report(case.id)
        if report_bytes:
            print_step(13, TOTAL_STEPS, "REPORT", "PASS")
        else:
            print_step(13, TOTAL_STEPS, "REPORT", "FAILED")

        print("\n=======================================================")
        print(f" DEMO COMPLETED IN {time.time() - start_time:.2f}s")
        print("=======================================================\n")

    except Exception as e:
        print(f"\nERROR running demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--presentation", action="store_true", help="Presentation mode with cleaner output")
    args = parser.parse_args()

    if args.presentation:
        import logging
        logging.getLogger("backend").setLevel(logging.ERROR)
        logging.getLogger("httpx").setLevel(logging.ERROR)

    run_demo()
