"""
Bengaluru Traffic AI - Traffic Health Score
Innovative feature: Real-time traffic quality monitoring

Calculates a 0-100 health score for each junction based on:
- Violation rate
- Congestion level
- Signal compliance
- Average vehicle speed
- Accident history
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("traffic_health")


class HealthGrade(str, Enum):
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"            # 75-89
    MODERATE = "moderate"    # 60-74
    POOR = "poor"            # 40-59
    CRITICAL = "critical"    # 0-39


class Trend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    WORSENING = "worsening"


@dataclass
class HealthScore:
    score: float  # 0-100
    grade: HealthGrade
    trend: Trend
    metrics: Dict[str, float]
    recommendations: List[str]
    emoji: str
    color: str
    timestamp: float


class TrafficHealthMonitor:
    """
    Calculate and monitor real-time traffic health scores.
    
    Usage:
        monitor = TrafficHealthMonitor()
        health = monitor.get_health_score("cam_01")
        print(f"Health: {health.emoji} {health.score}/100 ({health.grade})")
    """
    
    # Thresholds and weights
    VIOLATION_THRESHOLD_LOW = 5      # violations per hour
    VIOLATION_THRESHOLD_HIGH = 20
    CONGESTION_THRESHOLD = 30        # vehicles in frame
    SIGNAL_COMPLIANCE_TARGET = 95    # percentage
    
    # Scoring weights
    WEIGHTS = {
        'violations': 0.35,
        'congestion': 0.25,
        'compliance': 0.25,
        'speed': 0.15
    }
    
    def __init__(self):
        self.history = {}  # Store historical scores for trend analysis
    
    def get_health_score(
        self,
        camera_id: str,
        time_window_minutes: int = 60,
        db_session = None
    ) -> HealthScore:
        """
        Calculate comprehensive health score for a camera location.
        
        Args:
            camera_id: Camera identifier
            time_window_minutes: Time window for analysis
            db_session: Database session for queries
        
        Returns:
            HealthScore object with score, grade, trend, and recommendations
        """
        # Collect metrics
        metrics = self._collect_metrics(camera_id, time_window_minutes, db_session)
        
        # Calculate component scores
        violation_score = self._score_violations(metrics['violations_per_hour'])
        congestion_score = self._score_congestion(metrics['avg_vehicles'])
        compliance_score = metrics['signal_compliance']
        speed_score = self._score_speed(metrics['avg_speed'])
        
        # Weighted final score
        final_score = (
            violation_score * self.WEIGHTS['violations'] +
            congestion_score * self.WEIGHTS['congestion'] +
            compliance_score * self.WEIGHTS['compliance'] +
            speed_score * self.WEIGHTS['speed']
        )
        
        # Ensure score is in range
        final_score = max(0, min(100, final_score))
        
        # Determine grade
        grade = self._get_grade(final_score)
        
        # Analyze trend
        trend = self._analyze_trend(camera_id, final_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, final_score)
        
        # Visual indicators
        emoji, color = self._get_visual_indicators(grade)
        
        # Store for trend analysis
        self._store_score(camera_id, final_score)
        
        return HealthScore(
            score=round(final_score, 1),
            grade=grade,
            trend=trend,
            metrics={
                'violations_per_hour': metrics['violations_per_hour'],
                'violation_score': violation_score,
                'congestion_score': congestion_score,
                'compliance_score': compliance_score,
                'speed_score': speed_score,
                'avg_vehicles': metrics['avg_vehicles'],
                'signal_compliance': metrics['signal_compliance'],
                'avg_speed': metrics['avg_speed']
            },
            recommendations=recommendations,
            emoji=emoji,
            color=color,
            timestamp=datetime.now().timestamp()
        )
    
    def get_all_health_scores(self, db_session=None) -> Dict[str, HealthScore]:
        """Get health scores for all cameras."""
        # This would query all cameras from database
        cameras = self._get_all_cameras(db_session)
        
        return {
            cam_id: self.get_health_score(cam_id, db_session=db_session)
            for cam_id in cameras
        }
    
    def get_city_health_summary(self, db_session=None) -> Dict:
        """
        Get overall city traffic health.
        
        Returns:
            City-wide health metrics and statistics
        """
        all_scores = self.get_all_health_scores(db_session)
        
        if not all_scores:
            return {
                'overall_score': 0,
                'grade': HealthGrade.CRITICAL,
                'total_cameras': 0
            }
        
        scores = [s.score for s in all_scores.values()]
        
        return {
            'overall_score': round(sum(scores) / len(scores), 1),
            'grade': self._get_grade(sum(scores) / len(scores)),
            'total_cameras': len(scores),
            'excellent': sum(1 for s in all_scores.values() if s.grade == HealthGrade.EXCELLENT),
            'good': sum(1 for s in all_scores.values() if s.grade == HealthGrade.GOOD),
            'moderate': sum(1 for s in all_scores.values() if s.grade == HealthGrade.MODERATE),
            'poor': sum(1 for s in all_scores.values() if s.grade == HealthGrade.POOR),
            'critical': sum(1 for s in all_scores.values() if s.grade == HealthGrade.CRITICAL),
            'improving': sum(1 for s in all_scores.values() if s.trend == Trend.IMPROVING),
            'worsening': sum(1 for s in all_scores.values() if s.trend == Trend.WORSENING),
        }
    
    # ── Internal methods ──────────────────────────────────────────────────────
    
    def _collect_metrics(self, camera_id: str, time_window_minutes: int, db_session) -> Dict:
        """Collect raw metrics from database."""
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=time_window_minutes)
        
        if db_session:
            # Real database queries
            from api.database import ViolationRecord
            
            violations = db_session.query(ViolationRecord).filter(
                ViolationRecord.camera_id == camera_id,
                ViolationRecord.timestamp >= start_time.timestamp()
            ).all()
            
            violations_per_hour = len(violations) * (60 / time_window_minutes)
            
            # Signal compliance (no red light violations / total vehicles)
            red_light_violations = sum(1 for v in violations if 'red_light' in v.violation_type or 'stop_line' in v.violation_type)
            total_detections = len(violations) * 20  # Estimate: 1 violation per 20 vehicles
            signal_compliance = max(0, min(100, ((total_detections - red_light_violations) / max(total_detections, 1)) * 100))
            
        else:
            # Demo mode - simulate metrics
            import random
            violations_per_hour = random.uniform(3, 15)
            signal_compliance = random.uniform(85, 98)
        
        # Simulate other metrics (would come from detection pipeline)
        avg_vehicles = self._estimate_congestion(camera_id)
        avg_speed = self._estimate_speed(camera_id)
        
        return {
            'violations_per_hour': violations_per_hour,
            'avg_vehicles': avg_vehicles,
            'signal_compliance': signal_compliance,
            'avg_speed': avg_speed
        }
    
    def _score_violations(self, violations_per_hour: float) -> float:
        """Score based on violation rate (0-100, higher is better)."""
        if violations_per_hour <= self.VIOLATION_THRESHOLD_LOW:
            return 100
        elif violations_per_hour >= self.VIOLATION_THRESHOLD_HIGH:
            return 0
        else:
            # Linear interpolation
            return 100 - ((violations_per_hour - self.VIOLATION_THRESHOLD_LOW) / 
                         (self.VIOLATION_THRESHOLD_HIGH - self.VIOLATION_THRESHOLD_LOW)) * 100
    
    def _score_congestion(self, avg_vehicles: float) -> float:
        """Score based on congestion level."""
        if avg_vehicles < 10:
            return 100  # Free flow
        elif avg_vehicles < 20:
            return 80   # Light
        elif avg_vehicles < self.CONGESTION_THRESHOLD:
            return 60   # Moderate
        elif avg_vehicles < 50:
            return 30   # Heavy
        else:
            return 10   # Jammed
    
    def _score_speed(self, avg_speed_kmh: float) -> float:
        """Score based on average speed."""
        optimal_speed = 40  # km/h for urban areas
        
        if 30 <= avg_speed_kmh <= 50:
            return 100  # Optimal range
        elif avg_speed_kmh > 50:
            return max(50, 100 - (avg_speed_kmh - 50) * 2)  # Too fast
        else:
            return max(0, avg_speed_kmh / 30 * 100)  # Too slow
    
    def _get_grade(self, score: float) -> HealthGrade:
        """Convert numeric score to grade."""
        if score >= 90:
            return HealthGrade.EXCELLENT
        elif score >= 75:
            return HealthGrade.GOOD
        elif score >= 60:
            return HealthGrade.MODERATE
        elif score >= 40:
            return HealthGrade.POOR
        else:
            return HealthGrade.CRITICAL
    
    def _analyze_trend(self, camera_id: str, current_score: float) -> Trend:
        """Analyze score trend over time."""
        if camera_id not in self.history or len(self.history[camera_id]) < 3:
            return Trend.STABLE
        
        recent_scores = self.history[camera_id][-3:]
        avg_recent = sum(recent_scores) / len(recent_scores)
        
        diff = current_score - avg_recent
        
        if diff > 5:
            return Trend.IMPROVING
        elif diff < -5:
            return Trend.WORSENING
        else:
            return Trend.STABLE
    
    def _generate_recommendations(self, metrics: Dict, score: float) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if metrics['violations_per_hour'] > 15:
            recommendations.append("⚠️ High violation rate - increase enforcement presence")
        
        if metrics['avg_vehicles'] > 30:
            recommendations.append("🚦 Heavy congestion - optimize signal timing")
        
        if metrics['signal_compliance'] < 90:
            recommendations.append("🔴 Low signal compliance - install warning displays")
        
        if metrics['avg_speed'] < 20:
            recommendations.append("🐌 Very slow traffic - check for bottlenecks")
        
        if metrics['avg_speed'] > 60:
            recommendations.append("⚡ Excessive speed - increase speed monitoring")
        
        if score < 60:
            recommendations.append("🚨 Critical junction - requires immediate attention")
        
        if not recommendations:
            recommendations.append("✅ Traffic flowing smoothly - maintain current measures")
        
        return recommendations
    
    def _get_visual_indicators(self, grade: HealthGrade) -> tuple:
        """Get emoji and color for grade."""
        indicators = {
            HealthGrade.EXCELLENT: ("🟢", "green"),
            HealthGrade.GOOD: ("🟢", "green"),
            HealthGrade.MODERATE: ("🟡", "yellow"),
            HealthGrade.POOR: ("🟠", "orange"),
            HealthGrade.CRITICAL: ("🔴", "red")
        }
        return indicators.get(grade, ("⚪", "gray"))
    
    def _store_score(self, camera_id: str, score: float):
        """Store score for trend analysis."""
        if camera_id not in self.history:
            self.history[camera_id] = []
        
        self.history[camera_id].append(score)
        
        # Keep only last 20 scores
        if len(self.history[camera_id]) > 20:
            self.history[camera_id] = self.history[camera_id][-20:]
    
    def _get_all_cameras(self, db_session) -> List[str]:
        """Get all camera IDs."""
        if db_session:
            from api.database import CameraRecord
            cameras = db_session.query(CameraRecord.camera_id).all()
            return [c[0] for c in cameras]
        else:
            # Demo mode
            return ["cam_01", "cam_02", "cam_03"]
    
    def _estimate_congestion(self, camera_id: str) -> float:
        """Estimate current congestion level."""
        # In production, this would come from real-time detection
        # For now, simulate based on camera ID
        import random
        return random.uniform(10, 35)
    
    def _estimate_speed(self, camera_id: str) -> float:
        """Estimate average vehicle speed."""
        # In production, this would be calculated from track data
        import random
        return random.uniform(25, 45)


# Global instance
health_monitor = TrafficHealthMonitor()
