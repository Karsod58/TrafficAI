"""
BengaluruTrafficAI — Helmet & Seatbelt Detectors
Component 2a

Helmet:   For each motorcycle/auto detection, look at the rider bounding box
          upper region. Use a secondary YOLO classification pass to detect
          helmet presence. Falls back to head-size heuristic when model unavailable.

Seatbelt: For car detections, crop the driver region and check for diagonal
          seatbelt strap visibility using edge + line detection heuristic.
"""

import cv2
import numpy as np
import logging
from ultralytics import YOLO

from violations.base import BaseViolationDetector, ViolationEvent, ViolationType
from core.detector import Detection, VehicleType, BoundingBox

logger = logging.getLogger("violations.helmet")


class HelmetDetector(BaseViolationDetector):
    """
    Detects helmet non-compliance on motorcycle/bicycle/auto riders.

    Strategy:
      1. Find all motorcycle-type vehicles in frame
      2. Find all persons whose center overlaps with that vehicle bbox
      3. Crop the upper 40% of each person bbox (head region)
      4. Run helmet classifier on the crop
      5. If no helmet detected and confidence >= threshold → violation candidate
    """

    VIOLATION_TYPE = ViolationType.NO_HELMET

    # Upper fraction of person bbox to treat as head region
    HEAD_REGION_FRACTION = 0.40
    CONF_THRESHOLD = 0.55

    # Expected head-to-body height ratio (heuristic fallback)
    HEAD_BODY_RATIO_MIN = 0.18
    HEAD_BODY_RATIO_MAX = 0.35

    def __init__(self, camera_id: str = "unknown", helmet_model_path: str = None):
        super().__init__(camera_id)
        self.model = None
        if helmet_model_path:
            try:
                self.model = YOLO(helmet_model_path)
                logger.info(f"Helmet classifier loaded: {helmet_model_path}")
            except Exception as e:
                logger.warning(f"Could not load helmet model: {e}. Using heuristic fallback.")

    def detect(self, detections: list[Detection], frame: np.ndarray, frame_idx: int = 0,
               roi_manager=None, track_manager=None) -> list[ViolationEvent]:
        events = []

        two_wheelers = [d for d in detections if d.is_two_wheeler]
        persons      = [d for d in detections if d.is_person]

        for vehicle in two_wheelers:
            riders = self._find_riders(vehicle.bbox, persons)

            for rider in riders:
                head_crop = self._crop_head(frame, rider.bbox)
                if head_crop is None:
                    continue

                no_helmet, confidence = self._classify_head(head_crop)

                # Push signal to consensus engine
                if track_manager and vehicle.track_id is not None:
                    track_manager.push_violation(vehicle.track_id, "no_helmet", no_helmet)
                    confirmed = track_manager.confirmed_violations(vehicle.track_id)
                    if "no_helmet" not in confirmed:
                        continue   # wait for consensus

                if no_helmet and confidence >= self.CONF_THRESHOLD:
                    event = self._make_event(
                        track_id=vehicle.track_id,
                        confidence=confidence,
                        frame_idx=frame_idx,
                        bbox=vehicle.bbox
                    )
                    events.append(event)
                    logger.debug(f"Helmet violation: track={vehicle.track_id} conf={confidence:.2f}")

        return events

    def _find_riders(self, vehicle_bbox: BoundingBox,
                     persons: list[Detection]) -> list[Detection]:
        """
        Return persons whose center or upper body overlaps the vehicle bbox.
        A rider typically sits above the vehicle center.
        """
        riders = []
        for person in persons:
            px, py = person.bbox.center
            # expand vehicle box upward by 60% to catch rider torso
            expanded = BoundingBox(
                vehicle_bbox.x1,
                max(0, vehicle_bbox.y1 - int(vehicle_bbox.height * 0.6)),
                vehicle_bbox.x2,
                vehicle_bbox.y2
            )
            if expanded.contains_center(person.bbox):
                riders.append(person)
        return riders

    def _crop_head(self, frame: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """Crop the upper HEAD_REGION_FRACTION of the person bounding box."""
        h, w = frame.shape[:2]
        head_h = int(bbox.height * self.HEAD_REGION_FRACTION)
        x1 = max(0, bbox.x1)
        y1 = max(0, bbox.y1)
        x2 = min(w, bbox.x2)
        y2 = min(h, bbox.y1 + head_h)
        if x2 <= x1 or y2 <= y1:
            return None
        crop = frame[y1:y2, x1:x2]
        return crop if crop.size > 0 else None

    def _classify_head(self, head_crop: np.ndarray) -> tuple[bool, float]:
        """
        Returns (no_helmet: bool, confidence: float).
        Uses YOLO classifier if loaded, otherwise heuristic.
        """
        if self.model is not None:
            return self._model_classify(head_crop)
        return self._heuristic_classify(head_crop)

    def _model_classify(self, crop: np.ndarray) -> tuple[bool, float]:
        try:
            results = self.model(crop, verbose=False)
            for r in results:
                if r.probs is not None:
                    top_class = int(r.probs.top1)
                    top_conf  = float(r.probs.top1conf)
                    # Assumes class 0 = helmet, class 1 = no_helmet
                    # Adjust indices based on your trained model
                    no_helmet = (top_class == 1)
                    return no_helmet, top_conf
        except Exception as e:
            logger.debug(f"Model classify error: {e}")
        return False, 0.0

    def _heuristic_classify(self, crop: np.ndarray) -> tuple[bool, float]:
        """
        Fallback: checks if the head region contains a helmet-like object
        using colour and shape heuristics.

        Helmets tend to be:
          - Larger oval shapes in the head region
          - Often bright/solid colours distinct from skin tones

        This is a rough heuristic — replace with a trained model for production.
        """
        if crop is None or crop.size == 0:
            return False, 0.0

        # Skin tone detection in HSV
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        skin_lower = np.array([0, 20, 70])
        skin_upper = np.array([20, 255, 255])
        skin_mask  = cv2.inRange(hsv, skin_lower, skin_upper)

        skin_ratio = np.sum(skin_mask > 0) / max(crop.size // 3, 1)

        # High skin ratio in head region = likely no helmet
        if skin_ratio > 0.45:
            confidence = min(0.55 + skin_ratio * 0.3, 0.88)
            return True, confidence

        return False, 0.0


class SeatbeltDetector(BaseViolationDetector):
    """
    Detects seatbelt non-compliance for car drivers.

    Strategy:
      Crop the driver window region (left front seat area of car bbox).
      Detect diagonal line (seatbelt strap) using Canny + Hough lines.
      If no diagonal line found in expected strap region → violation candidate.
    """

    VIOLATION_TYPE = ViolationType.NO_SEATBELT
    CONF_THRESHOLD = 0.60

    def detect(self, detections: list[Detection], frame: np.ndarray, frame_idx: int = 0,
               roi_manager=None, track_manager=None) -> list[ViolationEvent]:
        events = []
        cars = [d for d in detections if d.vehicle_type == VehicleType.CAR]

        for car in cars:
            driver_crop = self._crop_driver_region(frame, car.bbox)
            if driver_crop is None:
                continue

            no_seatbelt, confidence = self._detect_strap(driver_crop)

            if track_manager and car.track_id is not None:
                track_manager.push_violation(car.track_id, "no_seatbelt", no_seatbelt)
                if "no_seatbelt" not in track_manager.confirmed_violations(car.track_id):
                    continue

            if no_seatbelt and confidence >= self.CONF_THRESHOLD:
                events.append(self._make_event(
                    track_id=car.track_id,
                    confidence=confidence,
                    frame_idx=frame_idx,
                    bbox=car.bbox
                ))

        return events

    def _crop_driver_region(self, frame: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """
        Crop the upper-left quadrant of the vehicle (driver side, Indian roads = right side).
        For India, driver sits on RIGHT side of vehicle.
        """
        h, w = frame.shape[:2]
        x1 = bbox.x1 + int(bbox.width * 0.50)   # right half for Indian driver
        y1 = bbox.y1
        x2 = min(w, bbox.x2)
        y2 = bbox.y1 + int(bbox.height * 0.60)  # upper 60% (windscreen area)
        if x2 <= x1 or y2 <= y1:
            return None
        crop = frame[y1:y2, x1:x2]
        return crop if crop.size > 0 else None

    def _detect_strap(self, crop: np.ndarray) -> tuple[bool, float]:
        """
        Detect diagonal seatbelt strap using Hough line transform.
        Seatbelt strap appears as a diagonal line (45–75 degrees) from shoulder to hip.
        """
        gray  = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                                threshold=20, minLineLength=20, maxLineGap=8)

        if lines is None:
            # No lines at all — unclear, low confidence
            return False, 0.40

        diagonal_count = 0
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            # Seatbelt strap angle: diagonal 30–75 degrees
            if 30 <= angle <= 75:
                diagonal_count += 1

        if diagonal_count >= 2:
            # Diagonal lines found = seatbelt present
            return False, 0.0
        else:
            confidence = 0.60 + min(0.25, 0.05 * (2 - diagonal_count))
            return True, confidence
