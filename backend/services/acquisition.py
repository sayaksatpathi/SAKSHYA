"""
SAKSHYA Evidence Acquisition Service

Safe ingestion of evidence files without modifying the source.
Computes SHA-256, extracts meta_data via FFprobe, and creates
a tamper-evident working reference.
"""

import logging
import mimetypes
import os
import shutil
import subprocess
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, BinaryIO

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Evidence
from backend.crypto.hashing import sha256_file, sha256_stream
from backend.services.ledger import LedgerService

logger = logging.getLogger(__name__)

# Safe file extensions for evidence upload
ALLOWED_EXTENSIONS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
    ".3gp", ".m4v", ".ts", ".mts", ".m2ts", ".vob",
    ".h264", ".h265", ".hevc",
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff",
    ".img", ".dd", ".raw", ".bin",  # disk images
}

MAX_FILENAME_LENGTH = 255


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.

    Strips directory components, restricts characters, and limits length.
    """
    # Take only the basename — no directory traversal
    name = os.path.basename(filename)
    # Remove potentially dangerous characters
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    name = "".join(c if c in safe_chars else "_" for c in name)
    # Limit length
    if len(name) > MAX_FILENAME_LENGTH:
        stem, ext = os.path.splitext(name)
        name = stem[: MAX_FILENAME_LENGTH - len(ext)] + ext
    return name or "unnamed_evidence"


def _run_ffprobe(file_path: str, timeout: int = 30) -> Optional[dict[str, Any]]:
    """
    Run FFprobe on a file and return parsed JSON meta_data.

    Args:
        file_path: Path to the media file.
        timeout: Maximum seconds to wait for FFprobe.

    Returns:
        Parsed FFprobe JSON output, or None on failure.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except FileNotFoundError:
        logger.warning("FFprobe not found — meta_data extraction unavailable")
    except subprocess.TimeoutExpired:
        logger.warning("FFprobe timed out for %s", file_path)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("FFprobe parse error for %s: %s", file_path, e)
    return None


