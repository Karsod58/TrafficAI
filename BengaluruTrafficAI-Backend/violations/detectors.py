"""
BengaluruTrafficAI — Violation Detectors: Triple Riding, Wrong-Side,
                      Stop-Line, Red-Light, Illegal Parking
Component 2b
"""

import cv2
import numpy as np
import time
import logging

from violations.base import BaseViolationDetector, ViolationEvent, ViolationType
from core.detector import Detection, VehicleType, BoundingBox

logger = logging.getLogger("violations")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Triple Riding
# ─────────────────────────────────────────────────────────────────────────────

class TripleRidingDetector(BaseViolationDetector):
    """
    Detects more than 2 persons on a single two-wheeler.

    Strategy:
      - For each motorcycle/bicycle/auto, expand the bounding box upward
        (riders sit above the bike frame).
      - Count persons whose center falls inside the expanded box.
      - Count > 2 → violation.
    """

    VIOLATION_TYPE  = ViolationType.TRIPLE_RIDING
    CONF_THRESHOLD  = 0.75
    VERTICAL_EXPAND = 0.80   # expand vehicle box upward by this fraction

    def detect(self, detections: list[Detection], frame: np.ndarray, frame_idx: int = 0,
               roi_manager=None, track_manager=None) -> list[ViolationEvent]:
        events  = []
        bikes   = [d for d in detections if d.is_two_wheeler]
        persons = [d for d in detections if d.is_person]

        for bike in bikes:
            expanded = BoundingBox(
                bike.bbox.x1,
                max(0, bike.bbox.y1 - int(bike.bbox.height * self.VERTICAL_EXPAND)),
                bike.bbox.x2,
                bike.bbox.y2
            )
            rider_count = sum(1 for p in persons if expanded.contains_center(p.bbox))
            is_triple   = rider_count > 2

            if track_manager and bike.track_id is not None:
                track_manager.push_violation(bike.track_id, "triple_riding", is_triple)
                if "triple_riding" not in track_manager.confirmed_violations(bike.track_id):
                    continue

            if is_triple:
                # Confidence scales with how many extra riders detected
                confidence = min(0.75 + (rider_count - 3) * 0.08, 0.97)
                events.append(self._make_event(
                    track_id=bike.track_id,
                    confidence=confidence,
                    frame_idx=frame_idx,
                    bbox=bike.bbox
                ))
                logger.debug(f"Triple riding: track={bike.track_id} riders={rider_count}")

        return events


# ─────────────────────────────────────────────────────────────────────────────
# 2. Wrong-Side Driving
# ─────────────────────────────────────────────────────────────────────────────

class WrongSideDetector(BaseViolationDetector):
    """
    Detects vehicles driving against the permitted traffic direction.

    Strategy:
      - Each lane ROI has a 'direction' attribute (up/down/left/right).
      - Use TrackHistory heading vector to determine actual movement direction.
      - If vehicle heading is opposite to lane direction → violation.
    """

    VIOLATION_TYPE  = ViolationType.WRONG_SIDE
    CONF_THRESHOLD  = 0.72
    MIN_SPEED_PX    = 8    # minimum pixel movement to consider direction reliable

    # Map permitted direction to expected (dx, dy) sign
    DIRECTION_VECTORS = {
        "up":    ( 0, -1),
        "down":  ( 0,  1),
        "left":  (-1,  0),
        "right": ( 1,  0),
    }

    def detect(self, detections: list[Detection], frame: np.ndarray, frame_idx: int = 0,
               roi_manager=None, track_manager=None) -> list[ViolationEvent]:
        events = []
        if not roi_manager or not track_manager:
            return events

        lane_zones = roi_manager.get_zones_by_type("lane")
        if not lane_zones:
            return events

        vehicles = [d for d in detections if d.is_vehicle]

        for vehicle in vehicles:
            if vehicle.track_id is None:
                continue

            track = track_manager.get_track(vehicle.track_id)
            if not track:
                continue

            heading = track.heading_vector
            if heading is None:
                continue   # not enough history yet

            # Check which lane zone the vehicle is in
            cx, cy = vehicle.bbox.center
            for zone in lane_zones:
                if not zone.contains_point(cx, cy):
                    continue
                if not zone.direction:
                    continue

                permitted = self.DIRECTION_VECTORS.get(zone.direction)
                if not permitted:
                    continue

                # Dot product: negative = opposing directions
                dot = heading[0] * permitted[0] + heading[1] * permitted[1]
                is_wrong = dot < -0.5    # more than 120° off

                track_manager.push_violation(vehicle.track_id, "wrong_side", is_wrong)
                if "wrong_side" not in track_manager.confirmed_violations(vehicle.track_id):
                    break

                if is_wrong:
                    confidence = min(0.72 + abs(dot) * 0.20, 0.96)
                    events.append(self._make_event(
                        track_id=vehicle.track_id,
                        confidence=confidence,
                        frame_idx=frame_idx,
                        bbox=vehicle.bbox
                    ))
                    logger.debug(f"Wrong-side: track={vehicle.track_id} dot={dot:.2f} zone={zone.name}")
                break

        return events


