"""
SAKSHYA Evidence API
"""

import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path

from backend.database import get_db
from backend.models import Case, Evidence, EvidenceSegment, AIResult, User
from backend.auth import get_current_investigator
from backend.schemas import (
    EvidenceResponse, EvidenceListResponse, SegmentResponse,
    TimelineEvent, TimelineResponse, ForensicFindingResponse
)
from backend.services.acquisition import AcquisitionService
from backend.services.recovery import RecoveryEngine
from backend.crypto.hashing import sha256_file

router = APIRouter()


def _evidence_response(evidence: Evidence, db: Session) -> EvidenceResponse:
    """Build an EvidenceResponse with counts."""
    resp = EvidenceResponse.model_validate(evidence)
    resp.segment_count = db.query(func.count(EvidenceSegment.id)).filter(
        EvidenceSegment.evidence_id == evidence.id
    ).scalar() or 0
    resp.ai_result_count = db.query(func.count(AIResult.id)).filter(
        AIResult.evidence_id == evidence.id
    ).scalar() or 0
    return resp


@router.post("/cases/{case_id}/evidence", response_model=EvidenceResponse, status_code=201)
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    source_device: str = Form(default=None),
    source_vendor: str = Form(default=None),
    evidence_type: str = Form(default="video"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_investigator),
):
    """
    Upload evidence to a case.

    The original file is never modified. SHA-256 is computed immediately.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        
    if current_user.role != "admin" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    service = AcquisitionService(db)

    try:
        evidence = service.ingest_file(
            case_id=case_id,
            file_stream=file.file,
            original_filename=file.filename or "unknown",
            source_device=source_device,
            source_vendor=source_vendor,
            evidence_type=evidence_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _evidence_response(evidence, db)


@router.get("/cases/{case_id}/evidence", response_model=EvidenceListResponse)
def list_case_evidence(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """List all evidence for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    if current_user.role != "admin" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    items = db.query(Evidence).filter(Evidence.case_id == case_id).order_by(Evidence.acquired_at.desc()).all()

    return EvidenceListResponse(
        evidence=[_evidence_response(e, db) for e in items],
        total=len(items),
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """Get evidence details."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    return _evidence_response(evidence, db)


@router.get("/evidence/{evidence_id}/stream")
def stream_evidence(
    evidence_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_investigator)
):
    """
    Stream evidence file directly to browser video player.
    Supports HTTP Range requests for seeking.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    file_path = Path(evidence.storage_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found on disk")
        
    # Prevent path traversal
    file_size = file_path.stat().st_size
    mime_type = evidence.mime_type or "video/mp4"
    
    range_header = request.headers.get("Range")
    if range_header:
        import re
        match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid Range header")
            
        byte1 = int(match.group(1))
        byte2 = match.group(2)
        if byte2:
            byte2 = int(byte2)
        else:
            byte2 = file_size - 1

        byte2 = min(byte2, file_size - 1)
        length = byte2 - byte1 + 1

        def file_iterator(start, size, chunk_size=8192):
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = size
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)

        headers = {
            "Content-Range": f"bytes {byte1}-{byte2}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        }
        return StreamingResponse(
            file_iterator(byte1, length), 
            status_code=206, 
            headers=headers, 
            media_type=mime_type
        )
    
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
    }
    def full_file_iterator(chunk_size=8192):
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk

    return StreamingResponse(
        full_file_iterator(), 
        status_code=200, 
        headers=headers, 
        media_type=mime_type
    )

@router.get("/evidence/{evidence_id}/verify")
def verify_evidence(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """
    Recomputes SHA-256 and compares with the stored hash.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    service = AcquisitionService(db)
    return service.verify_evidence_integrity(evidence)


@router.post("/evidence/{evidence_id}/recover", response_model=list[SegmentResponse])
def recover_evidence(evidence_id: str,
    use_demo: bool = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator),
):
    """
    Attempt recovery of deleted/fragmented segments from evidence.

    Defaults to real recovery. Set use_demo=true for demonstration recovery simulation,
    or configure SAKSHYA_AI_MODE=demo globally.
    """
    from backend.config import settings
    if use_demo is None:
        use_demo = settings.sakshya_ai_mode.lower() == "demo"
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    engine = RecoveryEngine(db)
    segments = engine.recover(evidence, use_demo=use_demo)

    return [SegmentResponse.model_validate(s) for s in segments]


@router.post("/evidence/{evidence_id}/forensics", response_model=list[ForensicFindingResponse])
def run_video_forensics(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """Run frame-level video forensics on evidence."""
    from backend.services.forensics import VideoForensicsService
    
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    service = VideoForensicsService(db)
    findings = service.analyze_evidence(evidence)
    
    if findings:
        from backend.services.ledger import LedgerService
        ledger = LedgerService(db)
        ledger.append_event(
            case_id=evidence.case_id,
            event_type="FORENSIC_ANALYSIS_COMPLETED",
            actor="SAKSHYA Video Forensics",
            evidence_id=evidence.id,
            meta_data={
                "total_findings": len(findings),
                "finding_types": list(set([f.type for f in findings]))
            }
        )

    return [ForensicFindingResponse.model_validate(f) for f in findings]

@router.get("/evidence/{evidence_id}/forensics", response_model=list[ForensicFindingResponse])
def get_video_forensics(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """Get frame-level video forensics on evidence."""
    from backend.models import ForensicFinding
    findings = db.query(ForensicFinding).filter(ForensicFinding.evidence_id == evidence_id).all()
    return [ForensicFindingResponse.model_validate(f) for f in findings]

@router.get("/evidence/{evidence_id}/segments", response_model=list[SegmentResponse])
def list_segments(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """List recovered segments for evidence."""
    segments = (
        db.query(EvidenceSegment)
        .filter(EvidenceSegment.evidence_id == evidence_id)
        .order_by(EvidenceSegment.created_at)
        .all()
    )
    return [SegmentResponse.model_validate(s) for s in segments]


@router.get("/evidence/{evidence_id}/timeline", response_model=TimelineResponse)
def get_evidence_timeline(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """
    Get AI detection timeline for evidence.

    Returns chronologically ordered events from AI analysis.
    """
    results = (
        db.query(AIResult)
        .filter(AIResult.evidence_id == evidence_id)
        .order_by(AIResult.timestamp.asc())
        .all()
    )

    events = []
    for r in results:
        label = r.label or r.detection_type
        if r.track_id:
            label = f"{label} #{r.track_id}"

        events.append(TimelineEvent(
            timestamp=r.timestamp or 0,
            event_type=r.detection_type,
            label=label,
            confidence=r.confidence,
            evidence_id=evidence_id,
            meta_data={
                "frame": r.frame_number,
                "model": r.model_name,
                "bounding_box": r.bounding_box,
            },
        ))

    return TimelineResponse(events=events, total=len(events))


@router.get("/evidence/{evidence_id}/stream")
async def stream_evidence(evidence_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """Stream evidence video file."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    file_path = Path(evidence.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Evidence file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=evidence.mime_type or "video/mp4",
        filename=evidence.original_filename,
    )
