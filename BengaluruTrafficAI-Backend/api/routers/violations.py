"""
BengaluruTrafficAI — Violations Router
GET /violations          — paginated list with filters
GET /violations/{id}     — single record
POST /violations/ingest  — called by CV pipeline
PATCH /violations/{id}/review — officer approves/rejects
GET /violations/stats    — dashboard summary stats
"""

import time
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, desc

from ..database import get_db, ViolationRecord
from ..schemas import ViolationOut, ViolationReview, IngestPayload, StatsOut
from ..ws_manager import manager

logger = logging.getLogger("router.violations")
router = APIRouter(prefix="/violations", tags=["violations"])


@router.get("/stats", response_model=StatsOut)
def get_stats():
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    with get_db() as db:
        base = db.query(ViolationRecord).filter(ViolationRecord.timestamp >= today_start)
        total     = base.count()
        auto_app  = base.filter(ViolationRecord.auto_approve == True).count()
        pending   = base.filter(ViolationRecord.reviewed == False, ViolationRecord.auto_approve == False).count()

        avg_conf_row = base.with_entities(func.avg(ViolationRecord.confidence)).scalar()
        avg_conf = round(float(avg_conf_row or 0), 3)

        # Violation type breakdown
        breakdown_rows = (
            base.with_entities(ViolationRecord.violation_type, func.count())
            .group_by(ViolationRecord.violation_type)
            .all()
        )
        breakdown = {r[0]: r[1] for r in breakdown_rows}
        top_vtype = max(breakdown, key=breakdown.get) if breakdown else "N/A"

        # Hourly trend for today (last 12 hours)
        hourly = []
        for h in range(12):
            hour_start = (datetime.utcnow() - timedelta(hours=11-h)).replace(minute=0, second=0, microsecond=0).timestamp()
            hour_end   = hour_start + 3600
            count = db.query(ViolationRecord).filter(
                ViolationRecord.timestamp >= hour_start,
                ViolationRecord.timestamp <  hour_end,
            ).count()
            hourly.append(count)

        active_cams = db.query(ViolationRecord.camera_id).filter(
            ViolationRecord.timestamp >= today_start
        ).distinct().count()

    return StatsOut(
        total_today=total,
        auto_approved=auto_app,
        pending_review=pending,
        avg_confidence=avg_conf,
        top_violation=top_vtype,
        active_cameras=active_cams,
        violation_breakdown=breakdown,
        hourly_trend=hourly,
    )


@router.get("", response_model=list[ViolationOut])
def list_violations(
    camera_id:      str  = Query(None),
    violation_type: str  = Query(None),
    reviewed:       bool = Query(None),
    limit:          int  = Query(50, le=200),
    offset:         int  = Query(0),
):
    with get_db() as db:
        q = db.query(ViolationRecord).order_by(desc(ViolationRecord.timestamp))
        if camera_id:
            q = q.filter(ViolationRecord.camera_id == camera_id)
        if violation_type:
            q = q.filter(ViolationRecord.violation_type == violation_type)
        if reviewed is not None:
            q = q.filter(ViolationRecord.reviewed == reviewed)
        records = q.offset(offset).limit(limit).all()
        return [r.to_dict() for r in records]


@router.get("/{event_id}", response_model=ViolationOut)
def get_violation(event_id: str):
    with get_db() as db:
        r = db.query(ViolationRecord).filter(ViolationRecord.event_id == event_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Violation not found")
        return r.to_dict()


@router.post("/ingest", status_code=201)
async def ingest_violation(payload: IngestPayload):
    """
    Called by the CV pipeline (main.py) when a violation is confirmed.
    Saves to DB and broadcasts to all WebSocket clients instantly.
    """
    bbox = payload.bbox or []

    with get_db() as db:
        existing = db.query(ViolationRecord).filter(
            ViolationRecord.event_id == payload.event_id
        ).first()
        if existing:
            return {"status": "duplicate", "event_id": payload.event_id}

        record = ViolationRecord(
            event_id=payload.event_id,
            violation_type=payload.violation_type,
            camera_id=payload.camera_id,
            track_id=payload.track_id,
            plate_number=payload.plate_number,
            confidence=payload.confidence,
            severity=payload.severity,
            fine_inr=payload.fine_inr,
            auto_approve=payload.auto_approve,
            reviewed=payload.auto_approve,   # auto-approved = skip review queue
            approved=True if payload.auto_approve else None,
            frame_idx=payload.frame_idx,
            bbox_x1=bbox[0] if len(bbox) > 0 else None,
            bbox_y1=bbox[1] if len(bbox) > 1 else None,
            bbox_x2=bbox[2] if len(bbox) > 2 else None,
            bbox_y2=bbox[3] if len(bbox) > 3 else None,
            image_path=payload.image_path,
            image_hash=payload.image_hash,
            timestamp=payload.timestamp,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        data = record.to_dict()

    # Push to all connected dashboard clients immediately
    await manager.broadcast_violation(data)
    logger.info(f"Ingested + broadcast: {payload.violation_type} | {payload.camera_id} | plate={payload.plate_number}")

    return {"status": "created", "event_id": payload.event_id}


@router.patch("/{event_id}/review")
async def review_violation(event_id: str, body: ViolationReview):
    """Officer approves or rejects a violation from the dashboard."""
    with get_db() as db:
        r = db.query(ViolationRecord).filter(ViolationRecord.event_id == event_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Not found")
        r.reviewed = True
        r.approved = body.approved
        db.commit()
        data = r.to_dict()

    await manager.broadcast({"type": "review_update", "data": data})
    return data
