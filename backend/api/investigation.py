"""
SAKSHYA Investigation API

Face search, plate search, and unified investigator query.
All searches query actual persisted AI results — never fabricated.
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from sqlalchemy.orm import Session
import numpy as np
import logging

from backend.database import get_db
from backend.models import Evidence, AIResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/investigation/face-search")
async def face_search(
    case_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Search for a face across all evidence in a case.

    Computes the embedding of the uploaded reference face, then compares
    against all stored face embeddings using cosine similarity.

    Results are labelled POSSIBLE_MATCH — similarity does not prove identity.
    """
    from backend.ai.engine import ai_engine

    if not ai_engine._face_recognizer or not ai_engine._face_recognizer.is_available():
        raise HTTPException(status_code=503, detail="AI STATUS: MODEL UNAVAILABLE — Face recognition model not loaded")

    if not ai_engine._face_detector or not ai_engine._face_detector.is_available():
        raise HTTPException(status_code=503, detail="AI STATUS: MODEL UNAVAILABLE — Face detection model not loaded")

    # 1. Read uploaded image
    import cv2
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # 2. Detect face in reference image
    ref_faces = ai_engine._face_detector.detect(img)
    if not ref_faces:
        raise HTTPException(status_code=400, detail="No face detected in the reference image")

    # Use the highest-confidence face
    best_face = max(ref_faces, key=lambda d: d.confidence)
    if not best_face.bounding_box:
        raise HTTPException(status_code=400, detail="Face detected but no bounding box available")

    # 3. Compute reference embedding
    ref_embedding = ai_engine._face_recognizer.compute_embedding(img, best_face.bounding_box)
    if ref_embedding is None:
        raise HTTPException(status_code=500, detail="AI STATUS: INFERENCE FAILED — Could not compute face embedding")

    # 4. Query all face detections in this case that have embeddings
    evidence_ids = [
        e.id for e in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()
    ]

    if not evidence_ids:
        return []

    face_results = (
        db.query(AIResult)
        .filter(
            AIResult.evidence_id.in_(evidence_ids),
            AIResult.detection_type == "face",
        )
        .all()
    )

    # 5. Compare embeddings (brute-force cosine similarity)
    candidates = []
    for r in face_results:
        if r.embedding_reference:
            try:
                stored_emb = np.array(r.embedding_reference, dtype=np.float32)
                similarity = float(np.dot(ref_embedding.flatten(), stored_emb.flatten()) / (
                    np.linalg.norm(ref_embedding) * np.linalg.norm(stored_emb) + 1e-8
                ))
                if similarity > 0.3:  # Low threshold to surface candidates
                    candidates.append({
                        "candidate_id": r.id,
                        "evidence_id": r.evidence_id,
                        "timestamp": r.timestamp,
                        "similarity": round(similarity, 4),
                        "frame": r.frame_number,
                        "confidence": r.confidence,
                        "status": "POSSIBLE_MATCH",
                        "note": "Similarity-based candidate. Does not independently establish identity.",
                    })
            except Exception as e:
                logger.warning("Embedding comparison failed for %s: %s", r.id, e)

    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    return candidates[:50]


@router.post("/investigation/plate-search")
def plate_search(
    case_id: str,
    plate: str = Query(..., description="License plate text to search for"),
    db: Session = Depends(get_db),
):
    """
    Search for a license plate across all evidence in a case.

    Searches both raw_text and normalized_text fields in plate detections.
    """
    evidence_ids = [
        e.id for e in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()
    ]

    if not evidence_ids:
        return []

    plate_results = (
        db.query(AIResult)
        .filter(
            AIResult.evidence_id.in_(evidence_ids),
            AIResult.detection_type == "plate",
        )
        .all()
    )

    search_text = plate.upper().replace(" ", "").replace("-", "")
    candidates = []

    for r in plate_results:
        label = (r.label or "").upper().replace(" ", "").replace("-", "")
        raw = (r.meta_data or {}).get("raw_text", "").upper().replace(" ", "").replace("-", "") if r.meta_data else ""

        if search_text in label or search_text in raw or label in search_text:
            candidates.append({
                "candidate_id": r.id,
                "evidence_id": r.evidence_id,
                "plate": r.label,
                "raw_text": (r.meta_data or {}).get("raw_text"),
                "confidence": r.confidence,
                "timestamp": r.timestamp,
                "frame": r.frame_number,
            })

    candidates.sort(key=lambda c: c.get("confidence", 0), reverse=True)
    return candidates


@router.get("/investigation/search")
def investigation_search(
    case_id: str,
    q: str = None,
    db: Session = Depends(get_db),
):
    """
    Unified investigator query — searches across all detection types.
    """
    if not q:
        return {"results": [], "query": q, "case_id": case_id}

    evidence_ids = [
        e.id for e in db.query(Evidence.id).filter(Evidence.case_id == case_id).all()
    ]
    if not evidence_ids:
        return {"results": [], "query": q, "case_id": case_id}

    search_lower = q.lower()
    all_results = (
        db.query(AIResult)
        .filter(AIResult.evidence_id.in_(evidence_ids))
        .all()
    )

    matches = []
    for r in all_results:
        label = (r.label or "").lower()
        track = (r.track_id or "").lower()
        det_type = (r.detection_type or "").lower()

        if search_lower in label or search_lower in track or search_lower in det_type:
            matches.append({
                "id": r.id,
                "evidence_id": r.evidence_id,
                "detection_type": r.detection_type,
                "label": r.label,
                "confidence": r.confidence,
                "timestamp": r.timestamp,
                "frame_number": r.frame_number,
                "track_id": r.track_id,
            })

@router.post("/investigation/cross-camera-search")
def cross_camera_search(
    case_id: str,
    track_id: str = Query(..., description="Source track ID to search for"),
    evidence_id: str = Query(..., description="Source evidence ID"),
    db: Session = Depends(get_db),
):
    """
    Search for a person track across other cameras in the case.
    """
    from backend.ai.engine import ai_engine
    # Since OSNet is not implemented, we must return UNAVAILABLE
    raise HTTPException(status_code=503, detail="AI STATUS: MODEL UNAVAILABLE — Cross-camera Re-ID model (OSNet) not loaded")
