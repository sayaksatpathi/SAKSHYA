"""
SAKSHYA Trust API — Integration with the independent trust authority
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Case, TrustReceipt
from backend.schemas import TrustReceiptResponse, TrustVerifyResponse
from backend.services.ledger import LedgerService
from backend.services.trust_client import TrustClient, TrustServiceUnavailable, TrustServiceError
from backend.config import settings

router = APIRouter()


@router.post("/cases/{case_id}/trust-sign", response_model=TrustReceiptResponse, status_code=201)
async def sign_with_trust(case_id: str, db: Session = Depends(get_db)):
    """
    Request an independent trust signature for the case's chain head.

    Sends the chain head (and Merkle root if available) to the
    independent trust authority for signing.

    The trust authority's signing secret is NOT held by this application.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    ledger = LedgerService(db)
    chain_head = ledger.get_chain_head(case_id)
    if not chain_head:
        raise HTTPException(status_code=400, detail="No chain events exist for this case")

    # Get latest Merkle root if available
    from backend.models import MerkleRecord
    latest_merkle = (
        db.query(MerkleRecord)
        .filter(MerkleRecord.case_id == case_id)
        .order_by(MerkleRecord.created_at.desc())
        .first()
    )
    merkle_root = latest_merkle.root_hash if latest_merkle else None

    # Call trust service
    client = TrustClient()
    try:
        result = await client.sign(
            chain_head=chain_head,
            case_id=case_id,
            merkle_root=merkle_root,
        )
    except TrustServiceUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )
    except TrustServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Store the receipt
    from datetime import datetime
    receipt = TrustReceipt(
        case_id=case_id,
        chain_head=chain_head,
        merkle_root=merkle_root,
        signature=result["signature"],
        timestamp=datetime.fromisoformat(result["timestamp"]),
        algorithm=result["algorithm"],
        authority_id=result["authority_id"],
        key_version=result.get("key_version"),
        verification_status="SIGNED",
        meta_data={
            "receipt_id": result.get("receipt_id"),
            "note": "This prototype trust service is not a government certification authority.",
        },
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    # Create ledger event
    ledger.append_event(
        case_id=case_id,
        event_type="TRUST_RECEIPT_ISSUED",
        actor="Trust Authority",
        meta_data={
            "authority_id": result["authority_id"],
            "algorithm": result["algorithm"],
            "chain_head": chain_head[:16] + "...",
            "signature": result["signature"][:16] + "...",
        },
    )

    return TrustReceiptResponse.model_validate(receipt)


@router.post("/cases/{case_id}/trust-verify", response_model=TrustVerifyResponse)
async def verify_trust(case_id: str, db: Session = Depends(get_db)):
    """
    Verify the latest trust receipt for a case.

    Sends the chain head and signature back to the trust authority
    for independent verification.
    """
    latest_receipt = (
        db.query(TrustReceipt)
        .filter(TrustReceipt.case_id == case_id)
        .order_by(TrustReceipt.timestamp.desc())
        .first()
    )
    if not latest_receipt:
        raise HTTPException(status_code=404, detail="No trust receipt found for this case")

    client = TrustClient()
    try:
        from datetime import timezone
        result = await client.verify(
            chain_head=latest_receipt.chain_head,
            signature=latest_receipt.signature,
            case_id=latest_receipt.case_id,
            timestamp=latest_receipt.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            authority_key_id=latest_receipt.key_version,
            merkle_root=latest_receipt.merkle_root,
            manifest_hash=latest_receipt.meta_data.get("manifest_hash") if latest_receipt.meta_data else None,
        )
    except TrustServiceUnavailable as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )

    # Update verification status
    latest_receipt.verification_status = "VERIFIED" if result["valid"] else "INVALID"
    db.commit()

    return TrustVerifyResponse(**result)


@router.get("/cases/{case_id}/trust-receipts", response_model=list[TrustReceiptResponse])
def list_trust_receipts(case_id: str, db: Session = Depends(get_db)):
    """List all trust receipts for a case."""
    receipts = (
        db.query(TrustReceipt)
        .filter(TrustReceipt.case_id == case_id)
        .order_by(TrustReceipt.timestamp.desc())
        .all()
    )
    return [TrustReceiptResponse.model_validate(r) for r in receipts]
