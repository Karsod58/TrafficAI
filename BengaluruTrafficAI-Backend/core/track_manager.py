"""
BengaluruTrafficAI — Track Manager
Component 1c: Vehicle trajectory tracking and multi-frame consensus engine.

Key functions:
  - Maintains per-vehicle trajectory history across frames
  - Implements multi-frame consensus (3/5 frames must agree on violation)
  - Computes heading vector for wrong-side detection
  - Tracks dwell time for illegal parking detection
"""

import time
import numpy as np
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Optional

from core.detector import Detection, BoundingBox


CONSENSUS_WINDOW  = 5   # frames to consider
CONSENSUS_MIN     = 3   # minimum agreements to confirm violation
MAX_TRACK_HISTORY = 60  # frames to retain per track (~2 seconds at 30fps)
PARKING_DWELL_SEC = 30  # seconds stationary before flagging illegal parking


@dataclass
class TrackHistory:
    track_id:   int
    centers:    deque = field(default_factory=lambda: deque(maxlen=MAX_TRACK_HISTORY))
    bboxes:     deque = field(default_factory=lambda: deque(maxlen=MAX_TRACK_HISTORY))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=MAX_TRACK_HISTORY))
    first_seen: float = field(default_factory=time.time)
    last_seen:  float = field(default_factory=time.time)

    # violation candidate buffers: {violation_type: deque of bool}
    violation_buffer: dict = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=CONSENSUS_WINDOW)))

    def update(self, detection: Detection):
        self.centers.append(detection.bbox.center)
        self.bboxes.append(detection.bbox)
        self.timestamps.append(time.time())
        self.last_seen = time.time()

    @property
    def dwell_seconds(self) -> float:
        return self.last_seen - self.first_seen

    @property
    def heading_vector(self) -> Optional[tuple[float, float]]:
        """
        Compute movement direction from recent trajectory.
        Returns normalised (dx, dy) or None if track is too short.
        """
        if len(self.centers) < 6:
            return None
        recent = list(self.centers)[-6:]
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]
        magnitude = (dx**2 + dy**2) ** 0.5
        if magnitude < 5:   # vehicle essentially stationary
            return None
        return (dx / magnitude, dy / magnitude)

    @property
    def is_stationary(self) -> bool:
        """True if vehicle hasn't moved significantly in last N frames."""
        if len(self.centers) < 10:
            return False
        recent = list(self.centers)[-10:]
        xs = [c[0] for c in recent]
        ys = [c[1] for c in recent]
        spread = max(max(xs)-min(xs), max(ys)-min(ys))
        return spread < 20   # pixels

    def push_violation_signal(self, violation_type: str, detected: bool):
        """Add one frame's detection result to the consensus buffer."""
        self.violation_buffer[violation_type].append(detected)

    def consensus_confirmed(self, violation_type: str) -> bool:
        """
        Returns True if ≥ CONSENSUS_MIN of the last CONSENSUS_WINDOW
        frames flagged this violation type for this track.
        """
        buf = self.violation_buffer[violation_type]
        if len(buf) < CONSENSUS_WINDOW:
            return False
        return sum(buf) >= CONSENSUS_MIN


class TrackManager:
    """
    Maintains trajectory history for all active vehicle tracks.

    Usage:
        tm = TrackManager()
        for frame_result in detector.process_video(...):
            tm.update(frame_result.detections)
            track = tm.get_track(some_track_id)
            if track.consensus_confirmed("no_helmet"):
                # fire violation event
    """

    def __init__(self, max_track_age_sec: float = 5.0):
        self.tracks: dict[int, TrackHistory] = {}
        self.max_track_age = max_track_age_sec
        self._next_anon_id = -1    # for detections without a track ID

    def update(self, detections: list[Detection]):
        """Ingest detections from one frame, update or create tracks."""
        now = time.time()

        for det in detections:
            tid = det.track_id
            if tid is None:
                # Assign temporary negative IDs for untracked detections
                tid = self._next_anon_id
                self._next_anon_id -= 1

            if tid not in self.tracks:
                self.tracks[tid] = TrackHistory(track_id=tid)
            self.tracks[tid].update(det)

        # Prune stale tracks
        stale = [tid for tid, t in self.tracks.items() if now - t.last_seen > self.max_track_age]
        for tid in stale:
            del self.tracks[tid]

    def get_track(self, track_id: int) -> Optional[TrackHistory]:
        return self.tracks.get(track_id)

    def get_parking_candidates(self) -> list[TrackHistory]:
        """Return tracks that have been stationary longer than parking threshold."""
        return [
            t for t in self.tracks.values()
            if t.is_stationary and t.dwell_seconds >= PARKING_DWELL_SEC
        ]

    def push_violation(self, track_id: int, violation_type: str, detected: bool):
        """Record per-frame violation signal for consensus tracking."""
        track = self.tracks.get(track_id)
        if track:
            track.push_violation_signal(violation_type, detected)

    def confirmed_violations(self, track_id: int) -> list[str]:
        """Return list of violation types confirmed by consensus for this track."""
        track = self.tracks.get(track_id)
        if not track:
            return []
        return [vtype for vtype in track.violation_buffer if track.consensus_confirmed(vtype)]

    @property
    def active_count(self) -> int:
        return len(self.tracks)

    def summary(self) -> dict:
        return {
            "active_tracks": self.active_count,
            "parking_candidates": len(self.get_parking_candidates()),
        }
