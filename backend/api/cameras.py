from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Camera
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = None
    source: Optional[str] = None
    timezone: str = "UTC"

class CameraResponse(BaseModel):
    id: str
    name: str
    location: Optional[str] = None
    source: Optional[str] = None
    timezone: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/cameras", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).all()
    return [CameraResponse.model_validate(c) for c in cameras]

@router.post("/cameras", response_model=CameraResponse)
def create_camera(cam: CameraCreate, db: Session = Depends(get_db)):
    new_cam = Camera(
        name=cam.name,
        location=cam.location,
        source=cam.source,
        timezone=cam.timezone
    )
    db.add(new_cam)
    db.commit()
    db.refresh(new_cam)
    return CameraResponse.model_validate(new_cam)

@router.get("/cameras/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    return CameraResponse.model_validate(cam)
