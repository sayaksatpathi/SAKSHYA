"""
SAKSHYA Video Forensics Service
"""

import logging
from sqlalchemy.orm import Session
from backend.models import Evidence, ForensicFinding
import subprocess
import json
import os

logger = logging.getLogger(__name__)

class VideoForensicsService:
    def __init__(self, db: Session):
        self.db = db

    def analyze_evidence(self, evidence: Evidence) -> list[ForensicFinding]:
        """
        Perform frame-level video forensic analysis.
        Currently checks for:
        1. Duplicate frame sequences
        2. Timestamp jumps/discontinuities
        """
        findings = []
        if not evidence.storage_path or not os.path.exists(evidence.storage_path):
            return findings

        # Run ffprobe to get frame-level information
        # We need packet/frame timestamps
        cmd = [
            "ffprobe", 
            "-v", "quiet", 
            "-select_streams", "v:0", 
            "-show_entries", "frame=pkt_pts_time,pkt_size,pict_type", 
            "-of", "json", 
            evidence.storage_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            frames = data.get("frames", [])
        except Exception as e:
            logger.error("FFprobe frame analysis failed: %s", e)
            return findings

        if not frames:
            return findings

        fps = evidence.fps or 25.0
        expected_delta = 1.0 / fps
        
        # 1. Timestamp discontinuities
        # 2. Duplicate frames (same pkt_size over multiple frames could indicate duplication)
        
        prev_time = None
        prev_size = None
        duplicate_start_frame = None
        duplicate_count = 0
        
        for i, frame in enumerate(frames):
            try:
                curr_time_str = frame.get("pkt_pts_time")
                if curr_time_str is None:
                    continue
                curr_time = float(curr_time_str)
                curr_size = frame.get("pkt_size")
                
                # Check timestamps
                if prev_time is not None:
                    delta = curr_time - prev_time
                    if delta > expected_delta * 2.5: # large gap
                        finding = ForensicFinding(
                            evidence_id=evidence.id,
                            type="TIMESTAMP_GAP",
                            frame_start=i-1,
                            frame_end=i,
                            timestamp_start=prev_time,
                            timestamp_end=curr_time,
                            severity="HIGH",
                            description=f"Abnormal timestamp gap detected: {delta:.3f}s (expected ~{expected_delta:.3f}s)",
                            method="ffprobe_pts_analysis",
                            parameters={"delta": delta, "expected": expected_delta}
                        )
                        self.db.add(finding)
                        findings.append(finding)
                    elif delta < 0:
                        finding = ForensicFinding(
                            evidence_id=evidence.id,
                            type="NON_MONOTONIC_TIMESTAMP",
                            frame_start=i-1,
                            frame_end=i,
                            timestamp_start=prev_time,
                            timestamp_end=curr_time,
                            severity="HIGH",
                            description=f"Timestamps went backwards from {prev_time} to {curr_time}",
                            method="ffprobe_pts_analysis"
                        )
                        self.db.add(finding)
                        findings.append(finding)

                # Check duplicates (naive: exactly same size consecutive frames, usually rare unless duplicated)
                if curr_size is not None and prev_size is not None and curr_size == prev_size:
                    if duplicate_count == 0:
                        duplicate_start_frame = i - 1
                    duplicate_count += 1
                else:
                    if duplicate_count >= 5: # 5 or more consecutive identical size frames
                        finding = ForensicFinding(
                            evidence_id=evidence.id,
                            type="DUPLICATE_FRAMES",
                            frame_start=duplicate_start_frame,
                            frame_end=i-1,
                            timestamp_start=float(frames[duplicate_start_frame].get("pkt_pts_time", 0)),
                            timestamp_end=float(frames[i-1].get("pkt_pts_time", 0)),
                            severity="MEDIUM",
                            description=f"Found {duplicate_count + 1} consecutive frames with identical size, indicating possible frame duplication.",
                            method="ffprobe_pkt_size_analysis",
                            parameters={"run_length": duplicate_count + 1, "pkt_size": prev_size}
                        )
                        self.db.add(finding)
                        findings.append(finding)
                    duplicate_count = 0
                    duplicate_start_frame = None

                prev_time = curr_time
                prev_size = curr_size
            except ValueError:
                pass

        if findings:
            self.db.commit()
            for f in findings:
                self.db.refresh(f)

        return findings
