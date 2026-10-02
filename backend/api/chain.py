"""
SAKSHYA Chain of Custody API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Case, ChainEvent
from backend.schemas import ChainEventResponse, ChainVerifyResponse
from backend.services.ledger import LedgerService

router = APIRouter()


@router.get("/cases/{case_id}/chain", response_model=list[ChainEventResponse])
def get_chain(case_id: str, db: Session = Depends(get_db)):
    """Get the complete chain of custody for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    ledger = LedgerService(db)
    events = ledger.get_chain(case_id)
    return [ChainEventResponse.model_validate(e) for e in events]


@router.post("/cases/{case_id}/verify-chain", response_model=ChainVerifyResponse)
def verify_chain(case_id: str, db: Session = Depends(get_db)):
    """
    Verify the integrity of the case's chain of custody.

    Recomputes all event hashes and checks linkage.
    Reports VALID or INTEGRITY FAILURE with the first broken record.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    ledger = LedgerService(db)
    result = ledger.verify_chain(case_id)
    return ChainVerifyResponse(**result)


@router.get("/cases/{case_id}/chain-head")
def get_chain_head(case_id: str, db: Session = Depends(get_db)):
    """Get the current chain head hash for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    ledger = LedgerService(db)
    head = ledger.get_chain_head(case_id)
    count = ledger.get_event_count(case_id)

    return {
        "case_id": case_id,
        "chain_head": head,
        "event_count": count,
    }
