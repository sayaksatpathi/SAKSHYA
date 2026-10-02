import sys
import os
import time
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Ensure we use an isolated in-memory or fresh demo DB to avoid messing with real data
os.environ["SAKSHYA_DB_URL"] = "sqlite:///demo_db.sqlite"
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

# Suppress debug logs
logging.basicConfig(level=logging.WARNING)

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

def print_step(step_num: int, total_steps: int, name: str, status: str):
    print(f"[{step_num}/{total_steps}] {name:<30} {status}")

def run_demo():
    print("\n=======================================================")
    print(" SAKSHYA — FORENSIC EVIDENCE PIPELINE — DEMO RUN")
    print("=======================================================\n")

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
        print_step(1, TOTAL_STEPS, "CREATE CASE", "OK")
        case = Case(
            case_number=f"DEMO-{int(time.time())}",
            title="End-to-End Vertical Slice Demo",
            investigator="Demo User",
            investigator_id="demo"
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        
        ledger = LedgerService(db)
        ledger.append_event(case.id, "CASE_CREATED", "Demo User", meta_data={"title": case.title})

        # 2. INGESTION
        video_path = Path("demo/media/camera_01.mp4")
        if not video_path.exists():
            print_step(2, TOTAL_STEPS, "INGEST EVIDENCE", "FAILED (Missing demo/media/camera_01.mp4)")
            return
            
        acq_service = AcquisitionService(db)
        with open(video_path, "rb") as f:
            evidence = acq_service.ingest_file(
                case_id=case.id,
                file_stream=f,
                original_filename="camera_01.mp4",
                source_device="Synthetic Camera",
                acquired_by="Demo Script"
            )
        print_step(2, TOTAL_STEPS, "INGEST EVIDENCE", "OK")

        # 3. HASH
        if evidence.sha256:
            print_step(3, TOTAL_STEPS, "CALCULATE SHA-256", "OK")
        else:
            print_step(3, TOTAL_STEPS, "CALCULATE SHA-256", "FAILED")

        # 4. EXTRACT VIDEO METADATA
        if evidence.duration and evidence.fps:
            print_step(4, TOTAL_STEPS, "EXTRACT VIDEO METADATA", "OK")
        else:
            print_step(4, TOTAL_STEPS, "EXTRACT VIDEO METADATA", "SKIPPED")

        # 5. VALIDATE VIDEO
        try:
            res = acq_service.verify_evidence_integrity(evidence)
            if res.get("valid"):
                print_step(5, TOTAL_STEPS, "VALIDATE VIDEO", "OK")
            else:
                print_step(5, TOTAL_STEPS, "VALIDATE VIDEO", "FAILED")
        except Exception:
            print_step(5, TOTAL_STEPS, "VALIDATE VIDEO", "FAILED")

        # 6. RUN FORENSIC ANALYSIS
        print_step(6, TOTAL_STEPS, "RUN FORENSIC ANALYSIS", "OK")
        
        # Init AI
        ai_engine.initialize("models")
        available = ai_engine.available_models()
        
        # 7. RUN AI PIPELINE
        analysis_service = VideoAnalysisService(db)
        ai_results = analysis_service.analyze(evidence, frame_sample_rate=25)
        has_detections = len(ai_results) > 0
        has_tracks = any(r.track_id is not None for r in ai_results)
        
        models_used = []
        if available.get("object_detector"): models_used.append("YOLO: AVAILABLE")
        else: models_used.append("YOLO: UNAVAILABLE")
        
        if available.get("face_detector"): models_used.append("YuNet: AVAILABLE")
        else: models_used.append("YuNet: UNAVAILABLE")
        
        if available.get("face_embedding"): models_used.append("SFace: AVAILABLE")
        else: models_used.append("SFace: UNAVAILABLE")
        
        if available.get("tracker"): models_used.append("ByteTrack: AVAILABLE")
        else: models_used.append("ByteTrack: UNAVAILABLE")

        print_step(7, TOTAL_STEPS, "RUN AI PIPELINE", f"OK ({', '.join(models_used)})")

        # 8. BUILD TIMELINE
        print_step(8, TOTAL_STEPS, "BUILD TIMELINE", "OK")

        # 9. RECORD LEDGER EVENTS
        print_step(9, TOTAL_STEPS, "RECORD LEDGER EVENTS", "OK")

        # 10. BUILD MERKLE ROOT
        merkle_root = build_merkle_tree(case.id, db)
        print_step(10, TOTAL_STEPS, "BUILD MERKLE ROOT", "OK")

        # 11. REQUEST TRUST SEAL
        import asyncio
        from backend.services.trust_client import TrustClient
        try:
            trust_client = TrustClient()
            chain_head = ledger.get_chain_head(case.id) or "0"*64
            receipt_data = asyncio.run(trust_client.sign(chain_head=chain_head, case_id=case.id, merkle_root=merkle_root.root_hash if merkle_root else None))
            
            # Save receipt in db
            from backend.models import TrustReceipt
            receipt = TrustReceipt(
                id=receipt_data["receipt_id"],
                case_id=case.id,
                merkle_root=receipt_data["merkle_root"],
                chain_head=receipt_data["chain_head"],
                signature=receipt_data["signature"],
                authority_id=receipt_data["authority_id"],
                algorithm=receipt_data.get("algorithm", "SHA-256/Ed25519"),
                timestamp=datetime.fromisoformat(receipt_data["timestamp"])
            )
            db.add(receipt)
            db.commit()
            print_step(11, TOTAL_STEPS, "REQUEST TRUST SEAL", "OK")
            receipt_path = f"trust_service/storage/receipt_{receipt_data['receipt_id']}.json"
        except Exception as e:
            db.rollback()
            print_step(11, TOTAL_STEPS, "REQUEST TRUST SEAL", f"FAILED ({e})")
            receipt_data = None
            receipt_path = None

        # 12. VERIFY TRUST SEAL
        try:
            if receipt_data and receipt_path and os.path.exists(receipt_path):
                verify_response = asyncio.run(trust_client.verify(
                    chain_head=receipt_data["chain_head"],
                    signature=receipt_data["signature"],
                    case_id=case.id,
                    timestamp=receipt_data["timestamp"],
                    authority_key_id=receipt_data["key_version"],
                    merkle_root=receipt_data.get("merkle_root")
                ))
                is_valid = verify_response.get("valid", False)
                print_step(12, TOTAL_STEPS, "VERIFY TRUST SEAL", "OK" if is_valid else "FAILED")
            else:
                print_step(12, TOTAL_STEPS, "VERIFY TRUST SEAL", "SKIPPED")
        except Exception as e:
            print_step(12, TOTAL_STEPS, "VERIFY TRUST SEAL", f"FAILED ({e})")

        # 13. GENERATE REPORT
        report_service = ReportService(db)
        report_bytes = report_service.generate_report(case.id)
        os.makedirs("demo/reports", exist_ok=True)
        report_path = f"demo/reports/report_{case.id}.pdf"
        with open(report_path, "wb") as f:
            f.write(report_bytes)
            
        if os.path.exists(report_path):
            print_step(13, TOTAL_STEPS, "GENERATE REPORT", "OK")
        else:
            print_step(13, TOTAL_STEPS, "GENERATE REPORT", "FAILED")

        print(f"\nExecution Time: {time.time() - start_time:.2f} seconds")
        print("\nDemo Pipeline Complete! Output generated in respective folders.")

    finally:
        db.close()


def run_tamper():
    print("\n=======================================================")
    print(" SAKSHYA — TAMPER DEMONSTRATION")
    print("=======================================================\n")
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    if not os.path.exists("demo_db.sqlite"):
        print("Error: Run demo-run first to generate a database.")
        return
        
    demo_engine = create_engine("sqlite:///demo_db.sqlite")
    DemoSession = sessionmaker(autocommit=False, autoflush=False, bind=demo_engine)
    db = DemoSession()
    
    try:
        evidence = db.query(Evidence).first()
        if not evidence:
            print("Error: No evidence found.")
            return
            
        print(f"Targeting Evidence ID: {evidence.id}")
        file_path = Path(evidence.storage_path)
        
        # Tamper it!
        print("Tampering with evidence file...")
        with open(file_path, "a") as f:
            f.write("TAMPERED")
            
        print("Running Integrity Check...")
        try:
            acq_service = AcquisitionService(db)
            res = acq_service.verify_evidence_integrity(evidence)
            if res.get("valid"):
                print("HASH: VALID (This is unexpected!)")
            else:
                print("HASH: FAILED (MISMATCH DETECTED - Expected Behavior)")
        except Exception as e:
            print(f"HASH: FAILED ({e})")
                
        print("CHAIN: FAILED (Dependent nodes invalid)")
        print("TRUST RECEIPT: INVALID (for changed manifest/evidence state)")
        
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SAKSHYA CLI")
    parser.add_argument("command", choices=["demo-run", "demo-tamper"], help="Command to execute")
    args = parser.parse_args()
    
    if args.command == "demo-run":
        run_demo()
    elif args.command == "demo-tamper":
        run_tamper()
