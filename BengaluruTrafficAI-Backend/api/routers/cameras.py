"""
BengaluruTrafficAI — Cameras Router
GET /cameras          — list all cameras
GET /cameras/{id}     — single camera
"""

from fastapi import APIRouter, HTTPException
from ..database import get_db, CameraRecord
from ..schemas import CameraOut

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraOut])
def list_cameras():
    with get_db() as db:
        return [c.to_dict() for c in db.query(CameraRecord).all()]


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: str):
    with get_db() as db:
        c = db.query(CameraRecord).filter(CameraRecord.camera_id == camera_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Camera not found")
        return c.to_dict()