def extract_video_metadata(ffprobe_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract structured video meta_data from FFprobe output.

    Returns:
        Dictionary with codec, resolution, fps, duration, etc.
    """
    meta: dict[str, Any] = {}

    fmt = ffprobe_data.get("format", {})
    meta["container_format"] = fmt.get("format_name")
    meta["duration"] = float(fmt.get("duration", 0)) if fmt.get("duration") else None
    meta["size"] = int(fmt.get("size", 0)) if fmt.get("size") else None
    meta["bit_rate"] = int(fmt.get("bit_rate", 0)) if fmt.get("bit_rate") else None

    has_audio = False
    video_stream = None

    for stream in ffprobe_data.get("streams", []):
        codec_type = stream.get("codec_type")
        if codec_type == "video" and video_stream is None:
            video_stream = stream
        elif codec_type == "audio":
            has_audio = True

    if video_stream:
        meta["codec"] = video_stream.get("codec_name")
        w = video_stream.get("width")
        h = video_stream.get("height")
        if w and h:
            meta["resolution"] = f"{w}x{h}"
        # Parse FPS from r_frame_rate (e.g., "25/1")
        r_fps = video_stream.get("r_frame_rate", "")
        if "/" in str(r_fps):
            parts = str(r_fps).split("/")
            try:
                meta["fps"] = round(int(parts[0]) / int(parts[1]), 2)
            except (ValueError, ZeroDivisionError):
                meta["fps"] = None
        elif r_fps:
            try:
                meta["fps"] = float(r_fps)
            except ValueError:
                meta["fps"] = None

    meta["has_audio"] = has_audio
    return meta


class AcquisitionService:
    """Handles safe evidence ingestion."""

    def __init__(self, db: Session):
        self.db = db
        self.ledger = LedgerService(db)

    def ingest_file(
        self,
        case_id: str,
        file_stream: BinaryIO,
        original_filename: str,
        source_device: Optional[str] = None,
        source_vendor: Optional[str] = None,
        acquired_by: Optional[str] = None,
        evidence_type: str = "video",
    ) -> Evidence:
        """
        Ingest an evidence file safely.

        Workflow:
        1. Sanitize filename
        2. Validate extension/MIME
        3. Save to temp location
        4. Compute SHA-256
        5. Extract meta_data via FFprobe
        6. Move to permanent storage
        7. Create database record
        8. Create ledger event

        Args:
            case_id: The case to associate with.
            file_stream: The uploaded file data.
            original_filename: Original filename from the upload.
            source_device: Device identifier.
            source_vendor: Vendor name.
            acquired_by: Investigator name.
            evidence_type: Type of evidence (video, image, disk_image).

        Returns:
            The created Evidence record.

        Raises:
            ValueError: If the file is invalid or rejected.
        """
        # 1. Sanitize filename
        safe_name = sanitize_filename(original_filename)
        ext = os.path.splitext(safe_name)[1].lower()

        # 2. Validate extension
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File extension '{ext}' is not allowed. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # 3. Save to temp location
        settings.ensure_directories()
        temp_dir = Path(settings.temp_storage_path)
        temp_path = temp_dir / f"ingest_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{safe_name}"

        total_size = 0
        try:
            with open(temp_path, "wb") as tmp:
                while True:
                    chunk = file_stream.read(8192)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > settings.max_upload_size:
                        raise ValueError(
                            f"File exceeds maximum upload size of {settings.max_upload_size} bytes"
                        )
                    tmp.write(chunk)
        except ValueError:
            # Clean up on validation failure
            if temp_path.exists():
                temp_path.unlink()
            raise

        # 4. Compute SHA-256
        file_hash = sha256_file(temp_path)

        # Check for duplicate evidence in this case
        existing = (
            self.db.query(Evidence)
            .filter(Evidence.case_id == case_id, Evidence.sha256 == file_hash)
            .first()
        )
        if existing:
            temp_path.unlink()
            raise ValueError(
                f"Evidence with identical SHA-256 ({file_hash[:16]}...) already exists "
                f"in this case as '{existing.original_filename}'"
            )

        # 5. Extract meta_data
        mime_type, _ = mimetypes.guess_type(safe_name)
        ffprobe_data = _run_ffprobe(str(temp_path))
        video_meta = extract_video_metadata(ffprobe_data) if ffprobe_data else {}

        # 6. Move to permanent evidence storage
        evidence_dir = Path(settings.evidence_storage_path) / case_id
        evidence_dir.mkdir(parents=True, exist_ok=True)
        # Use hash prefix + original name for uniqueness
        storage_name = f"{file_hash[:12]}_{safe_name}"
        storage_path = evidence_dir / storage_name
        shutil.move(str(temp_path), str(storage_path))

        # 7. Create database record
        evidence = Evidence(
            case_id=case_id,
            filename=storage_name,
            original_filename=original_filename,
            source_device=source_device,
            source_vendor=source_vendor or "Unknown",
            evidence_type=evidence_type,
            acquisition_method="file_upload",
            size=total_size,
            sha256=file_hash,
            mime_type=mime_type,
            acquired_at=datetime.now(timezone.utc),
            acquired_by=acquired_by or settings.default_investigator,
            meta_data={
                "ffprobe": ffprobe_data,
                "video": video_meta,
            } if ffprobe_data else None,
            status="INGESTED",
            storage_path=str(storage_path),
            codec=video_meta.get("codec"),
            resolution=video_meta.get("resolution"),
            fps=video_meta.get("fps"),
            duration=video_meta.get("duration"),
            has_audio=video_meta.get("has_audio"),
            container_format=video_meta.get("container_format"),
        )

        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)

        # 8. Create ledger event
        self.ledger.append_event(
            case_id=case_id,
            event_type="EVIDENCE_INGESTED",
            actor=acquired_by or settings.default_investigator,
            evidence_id=evidence.id,
            meta_data={
                "original_filename": original_filename,
                "sha256": file_hash,
                "size": total_size,
                "evidence_type": evidence_type,
            },
        )

        logger.info(
            "Evidence ingested",
            extra={
                "case_id": case_id,
                "evidence_id": evidence.id,
                "sha256": file_hash[:16] + "...",
                "size": total_size,
            },
        )

        return evidence

    def verify_evidence_integrity(self, evidence: Evidence) -> dict[str, Any]:
        """
        Verify that an evidence file has not been modified since ingestion.

        Recomputes SHA-256 and compares with stored hash.

        Returns:
            Dictionary with verification result.
        """
        storage_path = Path(evidence.storage_path)
        if not storage_path.exists():
            return {
                "valid": False,
                "stored_hash": evidence.sha256,
                "computed_hash": None,
                "detail": "Evidence file not found on disk",
            }

        computed_hash = sha256_file(storage_path)
        is_valid = computed_hash == evidence.sha256

        if not is_valid:
            logger.warning(
                "INTEGRITY FAILURE: Evidence hash mismatch",
                extra={
                    "evidence_id": evidence.id,
                    "stored": evidence.sha256[:16],
                    "computed": computed_hash[:16],
                },
            )

        return {
            "valid": is_valid,
            "stored_hash": evidence.sha256,
            "computed_hash": computed_hash,
            "detail": "HASH VERIFIED" if is_valid else "INTEGRITY FAILURE: Hash mismatch detected",
        }
