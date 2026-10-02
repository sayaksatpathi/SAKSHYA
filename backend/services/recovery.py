"""
SAKSHYA Recovery Engine

Extensible forensic recovery pipeline for deleted/fragmented surveillance video.
Supports filesystem-based recovery and raw file carving.
"""

import logging
import os
import struct
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Evidence, EvidenceSegment
from backend.crypto.hashing import sha256_file
from backend.services.ledger import LedgerService

logger = logging.getLogger(__name__)


# Known video file signatures (magic bytes)
VIDEO_SIGNATURES = {
    "mp4_ftyp": {
        "offset": 4,
        "magic": b"ftyp",
        "extensions": [".mp4", ".m4v", ".mov"],
        "description": "ISO Base Media (MP4/MOV/M4V)",
    },
    "avi_riff": {
        "offset": 0,
        "magic": b"RIFF",
        "secondary_offset": 8,
        "secondary_magic": b"AVI ",
        "extensions": [".avi"],
        "description": "AVI (RIFF container)",
    },
    "mkv_ebml": {
        "offset": 0,
        "magic": b"\x1a\x45\xdf\xa3",
        "extensions": [".mkv", ".webm"],
        "description": "Matroska/WebM (EBML)",
    },
    "flv": {
        "offset": 0,
        "magic": b"FLV",
        "extensions": [".flv"],
        "description": "Flash Video",
    },
    "mpg_pes": {
        "offset": 0,
        "magic": b"\x00\x00\x01\xba",
        "extensions": [".mpg", ".mpeg", ".vob"],
        "description": "MPEG Program Stream",
    },
    "h264_nalu": {
        "offset": 0,
        "magic": b"\x00\x00\x00\x01",
        "extensions": [".h264", ".h265"],
        "description": "H.264/H.265 NAL Unit",
    },
}

# Minimum segment size to consider valid (256 KB)
MIN_SEGMENT_SIZE = 256 * 1024


class RecoveryStrategy(ABC):
    """Abstract base for recovery strategies."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable strategy name."""
        ...

    @abstractmethod
    def can_handle(self, evidence: Evidence) -> bool:
        """Check if this strategy applies to the given evidence."""
        ...

    @abstractmethod
    def recover(
        self, evidence: Evidence, output_dir: Path, db: Session
    ) -> list[dict[str, Any]]:
        """
        Attempt recovery and return list of recovered segment info dicts.

        Each dict should contain:
            file_path, sha256, size, recovery_method, confidence,
            source_offset, validation_status
        """
        ...