# ─────────────────────────────────────────────────────────────────────────────
# 3. Stop-Line Violation
# ─────────────────────────────────────────────────────────────────────────────

class StopLineDetector(BaseViolationDetector):
    """
    Detects vehicles crossing the stop line while signal is red (or before go signal).

    Strategy:
      - ROI defines the stop line (2-point line).
      - Track trajectory between prev and curr frame to check if line was crossed.
      - Only fires during RED signal state (if SignalDetector is connected)
        or unconditionally if no signal detector is available.
    """

    VIOLATION_TYPE = ViolationType.STOP_LINE
    CONF_THRESHOLD = 0.78

    def __init__(self, camera_id: str = "unknown"):
        super().__init__(camera_id)
        self._prev_centers: dict[int, tuple] = {}   # track_id → previous center

    def detect(self, detections: list[Detection], frame: np.ndarray, frame_idx: int = 0,
               roi_manager=None, track_manager=None,
               signal_is_red: bool = True) -> list[ViolationEvent]:
        events = []
        if not roi_manager:
            return events

        stop_lines = roi_manager.get_zones_by_type("stop_line")
        if not stop_lines:
            return events

        vehicles = [d for d in detections if d.is_vehicle]

        for vehicle in vehicles:
            tid = vehicle.track_id
            curr_center = vehicle.bbox.center
            prev_center = self._prev_centers.get(tid)

            if prev_center and signal_is_red:
                for line in stop_lines:
                    crossed = line.line_crossed(prev_center, curr_center)

                    if track_manager and tid is not None:
                        track_manager.push_violation(tid, "stop_line", crossed)
                        if "stop_line" not in track_manager.confirmed_violations(tid):
                            break

                    if crossed:
                        events.append(self._make_event(
                            track_id=tid,
                            confidence=0.88,
                            frame_idx=frame_idx,
                            bbox=vehicle.bbox
                        ))
                        logger.debug(f"Stop-line violation: track={tid}")
                        break

            if tid is not None:
                self._prev_centers[tid] = curr_center

        return events


# ─────────────────────────────────────────────────────────────────────────────
# 4. Red-Light Violation
# ─────────────────────────────────────────────────────────────────────────────

