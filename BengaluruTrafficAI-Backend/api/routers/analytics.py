"""
BengaluruTrafficAI — Analytics & Reporting Router
GET /analytics/trends        — hourly/daily trends
GET /analytics/heatmap       — violation hotspots by location
GET /analytics/cameras       — per-camera statistics
GET /analytics/report        — generate PDF/CSV report
GET /analytics/realtime      — real-time dashboard metrics
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, and_
from typing import Optional, List
import json

from ..database import get_db, ViolationRecord, CameraRecord, AnalyticsSnapshot
from ..schemas import CameraOut

logger = logging.getLogger("router.analytics")
router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/trends")
def get_trends(
    period: str = Query("24h", pattern="^(24h|7d|30d)$"),
    camera_id: Optional[str] = None,
    violation_type: Optional[str] = None,
):
    """
    Get violation trends over time.
    
    Parameters:
        period: 24h (hourly), 7d (daily), 30d (daily)
        camera_id: filter by specific camera
        violation_type: filter by violation type
    
    Returns:
        {
            "labels": ["00:00", "01:00", ...],
            "datasets": [
                {"label": "no_helmet", "data": [5, 8, 12, ...]},
                ...
            ]
        }
    """
    now = datetime.utcnow()
    
    if period == "24h":
        start_time = (now - timedelta(hours=24)).timestamp()
        bucket_size = 3600  # 1 hour
        num_buckets = 24
        label_format = lambda i: (now - timedelta(hours=23-i)).strftime("%H:%M")
    elif period == "7d":
        start_time = (now - timedelta(days=7)).timestamp()
        bucket_size = 86400  # 1 day
        num_buckets = 7
        label_format = lambda i: (now - timedelta(days=6-i)).strftime("%b %d")
    else:  # 30d
        start_time = (now - timedelta(days=30)).timestamp()
        bucket_size = 86400
        num_buckets = 30
        label_format = lambda i: (now - timedelta(days=29-i)).strftime("%b %d")
    
    with get_db() as db:
        query = db.query(ViolationRecord).filter(
            ViolationRecord.timestamp >= start_time
        )
        
        if camera_id:
            query = query.filter(ViolationRecord.camera_id == camera_id)
        
        if violation_type:
            query = query.filter(ViolationRecord.violation_type == violation_type)
        
        violations = query.all()
    
    # Group by violation type and time bucket
    datasets = {}
    
    for v in violations:
        bucket_idx = int((v.timestamp - start_time) / bucket_size)
        if bucket_idx >= num_buckets:
            bucket_idx = num_buckets - 1
        
        if v.violation_type not in datasets:
            datasets[v.violation_type] = [0] * num_buckets
        
        datasets[v.violation_type][bucket_idx] += 1
    
    # Format for charting library
    labels = [label_format(i) for i in range(num_buckets)]
    chart_datasets = [
        {
            "label": vtype.replace("_", " ").title(),
            "data": counts
        }
        for vtype, counts in datasets.items()
    ]
    
    return {
        "labels": labels,
        "datasets": chart_datasets,
        "period": period,
        "total_violations": sum(sum(d["data"]) for d in chart_datasets),
    }


@router.get("/heatmap")
def get_heatmap(
    hours: int = Query(24, le=168),  # Max 7 days
):
    """
    Get violation heatmap by camera location.
    
    Returns:
        [
            {
                "camera_id": "cam_01",
                "name": "Silk Board",
                "lat": 12.9178,
                "lon": 77.6227,
                "count": 145,
                "severity_avg": 3.2
            },
            ...
        ]
    """
    start_time = (datetime.utcnow() - timedelta(hours=hours)).timestamp()
    
    with get_db() as db:
        # Get violation counts per camera
        counts = db.query(
            ViolationRecord.camera_id,
            func.count(ViolationRecord.id).label("count"),
            func.avg(ViolationRecord.severity).label("severity_avg"),
        ).filter(
            ViolationRecord.timestamp >= start_time
        ).group_by(
            ViolationRecord.camera_id
        ).all()
        
        # Join with camera metadata
        cameras = {c.camera_id: c for c in db.query(CameraRecord).all()}
        
        heatmap_data = []
        for cam_id, count, sev_avg in counts:
            cam = cameras.get(cam_id)
            if cam:
                heatmap_data.append({
                    "camera_id": cam_id,
                    "name": cam.name,
                    "lat": cam.lat,
                    "lon": cam.lon,
                    "count": count,
                    "severity_avg": round(float(sev_avg or 0), 2),
                })
        
        return sorted(heatmap_data, key=lambda x: x["count"], reverse=True)


@router.get("/cameras/{camera_id}/stats")
def get_camera_stats(camera_id: str, hours: int = Query(24)):
    """
    Detailed statistics for a specific camera.
    
    Returns:
        {
            "camera": {...},
            "total_violations": 45,
            "by_type": {"no_helmet": 20, ...},
            "by_hour": [...],
            "avg_confidence": 0.85,
            "top_plates": [{"plate": "KA01AB1234", "count": 3}, ...]
        }
    """
    start_time = (datetime.utcnow() - timedelta(hours=hours)).timestamp()
    
    with get_db() as db:
        # Camera metadata
        camera = db.query(CameraRecord).filter(
            CameraRecord.camera_id == camera_id
        ).first()
        
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        # Violations for this camera
        violations = db.query(ViolationRecord).filter(
            and_(
                ViolationRecord.camera_id == camera_id,
                ViolationRecord.timestamp >= start_time
            )
        ).all()
        
        if not violations:
            return {
                "camera": camera.to_dict(),
                "total_violations": 0,
                "by_type": {},
                "by_hour": [0] * 24,
                "avg_confidence": 0,
                "top_plates": [],
            }
        
        # By violation type
        by_type = {}
        for v in violations:
            by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
        
        # Hourly distribution
        by_hour = [0] * 24
        for v in violations:
            hour = datetime.fromtimestamp(v.timestamp).hour
            by_hour[hour] += 1
        
        # Average confidence
        avg_conf = sum(v.confidence for v in violations) / len(violations)
        
        # Top plates
        plate_counts = {}
        for v in violations:
            if v.plate_number:
                plate_counts[v.plate_number] = plate_counts.get(v.plate_number, 0) + 1
        
        top_plates = [
            {"plate": plate, "count": count}
            for plate, count in sorted(plate_counts.items(), key=lambda x: -x[1])[:10]
        ]
        
        return {
            "camera": camera.to_dict(),
            "total_violations": len(violations),
            "by_type": by_type,
            "by_hour": by_hour,
            "avg_confidence": round(avg_conf, 3),
            "top_plates": top_plates,
        }


@router.get("/realtime")
def get_realtime_metrics():
    """
    Real-time dashboard metrics for live monitoring.
    
    Returns:
        {
            "last_5_minutes": {...},
            "last_hour": {...},
            "active_cameras": 8,
            "recent_violations": [...]
        }
    """
    now = datetime.utcnow()
    five_min_ago = (now - timedelta(minutes=5)).timestamp()
    one_hour_ago = (now - timedelta(hours=1)).timestamp()
    
    with get_db() as db:
        # Last 5 minutes
        last_5min = db.query(ViolationRecord).filter(
            ViolationRecord.timestamp >= five_min_ago
        ).all()
        
        # Last hour
        last_hour = db.query(ViolationRecord).filter(
            ViolationRecord.timestamp >= one_hour_ago
        ).all()
        
        # Active cameras (with violations in last hour)
        active_cameras = db.query(ViolationRecord.camera_id).filter(
            ViolationRecord.timestamp >= one_hour_ago
        ).distinct().count()
        
        # Recent violations (last 10)
        recent = db.query(ViolationRecord).order_by(
            ViolationRecord.timestamp.desc()
        ).limit(10).all()
        
        return {
            "last_5_minutes": {
                "count": len(last_5min),
                "critical": sum(1 for v in last_5min if v.severity >= 4),
            },
            "last_hour": {
                "count": len(last_hour),
                "auto_approved": sum(1 for v in last_hour if v.auto_approve),
                "pending_review": sum(1 for v in last_hour if not v.reviewed),
            },
            "active_cameras": active_cameras,
            "recent_violations": [v.to_dict() for v in recent],
            "timestamp": now.isoformat(),
        }


@router.get("/summary")
def get_summary(days: int = Query(7, le=90)):
    """
    Executive summary report.
    
    Returns comprehensive statistics for the specified period.
    """
    start_time = (datetime.utcnow() - timedelta(days=days)).timestamp()
    
    with get_db() as db:
        violations = db.query(ViolationRecord).filter(
            ViolationRecord.timestamp >= start_time
        ).all()
        
        if not violations:
            return {
                "period_days": days,
                "total_violations": 0,
                "message": "No violations in this period"
            }
        
        total = len(violations)
        by_type = {}
        by_camera = {}
        by_day = {}
        total_fines = 0
        
        for v in violations:
            # By type
            by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
            
            # By camera
            by_camera[v.camera_id] = by_camera.get(v.camera_id, 0) + 1
            
            # By day
            day = datetime.fromtimestamp(v.timestamp).strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + 1
            
            # Total fines
            if v.approved or v.auto_approve:
                total_fines += v.fine_inr
        
        # Top violations
        top_violations = sorted(by_type.items(), key=lambda x: -x[1])[:5]
        
        # Top cameras
        top_cameras = sorted(by_camera.items(), key=lambda x: -x[1])[:5]
        
        # Daily average
        daily_avg = total / max(days, 1)
        
        return {
            "period_days": days,
            "total_violations": total,
            "daily_average": round(daily_avg, 1),
            "total_fines_inr": total_fines,
            "auto_approved": sum(1 for v in violations if v.auto_approve),
            "pending_review": sum(1 for v in violations if not v.reviewed),
            "top_violations": [{"type": t, "count": c} for t, c in top_violations],
            "top_cameras": [{"camera_id": c, "count": n} for c, n in top_cameras],
            "by_severity": {
                "critical": sum(1 for v in violations if v.severity >= 4),
                "high": sum(1 for v in violations if v.severity == 3),
                "medium": sum(1 for v in violations if v.severity == 2),
                "low": sum(1 for v in violations if v.severity == 1),
            }
        }