class VideoCarver(RecoveryStrategy):
    """
    Raw file carver that scans binary data for known video signatures
    and extracts candidate segments.
    """

    def name(self) -> str:
        return "raw_video_carver"

    def can_handle(self, evidence: Evidence) -> bool:
        """Can attempt carving on any file."""
        return True

    def recover(
        self, evidence: Evidence, output_dir: Path, db: Session
    ) -> list[dict[str, Any]]:
        """
        Scan the evidence file for known video signatures and extract
        candidate segments.
        """
        source_path = Path(evidence.storage_path)
        if not source_path.exists():
            logger.error("Evidence file not found: %s", source_path)
            return []

        results = []
        file_size = source_path.stat().st_size

        with open(source_path, "rb") as f:
            data = f.read()

        for sig_name, sig_info in VIDEO_SIGNATURES.items():
            offset = 0
            magic = sig_info["magic"]

            while offset < len(data):
                # Search for the magic bytes at the expected position
                search_start = max(0, offset)
                pos = data.find(magic, search_start)
                if pos < 0:
                    break

                # For signatures with an offset (like MP4 ftyp at byte 4),
                # adjust the actual start position
                actual_start = pos - sig_info.get("offset", 0)
                if actual_start < 0:
                    offset = pos + len(magic)
                    continue

                # Secondary magic check (e.g., AVI has RIFF + AVI)
                if "secondary_magic" in sig_info:
                    sec_off = actual_start + sig_info["secondary_offset"]
                    sec_magic = sig_info["secondary_magic"]
                    if sec_off + len(sec_magic) > len(data):
                        offset = pos + len(magic)
                        continue
                    if data[sec_off:sec_off + len(sec_magic)] != sec_magic:
                        offset = pos + len(magic)
                        continue

                # Attempt to determine segment size
                segment_size = self._estimate_segment_size(
                    data, actual_start, sig_name, file_size
                )

                if segment_size >= MIN_SEGMENT_SIZE:
                    # Extract the candidate segment
                    ext = sig_info["extensions"][0]
                    seg_filename = f"recovered_{sig_name}_{actual_start:08x}{ext}"
                    seg_path = output_dir / seg_filename

                    segment_data = data[actual_start:actual_start + segment_size]
                    with open(seg_path, "wb") as sf:
                        sf.write(segment_data)

                    seg_hash = sha256_file(seg_path)
                    confidence = self._estimate_confidence(segment_data, sig_name)

                    results.append({
                        "file_path": str(seg_path),
                        "sha256": seg_hash,
                        "size": segment_size,
                        "recovery_method": f"raw_carve_{sig_name}",
                        "source_offset": actual_start,
                        "confidence": confidence,
                        "validation_status": "CANDIDATE",
                        "meta_data": {
                            "signature": sig_name,
                            "description": sig_info["description"],
                        },
                    })

                    logger.info(
                        "Carved candidate segment",
                        extra={
                            "signature": sig_name,
                            "offset": actual_start,
                            "size": segment_size,
                            "confidence": confidence,
                        },
                    )

                offset = pos + max(len(magic), segment_size if segment_size > 0 else 1)

        return results

    def _estimate_segment_size(
        self, data: bytes, start: int, sig_name: str, file_size: int
    ) -> int:
        """
        Estimate the size of a carved segment.

        For MP4/MOV: parse the atom structure to find the end.
        For others: use heuristic (next signature or end of file).
        """
        remaining = len(data) - start

        if sig_name == "mp4_ftyp":
            return self._parse_mp4_size(data, start, remaining)

        if sig_name == "avi_riff":
            # AVI RIFF header contains size at bytes 4-8
            if start + 8 <= len(data):
                size = struct.unpack_from("<I", data, start + 4)[0] + 8
                return min(size, remaining)

        # Default: scan forward for next known signature or use a max chunk
        max_segment = min(remaining, 50 * 1024 * 1024)  # 50MB max per segment
        return max_segment

    def _parse_mp4_size(self, data: bytes, start: int, remaining: int) -> int:
        """Parse MP4 atom structure to determine container size."""
        offset = start
        end = start + remaining

        while offset < end:
            if offset + 8 > end:
                break
            atom_size = struct.unpack_from(">I", data, offset)[0]
            if atom_size == 0:
                # Atom extends to end of file
                return end - start
            if atom_size == 1:
                # 64-bit extended size
                if offset + 16 > end:
                    break
                atom_size = struct.unpack_from(">Q", data, offset + 8)[0]
            if atom_size < 8:
                break
            atom_type = data[offset + 4:offset + 8]
            offset += atom_size
            # moov atom typically marks the structural end
            if atom_type == b"moov":
                return offset - start

        return min(offset - start, remaining)

    def _estimate_confidence(self, segment_data: bytes, sig_name: str) -> float:
        """
        Estimate confidence that a carved segment is a valid video.

        Higher confidence if we can detect proper structure.
        """
        if len(segment_data) < MIN_SEGMENT_SIZE:
            return 0.2

        if sig_name == "mp4_ftyp":
            # Check for moov atom
            if b"moov" in segment_data[:min(len(segment_data), 10 * 1024 * 1024)]:
                return 0.85
            return 0.5

        if sig_name == "avi_riff":
            if b"AVI " in segment_data[:12]:
                return 0.80
            return 0.4

        if sig_name == "mkv_ebml":
            return 0.70

        return 0.50


class FragmentDetector(RecoveryStrategy):
    """
    Detects video fragments that may be parts of a larger recording
    split by the DVR/NVR filesystem.
    """

    def name(self) -> str:
        return "fragment_detector"

    def can_handle(self, evidence: Evidence) -> bool:
        ext = os.path.splitext(evidence.storage_path)[1].lower()
        return ext in {".img", ".dd", ".raw", ".bin"}

    def recover(
        self, evidence: Evidence, output_dir: Path, db: Session
    ) -> list[dict[str, Any]]:
        """
        Scan a disk image for video fragments.
        Falls back to VideoCarver for the actual carving.
        """
        carver = VideoCarver()
        return carver.recover(evidence, output_dir, db)