class RedLightDetector(BaseViolationDetector):
    """
    Detects vehicles entering the junction box while signal is red.

    Strategy:
      - ROI defines the signal box (polygon covering the junction crossing area).
      - Detect traffic light state using colour segmentation in signal crop.
      - If signal is RED and a vehicle center is inside the signal box → violation.
    """

    VIOLATION_TYPE = ViolationType.RED_LIGHT
    CONF_THRESHOLD = 0.82

    # HSV ranges for red light detection
    RED_LOWER_1 = np.array([0,   120, 120])
    RED_UPPER_1 = np.array([10,  255, 255])
    RED_LOWER_2 = np.array([170, 120, 120])
    RED_UPPER_2 = np.array([180, 255, 255])

    def detect(self, detections: list[Detection], frame: np.ndarray, frame_idx: int = 0,
               roi_manager=None, track_manager=None) -> list[ViolationEvent]:
        events = []
        if not roi_manager:
            return events

        signal_boxes = roi_manager.get_zones_by_type("signal_box")
        if not signal_boxes:
            return events

        signal_is_red = self._detect_signal_state(frame)
        if not signal_is_red:
            return events

        vehicles = [d for d in detections if d.is_vehicle]

        for zone in signal_boxes:
            for vehicle in vehicles:
                cx, cy = vehicle.bbox.center
                if not zone.contains_point(cx, cy):
                    continue

                tid = vehicle.track_id
                if track_manager and tid is not None:
                    track_manager.push_violation(tid, "red_light", True)
                    if "red_light" not in track_manager.confirmed_violations(tid):
                        continue

                events.append(self._make_event(
                    track_id=tid,
                    confidence=0.90,
                    frame_idx=frame_idx,
                    bbox=vehicle.bbox
                ))
                logger.debug(f"Red-light violation: track={tid}")

        return events

    def _detect_signal_state(self, frame: np.ndarray) -> bool:
        """
        Detect if the traffic signal is red using colour segmentation.
        Looks in the upper portion of the frame where signals typically appear.
        Returns True if red signal detected.
        """
        h, w = frame.shape[:2]
        # Top 30% of frame, right half (typical signal position)
        signal_region = frame[:int(h * 0.30), int(w * 0.50):]
        hsv = cv2.cvtColor(signal_region, cv2.COLOR_BGR2HSV)

        red_mask = cv2.inRange(hsv, self.RED_LOWER_1, self.RED_UPPER_1) | \
                   cv2.inRange(hsv, self.RED_LOWER_2, self.RED_UPPER_2)

        red_pixels = np.sum(red_mask > 0)
        total      = signal_region.shape[0] * signal_region.shape[1]
        red_ratio  = red_pixels / max(total, 1)

        # Threshold tuned for typical Indian signal brightness
        return red_ratio > 0.008


# ─────────────────────────────────────────────────────────────────────────────
# 5. Illegal Parking
# ─────────────────────────────────────────────────────────────────────────────

class IllegalParkingDetector(BaseViolationDetector):
    """
    Detects vehicles parked in no-parking zones beyond the dwell threshold.

    Strategy:
      - ROI defines no-parking polygon zones.
      - TrackManager.get_parking_candidates() returns stationary tracks.
      - If a stationary track center is inside a no-parking zone → violation.
    """

    VIOLATION_TYPE = ViolationType.ILLEGAL_PARKING
    CONF_THRESHOLD = 0.80
    DWELL_SECONDS  = 30    # seconds stationary before flagging

    def detect(self, detections: list[Detection], frame: np.ndarray, frame_idx: int = 0,
               roi_manager=None, track_manager=None) -> list[ViolationEvent]:
        events = []
        if not roi_manager or not track_manager:
            return events

        no_park_zones = roi_manager.get_zones_by_type("no_parking")
        if not no_park_zones:
            return events

        # Get vehicles that have been stationary long enough
        parking_candidates = track_manager.get_parking_candidates()

        for track in parking_candidates:
            if not track.centers:
                continue
            cx, cy = track.centers[-1]

            for zone in no_park_zones:
                if zone.contains_point(cx, cy):
                    # Confidence increases with dwell time
                    dwell = track.dwell_seconds
                    confidence = min(0.80 + (dwell - self.DWELL_SECONDS) * 0.005, 0.97)

                    track_manager.push_violation(track.track_id, "illegal_parking", True)
                    if "illegal_parking" not in track_manager.confirmed_violations(track.track_id):
                        break

                    bbox = track.bboxes[-1] if track.bboxes else None
                    events.append(self._make_event(
                        track_id=track.track_id,
                        confidence=confidence,
                        frame_idx=frame_idx,
                        bbox=bbox
                    ))
                    logger.debug(f"Illegal parking: track={track.track_id} dwell={dwell:.1f}s")
                    break

        return events
