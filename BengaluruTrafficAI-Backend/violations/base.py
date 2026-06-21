"""
BengaluruTrafficAI — Violation Base
Component 2: Shared types for all violation detectors.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import numpy as np


class ViolationType(str, Enum):
    NO_HELMET       = "no_helmet"
    NO_SEATBELT     = "no_seatbelt"
    TRIPLE_RIDING   = "triple_riding"
    WRONG_SIDE      = "wrong_side"
    STOP_LINE       = "stop_line_violation"
    RED_LIGHT       = "red_light_violation"
    ILLEGAL_PARKING = "illegal_parking"


VIOLATION_SEVERITY = {
    ViolationType.RED_LIGHT:       5,
    ViolationType.WRONG_SIDE:      5,
    ViolationType.NO_HELMET:       4,
    ViolationType.TRIPLE_RIDING:   4,
    ViolationType.STOP_LINE:       3,
    ViolationType.NO_SEATBELT:     3,
    ViolationType.ILLEGAL_PARKING: 2,
}

VIOLATION_FINE_INR = {
    ViolationType.NO_HELMET:       1000,
    ViolationType.NO_SEATBELT:     1000,
    ViolationType.TRIPLE_RIDING:   1000,
    ViolationType.WRONG_SIDE:      5000,
    ViolationType.STOP_LINE:       1000,
    ViolationType.RED_LIGHT:       5000,
    ViolationType.ILLEGAL_PARKING: 500,
}


@dataclass
class ViolationEvent:
    """A confirmed (consensus-passed) traffic violation."""
    event_id:       str             = field(default_factory=lambda: str(uuid.uuid4())[:8])
    violation_type: ViolationType   = ViolationType.NO_HELMET
    track_id:       Optional[int]   = None
    camera_id:      str             = "unknown"
    confidence:     float           = 0.0
    frame_idx:      int             = 0
    timestamp:      float           = field(default_factory=time.time)
    bbox:           Optional[tuple] = None   # (x1,y1,x2,y2) of offending vehicle
    plate_number:   Optional[str]   = None
    evidence_frame: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def severity(self) -> int:
        return VIOLATION_SEVERITY.get(self.violation_type, 1)

    @property
    def fine_inr(self) -> int:
        return VIOLATION_FINE_INR.get(self.violation_type, 500)

    @property
    def auto_approve(self) -> bool:
        """High-confidence violations skip human review queue."""
        return self.confidence >= 0.92

    def to_dict(self) -> dict:
        return {
            "event_id":       self.event_id,
            "violation_type": self.violation_type.value,
            "track_id":       self.track_id,
            "camera_id":      self.camera_id,
            "confidence":     round(self.confidence, 3),
            "frame_idx":      self.frame_idx,
            "timestamp":      self.timestamp,
            "bbox":           self.bbox,
            "plate_number":   self.plate_number,
            "severity":       self.severity,
            "fine_inr":       self.fine_inr,
            "auto_approve":   self.auto_approve,
        }


class BaseViolationDetector:
    """
    All violation detectors inherit from this.
    Each detector receives the full list of detections for a frame
    and returns zero or more ViolationEvent candidates.
    Consensus is enforced by TrackManager before events are finalised.
    """
    VIOLATION_TYPE: ViolationType = None

    def __init__(self, camera_id: str = "unknown"):
        self.camera_id = camera_id

    def detect(self, detections, frame, frame_idx: int = 0, roi_manager=None, track_manager=None) -> list[ViolationEvent]:
        raise NotImplementedError

    def _make_event(self, track_id, confidence, frame_idx, bbox=None) -> ViolationEvent:
        return ViolationEvent(
            violation_type=self.VIOLATION_TYPE,
            track_id=track_id,
            camera_id=self.camera_id,
            confidence=confidence,
            frame_idx=frame_idx,
            bbox=bbox.as_tuple if bbox else None,
        )
