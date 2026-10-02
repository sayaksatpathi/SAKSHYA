"""
SAKSHYA Case Management API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import Case, Evidence, User
from backend.schemas import CaseCreate, CaseResponse, CaseListResponse
from backend.services.ledger import LedgerService
from backend.config import settings
from backend.auth import get_current_investigator

router = APIRouter()


@router.post("/cases", response_model=CaseResponse, status_code=201)
def create_case(case_data: CaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """Create a new forensic investigation case."""
    # Check for duplicate case number
    existing = db.query(Case).filter(Case.case_number == case_data.case_number).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Case number '{case_data.case_number}' already exists")

    case = Case(
        case_number=case_data.case_number,
        title=case_data.title,
        description=case_data.description,
        investigator=current_user.username,
        investigator_id=current_user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Create ledger event for case creation
    ledger = LedgerService(db)
    ledger.append_event(
        case_id=case.id,
        event_type="CASE_CREATED",
        actor=case.investigator,
        meta_data={
            "case_number": case.case_number,
            "title": case.title,
        },
    )

    # Get evidence count
    response = CaseResponse.model_validate(case)
    response.evidence_count = 0
    return response


@router.get("/cases", response_model=CaseListResponse)
def list_cases(
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_investigator),
):
    """List all cases, optionally filtered by status."""
    query = db.query(Case)
    if current_user.role != "admin":
        query = query.filter(Case.investigator_id == current_user.id)
    
    if status:
        query = query.filter(Case.status == status)

    total = query.count()
    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for case in cases:
        resp = CaseResponse.model_validate(case)
        resp.evidence_count = db.query(func.count(Evidence.id)).filter(Evidence.case_id == case.id).scalar() or 0
        result.append(resp)

    return CaseListResponse(cases=result, total=total)


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """Get a specific case by ID."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        
    if current_user.role != "admin" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    resp = CaseResponse.model_validate(case)
    resp.evidence_count = db.query(func.count(Evidence.id)).filter(Evidence.case_id == case.id).scalar() or 0
    return resp

@router.get("/cases/{case_id}/timeline")
def get_case_timeline(case_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_investigator)):
    """Get timeline of events for a case."""
    from backend.models import ChainEvent
    from backend.schemas import CaseTimelineEvent, CaseTimelineResponse
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        
    if current_user.role != "admin" and case.investigator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
        
    events = db.query(ChainEvent).filter(ChainEvent.case_id == case_id).order_by(ChainEvent.timestamp.asc()).all()
    
    timeline_events = []
    for evt in events:
        evidence_id = evt.meta_data.get("evidence_id") if evt.meta_data else None
        title = evt.event_type.replace("_", " ").title()
        
        timeline_events.append(CaseTimelineEvent(
            id=evt.id,
            timestamp=evt.timestamp,
            type=evt.event_type,
            title=title,
            description=f"Recorded by {evt.actor}",
            case_id=evt.case_id,
            evidence_id=evidence_id,
            metadata=evt.meta_data,
            hash=evt.event_hash
        ))
        
    return CaseTimelineResponse(events=timeline_events, total=len(timeline_events))

@router.post("/cases/{case_id}/simulate-tamper")
def simulate_tamper(case_id: str, db: Session = Depends(get_db)):
    """DEMO ONLY: Simulates tampering with the first evidence file of a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    evidence = db.query(Evidence).filter(Evidence.case_id == case_id).first()
    if not evidence:
        raise HTTPException(status_code=400, detail="No evidence to tamper with")
        
    import os
    file_path = evidence.storage_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Evidence file missing")
        
    with open(file_path, "ab") as f:
        f.write(b"TAMPERED_DATA")
        
    return {"message": "Evidence file tampered successfully. Run Verification to detect."}

@router.get("/cases/{case_id}/stats")
def get_case_stats(case_id: str, db: Session = Depends(get_db)):
    """Get aggregated statistics for a case."""
    from backend.models import AIResult, RecoveredSegment, ForensicFinding, Camera
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    evidence_ids = [e.id for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()]
    evidence_count = len(evidence_ids)
    
    ai_count = db.query(func.count(AIResult.id)).filter(AIResult.evidence_id.in_(evidence_ids)).scalar() if evidence_count > 0 else 0
    recovery_count = db.query(func.count(RecoveredSegment.id)).filter(RecoveredSegment.evidence_id.in_(evidence_ids)).scalar() if evidence_count > 0 else 0
    forensic_count = db.query(func.count(ForensicFinding.id)).filter(ForensicFinding.evidence_id.in_(evidence_ids)).scalar() if evidence_count > 0 else 0
    
    # Cameras could be global or per case, but we just return total count here
    camera_count = db.query(func.count(Camera.id)).scalar()
    
    return {
        "evidence_count": evidence_count,
        "recovered_artifacts": recovery_count,
        "ai_analyses": ai_count,
        "forensic_findings": forensic_count,
        "cameras": camera_count
    }