class DemoRecoveryStrategy(RecoveryStrategy):
    """
    Demo recovery strategy that simulates finding deleted segments
    within an evidence file for demonstration purposes.

    Clearly marks results as DEMO_SIMULATION.
    """

    def name(self) -> str:
        return "demo_simulation"

    def can_handle(self, evidence: Evidence) -> bool:
        return True

    def recover(
        self, evidence: Evidence, output_dir: Path, db: Session
    ) -> list[dict[str, Any]]:
        """
        Simulate recovery by splitting the evidence into segments.
        Each segment is marked as a demo simulation.
        """
        source_path = Path(evidence.storage_path)
        if not source_path.exists():
            return []

        file_size = source_path.stat().st_size
        if file_size < MIN_SEGMENT_SIZE * 2:
            # Too small to meaningfully split
            return []

        results = []
        # Simulate finding 2-3 "deleted" segments
        segment_count = min(3, max(2, file_size // (5 * 1024 * 1024)))
        segment_size = file_size // segment_count

        with open(source_path, "rb") as f:
            for i in range(segment_count):
                offset = i * segment_size
                f.seek(offset)
                chunk = f.read(segment_size)

                seg_filename = f"demo_recovered_segment_{i + 1}.mp4"
                seg_path = output_dir / seg_filename

                with open(seg_path, "wb") as sf:
                    sf.write(chunk)

                seg_hash = sha256_file(seg_path)

                results.append({
                    "file_path": str(seg_path),
                    "sha256": seg_hash,
                    "size": len(chunk),
                    "recovery_method": "demo_simulation",
                    "source_offset": offset,
                    "confidence": 0.95,
                    "validation_status": "DEMO",
                    "start_time": i * 30.0,  # simulated timestamps
                    "end_time": (i + 1) * 30.0,
                    "meta_data": {
                        "note": "This segment was created by the demo recovery simulator. "
                                "It does not represent actual forensic recovery.",
                        "demo": True,
                    },
                })

        return results


class Validator(RecoveryStrategy):
    """Validates structural integrity of recovered candidates."""
    def name(self) -> str:
        return "Validator"
    
    def can_handle(self, evidence: Evidence) -> bool:
        return True
        
    def recover(self, evidence: Evidence, output_dir: Path, db: Session) -> list[dict[str, Any]]:
        # In a real system, this would scan the file and return validation results.
        # We simulate it for testing.
        return []

class MetadataRecovery(RecoveryStrategy):
    """Attempts to recover filesystem or container metadata."""
    def name(self) -> str:
        return "MetadataRecovery"
    
    def can_handle(self, evidence: Evidence) -> bool:
        return True
        
    def recover(self, evidence: Evidence, output_dir: Path, db: Session) -> list[dict[str, Any]]:
        return []

class RecoveryEngine:
    """
    Orchestrates the recovery pipeline.

    Tries strategies in order and collects results.
    """

    def __init__(self, db: Session):
        self.db = db
        self.ledger = LedgerService(db)
        self.strategies: list[RecoveryStrategy] = [
            MetadataRecovery(),
            VideoCarver(),
            FragmentDetector(),
            Validator(),
        ]

    def recover(
        self, evidence: Evidence, use_demo: bool = False
    ) -> list[EvidenceSegment]:
        """
        Run recovery on the given evidence.

        Args:
            evidence: The evidence to attempt recovery on.
            use_demo: If True, use demo simulation instead of real carving.

        Returns:
            List of created EvidenceSegment records.
        """
        output_dir = Path(settings.evidence_storage_path) / evidence.case_id / "recovered"
        output_dir.mkdir(parents=True, exist_ok=True)

        segments = []

        if use_demo:
            strategy = DemoRecoveryStrategy()
            results = strategy.recover(evidence, output_dir, self.db)
        else:
            results = []
            for strategy in self.strategies:
                if isinstance(strategy, DemoRecoveryStrategy):
                    continue  # Skip demo unless explicitly requested
                if strategy.can_handle(evidence):
                    try:
                        found = strategy.recover(evidence, output_dir, self.db)
                        results.extend(found)
                    except Exception as e:
                        logger.error("Recovery strategy %s failed: %s", strategy.name(), e)

        for result in results:
            segment = EvidenceSegment(
                evidence_id=evidence.id,
                start_time=result.get("start_time"),
                end_time=result.get("end_time"),
                file_path=result["file_path"],
                sha256=result["sha256"],
                size=result.get("size"),
                recovery_method=result["recovery_method"],
                source_offset=result.get("source_offset"),
                confidence=result.get("confidence", 0.5),
                validation_status=result.get("validation_status", "CANDIDATE"),
                meta_data=result.get("meta_data"),
            )
            self.db.add(segment)
            segments.append(segment)

        if segments:
            self.db.commit()
            for seg in segments:
                self.db.refresh(seg)

            # Create ledger event
            self.ledger.append_event(
                case_id=evidence.case_id,
                event_type="RECOVERY_COMPLETED",
                actor=settings.default_investigator,
                evidence_id=evidence.id,
                meta_data={
                    "segments_recovered": len(segments),
                    "methods": list({s.recovery_method for s in segments}),
                },
            )

        return segments
