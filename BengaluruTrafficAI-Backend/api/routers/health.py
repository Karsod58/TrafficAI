"""
Bengaluru Traffic AI - Traffic Health Score API
Innovative feature endpoints for real-time traffic quality monitoring
"""

import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ..database import get_db
from features.traffic_health import health_monitor, HealthScore

logger = logging.getLogger("router.health")
router = APIRouter(prefix="/health", tags=["traffic-health"])


@router.get("/score/{camera_id}")
def get_camera_health_score(
    camera_id: str,
    time_window: int = Query(60, ge=15, le=180, description="Time window in minutes")
):
    """
    Get real-time traffic health score for a specific camera/junction.
    
    Returns comprehensive health metrics including:
    - Overall score (0-100)
    - Grade (excellent/good/moderate/poor/critical)
    - Trend (improving/stable/worsening)
    - Component metrics
    - Actionable recommendations
    
    Example Response:
    {
        "score": 85.3,
        "grade": "good",
        "trend": "improving",
        "emoji": "🟢",
        "color": "green",
        "metrics": {
            "violations_per_hour": 8.5,
            "avg_vehicles": 18.2,
            "signal_compliance": 94.5,
            "avg_speed": 38.2
        },
        "recommendations": [
            "✅ Traffic flowing smoothly - maintain current measures"
        ]
    }
    """
    try:
        with get_db() as db:
            health = health_monitor.get_health_score(
                camera_id=camera_id,
                time_window_minutes=time_window,
                db_session=db
            )
        
        return {
            "camera_id": camera_id,
            "score": health.score,
            "grade": health.grade.value,
            "trend": health.trend.value,
            "emoji": health.emoji,
            "color": health.color,
            "metrics": health.metrics,
            "recommendations": health.recommendations,
            "timestamp": health.timestamp
        }
    
    except Exception as e:
        logger.error(f"Error calculating health score for {camera_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scores")
def get_all_health_scores(
    time_window: int = Query(60, ge=15, le=180)
):
    """
    Get traffic health scores for all cameras/junctions.
    
    Returns a map of camera_id to health score.
    
    Example Response:
    {
        "cam_01": {
            "score": 85.3,
            "grade": "good",
            "trend": "improving",
            ...
        },
        "cam_02": {
            "score": 72.1,
            "grade": "moderate",
            "trend": "stable",
            ...
        }
    }
    """
    try:
        with get_db() as db:
            all_scores = health_monitor.get_all_health_scores(db_session=db)
        
        return {
            camera_id: {
                "score": health.score,
                "grade": health.grade.value,
                "trend": health.trend.value,
                "emoji": health.emoji,
                "color": health.color,
                "metrics": health.metrics,
                "recommendations": health.recommendations,
                "timestamp": health.timestamp
            }
            for camera_id, health in all_scores.items()
        }
    
    except Exception as e:
        logger.error(f"Error calculating all health scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/city-summary")
def get_city_health_summary():
    """
    Get overall city-wide traffic health summary.
    
    Returns aggregated metrics across all junctions:
    - Overall city score
    - Distribution by grade
    - Trend analysis
    
    Example Response:
    {
        "overall_score": 78.5,
        "grade": "good",
        "total_cameras": 12,
        "excellent": 2,
        "good": 6,
        "moderate": 3,
        "poor": 1,
        "critical": 0,
        "improving": 7,
        "worsening": 2
    }
    """
    try:
        with get_db() as db:
            summary = health_monitor.get_city_health_summary(db_session=db)
        
        return summary
    
    except Exception as e:
        logger.error(f"Error calculating city health summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
def get_health_leaderboard(
    order: str = Query("best", regex="^(best|worst)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get ranked list of junctions by health score.
    
    Args:
        order: "best" for highest scores first, "worst" for lowest
        limit: Number of results to return
    
    Returns list of junctions sorted by score.
    
    Example Response:
    {
        "leaderboard": [
            {
                "rank": 1,
                "camera_id": "cam_silk_board",
                "name": "Silk Board Junction",
                "score": 92.5,
                "grade": "excellent",
                "trend": "improving"
            },
            ...
        ],
        "order": "best",
        "timestamp": 1718635845.123
    }
    """
    try:
        with get_db() as db:
            from api.database import CameraRecord
            
            all_scores = health_monitor.get_all_health_scores(db_session=db)
            
            # Get camera names
            cameras = {c.camera_id: c.name for c in db.query(CameraRecord).all()}
            
            # Sort by score
            sorted_cameras = sorted(
                all_scores.items(),
                key=lambda x: x[1].score,
                reverse=(order == "best")
            )[:limit]
            
            leaderboard = [
                {
                    "rank": idx + 1,
                    "camera_id": camera_id,
                    "name": cameras.get(camera_id, camera_id),
                    "score": health.score,
                    "grade": health.grade.value,
                    "trend": health.trend.value,
                    "emoji": health.emoji
                }
                for idx, (camera_id, health) in enumerate(sorted_cameras)
            ]
            
            return {
                "leaderboard": leaderboard,
                "order": order,
                "timestamp": datetime.now().timestamp()
            }
    
    except Exception as e:
        logger.error(f"Error generating leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
def get_health_alerts(
    severity: Optional[str] = Query(None, regex="^(critical|poor|moderate)$")
):
    """
    Get list of junctions requiring attention based on health scores.
    
    Args:
        severity: Filter by severity level (critical/poor/moderate)
    
    Returns junctions with low health scores that need intervention.
    
    Example Response:
    {
        "alerts": [
            {
                "camera_id": "cam_03",
                "name": "Koramangala Junction",
                "score": 45.2,
                "grade": "poor",
                "trend": "worsening",
                "top_issue": "High violation rate",
                "recommendations": [...]
            }
        ],
        "total_alerts": 3
    }
    """
    try:
        with get_db() as db:
            from api.database import CameraRecord
            
            all_scores = health_monitor.get_all_health_scores(db_session=db)
            cameras = {c.camera_id: c.name for c in db.query(CameraRecord).all()}
            
            # Filter by severity
            alerts = []
            for camera_id, health in all_scores.items():
                if severity:
                    if health.grade.value != severity:
                        continue
                
                # Only include poor, critical, or worsening moderate
                if health.score < 75 or (health.score < 85 and health.trend.value == "worsening"):
                    # Identify top issue
                    metrics = health.metrics
                    top_issue = "Unknown"
                    if metrics['violations_per_hour'] > 15:
                        top_issue = "High violation rate"
                    elif metrics['avg_vehicles'] > 30:
                        top_issue = "Heavy congestion"
                    elif metrics['signal_compliance'] < 90:
                        top_issue = "Low signal compliance"
                    
                    alerts.append({
                        "camera_id": camera_id,
                        "name": cameras.get(camera_id, camera_id),
                        "score": health.score,
                        "grade": health.grade.value,
                        "trend": health.trend.value,
                        "emoji": health.emoji,
                        "top_issue": top_issue,
                        "recommendations": health.recommendations[:3]  # Top 3
                    })
            
            # Sort by score (worst first)
            alerts.sort(key=lambda x: x['score'])
            
            return {
                "alerts": alerts,
                "total_alerts": len(alerts),
                "timestamp": datetime.now().timestamp()
            }
    
    except Exception as e:
        logger.error(f"Error generating health alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from datetime import datetime
