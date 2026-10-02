"""
SAKSHYA Report API — adds report endpoint to the cases API
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Case
from backend.services.report import ReportService

# Note: This router is added to the cases.py router
# Import and include in main.py if separated

router = APIRouter()


@router.post("/cases/{case_id}/report")
def generate_report(case_id: str, db: Session = Depends(get_db)):
    """
    Generate a forensic PDF report for a case.
    Saves it to disk and returns metadata.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    try:
        service = ReportService(db)
        pdf_bytes = service.generate_report(case_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    import hashlib
    import datetime
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    # Save the PDF to disk in the case's storage directory
    from backend.config import settings
    from pathlib import Path
    case_dir = Path(settings.evidence_storage_path) / case.id
    case_dir.mkdir(parents=True, exist_ok=True)
    report_path = case_dir / "report.pdf"
    
    with open(report_path, "wb") as f:
        f.write(pdf_bytes)

    # We return the metadata. 
    return {
        "id": case.id, # Using case ID as report ID for simplicity
        "case_id": case.id,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "generated_by": case.investigator,
        "sha256": pdf_hash,
        "download_url": f"/api/reports/{case.id}"
    }

@router.get("/reports/{report_id}")
def download_report(report_id: str):
    """Download the generated report."""
    from backend.config import settings
    from pathlib import Path
    
    report_path = Path(settings.evidence_storage_path) / report_id / "report.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
        
    return Response(
        content=report_path.read_bytes(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="SAKSHYA_Report_{report_id}.pdf"',
        },
    )

