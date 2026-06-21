"""
BengaluruTrafficAI — Pydantic Schemas
Component 4c: Request/response models for all API endpoints.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ViolationOut(BaseModel):
    id:             int
    event_id:       str
    violation_type: str
    camera_id:      str
    track_id:       Optional[int]
    plate_number:   Optional[str]
    confidence:     float
    severity:       int
    fine_inr:       int
    auto_approve:   bool
    reviewed:       bool
    approved:       Optional[bool]
    image_path:     Optional[str]
    timestamp:      float
    created_at:     Optional[str]

    class Config:
        from_attributes = True


class ViolationReview(BaseModel):
    approved: bool


class CameraOut(BaseModel):
    camera_id: str
    name:      str
    location:  str
    lat:       Optional[float]
    lon:       Optional[float]
    active:    bool

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_today:        int
    auto_approved:      int
    pending_review:     int
    avg_confidence:     float
    top_violation:      str
    active_cameras:     int
    violation_breakdown: dict
    hourly_trend:       list


class IngestPayload(BaseModel):
    """Posted by the CV pipeline when a violation is detected."""
    event_id:       str
    violation_type: str
    camera_id:      str
    track_id:       Optional[int] = None
    plate_number:   Optional[str] = None
    confidence:     float
    severity:       int
    fine_inr:       int
    auto_approve:   bool
    frame_idx:      int
    timestamp:      float
    bbox:           Optional[list[int]] = None
    image_path:     Optional[str] = None
    image_hash:     Optional[str] = None
