"""
SAKSHYA Video Analysis Service

Processes video evidence through the AI pipeline with configurable
frame sampling and result storage.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Evidence, AIResult
from backend.ai.engine import ai_engine, Detection
from backend.services.ledger import LedgerService

logger = logging.getLogger(__name__)


class VideoAnalysisService:
    """Coordinates AI analysis of video evidence."""

    def __init__(self, db: Session):
        self.db = db
        self.ledger = LedgerService(db)

    def analyze(
        self,
        evidence: Evidence,
        frame_sample_rate: Optional[int] = None,
        detection_confidence: Optional[float] = None,
    ) -> list[AIResult]:
        """
        Run AI analysis on video evidence.

        Samples frames at the configured rate and runs all available
        detectors on each sampled frame.

        Args:
            evidence: The evidence to analyze.
            frame_sample_rate: Analyze every Nth frame (default from config).
            detection_confidence: Minimum confidence threshold.

        Returns:
            List of created AIResult records.
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available — cannot analyze video")
            return []

        if not ai_engine.available_models():
            logger.warning("No AI models available")
            return []

        # Initialize AI engine if needed
        if not ai_engine._initialized:
            ai_engine.initialize(settings.model_base_path)

        sample_rate = frame_sample_rate or settings.frame_sample_rate
        min_confidence = detection_confidence or settings.detection_confidence

        video_path = Path(evidence.storage_path)
        if not video_path.exists():
            logger.error("Evidence file not found: %s", video_path)
            return []

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error("Cannot open video: %s", video_path)
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        ai_results = []
        frame_num = 0
        
        import uuid
        from datetime import datetime, timezone
        from backend.crypto.hashing import sha256_string, canonicalize_json
        
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Starting video analysis",
            extra={
                "evidence_id": evidence.id,
                "total_frames": total_frames,
                "sample_rate": sample_rate,
                "fps": fps,
            },
        )

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_num % sample_rate == 0:
                    timestamp = frame_num / fps if fps > 0 else 0

                    detections = ai_engine.detect_all(frame)

                    for det in detections:
                        if det.confidence < min_confidence:
                            continue

                        det.frame_number = frame_num
                        det.timestamp = timestamp

                        result = AIResult(
                            evidence_id=evidence.id,
                            frame_number=frame_num,
                            timestamp=timestamp,
                            detection_type=det.detection_type,
                            label=det.label,
                            confidence=det.confidence,
                            bounding_box=det.bounding_box,
                            track_id=det.track_id,
                            model_name=det.model_name,
                            model_version=det.model_version,
                            meta_data=det.meta_data if det.meta_data else None,
                        )
                        self.db.add(result)
                        ai_results.append(result)

                frame_num += 1
        finally:
            cap.release()

        if ai_results:
            self.db.commit()
            for r in ai_results:
                self.db.refresh(r)

            # Create ledger event
            type_counts = {}
            end_time = datetime.now(timezone.utc).isoformat()
            
            # Chain AI Results into Integrity System
            # Preferred conceptual structure: AI analysis result hash -> chain event
            ai_data_list = []
            for r in ai_results:
                type_counts[r.detection_type] = type_counts.get(r.detection_type, 0) + 1
                ai_data_list.append({
                    "detection_type": r.detection_type,
                    "label": r.label,
                    "confidence": r.confidence,
                    "frame_number": r.frame_number,
                    "timestamp": r.timestamp,
                    "bounding_box": r.bounding_box,
                    "track_id": r.track_id,
                    "meta_data": r.meta_data
                })
            
            # Canonical Hash of analysis result
            analysis_hash = sha256_string(canonicalize_json(ai_data_list))

            self.ledger.append_event(
                case_id=evidence.case_id,
                event_type="AI_ANALYSIS_COMPLETED",
                actor="SAKSHYA AI Engine",
                evidence_id=evidence.id,
                meta_data={
                    "analysis_id": analysis_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": "READY" if ai_results else "NO_DETECTIONS",
                    "total_detections": len(ai_results),
                    "frames_analyzed": (frame_num // sample_rate) + 1,
                    "frame_sample_rate": sample_rate,
                    "confidence_threshold": min_confidence,
                    "detection_summary": type_counts,
                    "models_used": list({
                        f"{r.model_name} (v{r.model_version}) - {r.meta_data.get('model_sha256', 'unknown')}"
                        for r in ai_results if r.model_name
                    }),
                    "analysis_result_hash": analysis_hash,
                    "software_version": ai_engine.version(),
                    "note": "AI results are investigative aids, not definitive identifications",
                },
            )

        logger.info(
            "Video analysis complete",
            extra={
                "evidence_id": evidence.id,
                "frames_analyzed": frame_num,
                "detections": len(ai_results),
            },
        )

        return ai_results

    def generate_demo_results(self, evidence: Evidence) -> list[AIResult]:
        """
        Generate synthetic AI results for demonstration purposes.

        Clearly marks all results as demo/synthetic data.
        """
        import random

        demo_detections = [
            {"type": "face", "label": "face", "conf": 0.87, "frame": 30, "box": [120, 80, 60, 70]},
            {"type": "face", "label": "face", "conf": 0.92, "frame": 150, "box": [200, 90, 55, 65]},
            {"type": "object", "label": "person", "conf": 0.94, "frame": 30, "box": [100, 50, 120, 280]},
            {"type": "object", "label": "person", "conf": 0.91, "frame": 150, "box": [180, 60, 110, 270]},
            {"type": "object", "label": "car", "conf": 0.89, "frame": 60, "box": [300, 200, 180, 100]},
            {"type": "object", "label": "car", "conf": 0.85, "frame": 210, "box": [350, 210, 170, 95]},
            {"type": "object", "label": "motorcycle", "conf": 0.82, "frame": 120, "box": [400, 250, 80, 60]},
            {"type": "plate", "label": "WB12AB1234", "conf": 0.91, "frame": 60, "box": [340, 280, 70, 25]},
            {"type": "plate", "label": "KA05CD5678", "conf": 0.78, "frame": 210, "box": [390, 285, 65, 22]},
            {"type": "object", "label": "person", "conf": 0.88, "frame": 300, "box": [150, 70, 100, 250]},
            {"type": "face", "label": "face", "conf": 0.79, "frame": 300, "box": [165, 75, 50, 60]},
            {"type": "object", "label": "truck", "conf": 0.76, "frame": 450, "box": [250, 180, 200, 130]},
        ]

        fps = evidence.fps or 25.0
        results = []

        for det in demo_detections:
            timestamp = det["frame"] / fps

            result = AIResult(
                evidence_id=evidence.id,
                frame_number=det["frame"],
                timestamp=timestamp,
                detection_type=det["type"],
                label=det["label"],
                confidence=det["conf"],
                bounding_box=det["box"],
                track_id=f"T{random.randint(1, 20):03d}" if det["type"] == "object" else None,
                model_name="DEMO_MODEL",
                model_version="demo-v1",
                meta_data={
                    "demo": True,
                    "note": "This is synthetic demo data, not actual AI inference",
                },
            )
            self.db.add(result)
            results.append(result)

        if results:
            self.db.commit()
            for r in results:
                self.db.refresh(r)

            self.ledger.append_event(
                case_id=evidence.case_id,
                event_type="DEMO_AI_ANALYSIS",
                actor="SAKSHYA Demo System",
                evidence_id=evidence.id,
                meta_data={
                    "total_detections": len(results),
                    "demo": True,
                    "note": "Demo/synthetic AI results — not actual inference",
                },
            )

        return results
