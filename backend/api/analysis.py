"""
SAKSHYA AI Analysis API

IMPORTANT: AI results are investigative aids, not definitive identifications.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timezone

from backend.config import settings
from backend.database import get_db, SessionLocal
from backend.models import Evidence, AIResult, Job, User, Case
from backend.auth import get_current_investigator
from backend.schemas import AIResultResponse, AIResultListResponse, JobResponse
from backend.services.analysis import VideoAnalysisService

router = APIRouter()

def background_analyze(evidence_id: str, job_id: str, frame_sample_rate: int, detection_confidence: float):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return
    
    try:
        job.status = "PROCESSING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        service = VideoAnalysisService(db)
        
        if settings.sakshya_ai_mode.lower() == "demo":
            results = service.generate_demo_results(evidence)
        else:
            results = service.analyze(
                evidence,
                frame_sample_rate=frame_sample_rate,
                detection_confidence=detection_confidence,
            )
            
        job.status = "COMPLETED"
        job.progress = 100.0
        job.finished_at = datetime.now(timezone.utc)
        job.result = {"detections_count": len(results)}
        db.commit()
    except Exception as e:
        job.status = "FAILED"
        job.error = str(e)
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()

@router.post("/evidence/{evidence_id}/analyze_async", response_model=JobResponse)
def analyze_evidence_async(
    evidence_id: str,
    background_tasks: BackgroundTasks,
    frame_sample_rate: int = Query(default=None, description="Override frame sample rate"),
    detection_confidence: float = Query(default=None, description="Override confidence threshold"),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator),
):
    """
    Run AI analysis on evidence asynchronously in the background.
    Returns a Job ID which can be polled for status.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
        
    # Idempotency / Deduplication check
    existing_job = db.query(Job).filter(
        Job.evidence_id == evidence_id,
        Job.job_type == "AI_ANALYSIS",
        Job.status.in_(["QUEUED", "PROCESSING"])
    ).first()
    
    if existing_job:
        return JobResponse.model_validate(existing_job)
        
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        evidence_id=evidence_id,
        case_id=evidence.case_id,
        job_type="AI_ANALYSIS",
        status="QUEUED"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(
        background_analyze,
        evidence_id=evidence_id,
        job_id=job_id,
        frame_sample_rate=frame_sample_rate,
        detection_confidence=detection_confidence
    )
    
    return JobResponse.model_validate(job)


@router.post("/evidence/{evidence_id}/analyze", response_model=AIResultListResponse)
def analyze_evidence(evidence_id: str,
    frame_sample_rate: int = Query(default=None, description="Override frame sample rate"),
    detection_confidence: float = Query(default=None, description="Override confidence threshold"),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator),
):
    """
    Run AI analysis on evidence.

    Behaviour depends on SAKSHYA_AI_MODE:
    - "real": Uses real model inference. Returns 503 if no models are available.
    - "demo": Uses synthetic demo results for demonstration.

    IMPORTANT: AI results are investigative aids, not definitive identifications.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
        
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if current_user.role != "admin" and case and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    service = VideoAnalysisService(db)
    ai_mode = settings.sakshya_ai_mode.lower()

    if ai_mode == "demo":
        results = service.generate_demo_results(evidence)
        return AIResultListResponse(
            results=[AIResultResponse.model_validate(r) for r in results],
            total=len(results),
            mode="demo",
        )

    # --- REAL MODE ---
    from backend.ai.engine import ai_engine
    has_models = any(ai_engine.available_models().values())

    if not has_models:
        raise HTTPException(
            status_code=503,
            detail="AI STATUS: MODEL UNAVAILABLE — No AI models available for inference. "
                   "Install models per models/README.md or set SAKSHYA_AI_MODE=demo.",
        )

    results = service.analyze(
        evidence,
        frame_sample_rate=frame_sample_rate,
        detection_confidence=detection_confidence,
    )

    return AIResultListResponse(
        results=[AIResultResponse.model_validate(r) for r in results],
        total=len(results),
        mode="real",
    )


@router.get("/evidence/{evidence_id}/detections", response_model=AIResultListResponse)
def get_detections(evidence_id: str,
    detection_type: str = None,
    min_confidence: float = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator),
):
    """Get AI detection results for evidence, with optional filtering."""
    query = db.query(AIResult).filter(AIResult.evidence_id == evidence_id)

    if detection_type:
        query = query.filter(AIResult.detection_type == detection_type)
    if min_confidence is not None:
        query = query.filter(AIResult.confidence >= min_confidence)

    total = query.count()
    results = query.order_by(AIResult.timestamp.asc()).offset(skip).limit(limit).all()

    return AIResultListResponse(
        results=[AIResultResponse.model_validate(r) for r in results],
        total=total,
    )


@router.get("/cases/{case_id}/detections", response_model=AIResultListResponse)
def get_case_detections(
    case_id: str,
    detection_type: str = None,
    min_confidence: float = None,
    db: Session = Depends(get_db),
):
    """Get all AI detections across all evidence in a case."""
    from backend.models import Evidence

    evidence_ids = [
        e.id for e in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()
    ]

    if not evidence_ids:
        return AIResultListResponse(results=[], total=0)

    query = db.query(AIResult).filter(AIResult.evidence_id.in_(evidence_ids))

    if detection_type:
        query = query.filter(AIResult.detection_type == detection_type)
    if min_confidence is not None:
        query = query.filter(AIResult.confidence >= min_confidence)

    total = query.count()
    results = query.order_by(AIResult.timestamp.asc()).limit(500).all()

    return AIResultListResponse(
        results=[AIResultResponse.model_validate(r) for r in results],
        total=total,
    )
