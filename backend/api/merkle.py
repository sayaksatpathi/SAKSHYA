"""
SAKSHYA Merkle Tree API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Case, Evidence, ChainEvent, MerkleRecord
from backend.schemas import MerkleResponse, MerkleProofResponse, MerkleVerifyResponse
from backend.crypto.merkle import MerkleTree
from backend.services.ledger import LedgerService
from backend.config import settings

router = APIRouter()


@router.post("/cases/{case_id}/merkle", response_model=MerkleResponse, status_code=201)
def build_merkle_tree(case_id: str, db: Session = Depends(get_db)):
    """
    Build a Merkle tree from all evidence hashes in a case.

    The Merkle root provides efficient integrity verification
    of the entire evidence set.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    # Collect all evidence hashes
    evidence_items = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.acquired_at)
        .all()
    )

    if not evidence_items:
        raise HTTPException(status_code=400, detail="No evidence in this case to build Merkle tree")

    leaves = [e.sha256 for e in evidence_items]

    # Build the tree
    tree = MerkleTree(leaves)

    # Store the record
    record = MerkleRecord(
        case_id=case_id,
        root_hash=tree.root,
        leaf_count=tree.leaf_count,
        leaves=tree.leaves,
        algorithm="SHA-256",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Create ledger event
    ledger = LedgerService(db)
    ledger.append_event(
        case_id=case_id,
        event_type="MERKLE_ROOT_CREATED",
        actor=settings.default_investigator,
        meta_data={
            "merkle_root": tree.root,
            "leaf_count": tree.leaf_count,
            "algorithm": "SHA-256",
        },
    )

    return MerkleResponse.model_validate(record)


@router.get("/cases/{case_id}/merkle", response_model=list[MerkleResponse])
def list_merkle_records(case_id: str, db: Session = Depends(get_db)):
    """List all Merkle tree records for a case."""
    records = (
        db.query(MerkleRecord)
        .filter(MerkleRecord.case_id == case_id)
        .order_by(MerkleRecord.created_at.desc())
        .all()
    )
    return [MerkleResponse.model_validate(r) for r in records]


@router.get("/cases/{case_id}/merkle/{merkle_id}/proof/{leaf_index}", response_model=MerkleProofResponse)
def get_merkle_proof(case_id: str, merkle_id: str, leaf_index: int, db: Session = Depends(get_db)):
    """
    Get a Merkle proof for a specific leaf (evidence hash).

    The proof allows independent verification that the leaf
    is included in the Merkle root.
    """
    record = db.query(MerkleRecord).filter(
        MerkleRecord.id == merkle_id, MerkleRecord.case_id == case_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Merkle record not found")

    if not record.leaves:
        raise HTTPException(status_code=400, detail="Merkle record has no stored leaves")

    if leaf_index < 0 or leaf_index >= len(record.leaves):
        raise HTTPException(
            status_code=400,
            detail=f"Leaf index must be 0-{len(record.leaves) - 1}"
        )

    tree = MerkleTree(record.leaves)
    proof = tree.get_proof(leaf_index)

    return MerkleProofResponse(
        leaf_hash=record.leaves[leaf_index],
        root_hash=tree.root,
        proof=proof,
        valid=MerkleTree.verify_proof(record.leaves[leaf_index], proof, tree.root),
    )


@router.post("/cases/{case_id}/merkle/{merkle_id}/verify", response_model=MerkleVerifyResponse)
def verify_merkle(case_id: str, merkle_id: str, db: Session = Depends(get_db)):
    """
    Verify a Merkle tree by recomputing the root from stored leaves.

    Compares the recomputed root with the stored root.
    """
    record = db.query(MerkleRecord).filter(
        MerkleRecord.id == merkle_id, MerkleRecord.case_id == case_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Merkle record not found")

    if not record.leaves:
        raise HTTPException(status_code=400, detail="Merkle record has no stored leaves")

    tree = MerkleTree(record.leaves)
    computed_root = tree.root
    is_valid = computed_root == record.root_hash

    return MerkleVerifyResponse(
        valid=is_valid,
        computed_root=computed_root,
        stored_root=record.root_hash,
        leaf_count=len(record.leaves),
    )
