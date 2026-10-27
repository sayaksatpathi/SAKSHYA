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


def _stored_embedding(result: AIResult) -> np.ndarray | None:
    """Extract a persisted detection embedding, if present.

    Embeddings are stored as a plain list under ``meta_data["embedding"]`` at
    analysis time. Older rows may carry a JSON list in ``embedding_reference``.
    """
    meta = result.meta_data or {}
    raw = meta.get("embedding") if isinstance(meta, dict) else None
    if raw is None:
        raw = result.embedding_reference
    if raw is None:
        return None
    try:
        arr = np.asarray(raw, dtype=np.float32).flatten()
        return arr if arr.size else None
    except (ValueError, TypeError):
        return None


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(np.dot(a.flatten(), b.flatten()) / denom)


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
        stored_emb = _stored_embedding(r)
        if stored_emb is None:
            continue
        try:
            similarity = _cosine(ref_embedding, stored_emb)
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

    matches.sort(key=lambda m: (m.get("confidence") or 0), reverse=True)
    return {"results": matches, "query": q, "case_id": case_id, "count": len(matches)}


def _is_person(result: AIResult) -> bool:
    if result.detection_type == "person":
        return True
    return result.detection_type == "object" and (result.label or "").lower() == "person"


@router.post("/investigation/cross-camera-search")
def cross_camera_search(
    case_id: str,
    track_id: str = Query(..., description="Source track ID to search for"),
    evidence_id: str = Query(..., description="Source evidence ID"),
    threshold: float = Query(0.5, ge=0.0, le=1.0, description="Minimum cosine similarity"),
    db: Session = Depends(get_db),
):
    """
    Search for a person track across other cameras (evidence items) in the case
    using OSNet appearance embeddings.

    The source track's person embeddings are averaged into a query signature and
    compared (cosine similarity) against person detections in *other* evidence
    items. Results are labelled POSSIBLE_MATCH — appearance similarity does not
    independently establish identity.
    """
    from backend.ai.engine import ai_engine

    # Honesty contract: never fabricate matches when the model is not loaded.
    if not ai_engine._reid or not ai_engine._reid.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI STATUS: MODEL UNAVAILABLE — Cross-camera Re-ID model (OSNet) not loaded",
        )

    # 1. Build the query signature from the source track's person embeddings.
    source_results = (
        db.query(AIResult)
        .filter(
            AIResult.evidence_id == evidence_id,
            AIResult.track_id == track_id,
        )
        .all()
    )
    source_embeddings = [
        e for e in (_stored_embedding(r) for r in source_results if _is_person(r)) if e is not None
    ]
    if not source_embeddings:
        raise HTTPException(
            status_code=404,
            detail="No person Re-ID embeddings found for the source track. "
            "Re-run analysis with the Re-ID model enabled.",
        )
    query_sig = np.mean(np.stack(source_embeddings), axis=0)

    # 2. Gather person detections from OTHER evidence items in the same case.
    other_evidence_ids = [
        e.id
        for e in db.query(Evidence.id)
        .filter(Evidence.case_id == case_id, Evidence.id != evidence_id)
        .all()
    ]
    if not other_evidence_ids:
        return {"source_track": track_id, "matches": [], "count": 0,
                "note": "No other cameras/evidence in this case to search."}

    candidate_results = (
        db.query(AIResult)
        .filter(AIResult.evidence_id.in_(other_evidence_ids))
        .all()
    )

    # 3. Score the best detection per (evidence, track) so one person on another
    #    camera collapses to a single ranked candidate.
    best_by_track: dict[tuple, dict] = {}
    for r in candidate_results:
        if not _is_person(r):
            continue
        emb = _stored_embedding(r)
        if emb is None:
            continue
        similarity = _cosine(query_sig, emb)
        if similarity < threshold:
            continue
        key = (r.evidence_id, r.track_id or r.id)
        prev = best_by_track.get(key)
        if prev is None or similarity > prev["similarity"]:
            best_by_track[key] = {
                "candidate_id": r.id,
                "evidence_id": r.evidence_id,
                "track_id": r.track_id,
                "similarity": round(similarity, 4),
                "timestamp": r.timestamp,
                "frame": r.frame_number,
                "confidence": r.confidence,
                "status": "POSSIBLE_MATCH",
                "note": "Appearance-based candidate. Does not independently establish identity.",
            }

    matches = sorted(best_by_track.values(), key=lambda c: c["similarity"], reverse=True)
    return {
        "source_track": track_id,
        "source_evidence": evidence_id,
        "threshold": threshold,
        "matches": matches[:50],
        "count": len(matches),
    }
