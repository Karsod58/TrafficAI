"""
BengaluruTrafficAI — Violation Pipeline
Component 2c: Orchestrates all violation detectors on each frame result.

Usage:
    pipeline = ViolationPipeline(camera_id="cam_07", roi_manager=roi)
    for frame_result in detector.process_video("silk_board.mp4"):
        track_manager.update(frame_result.detections)
        events = pipeline.run(frame_result, track_manager)
        for ev in events:
            print(ev.to_dict())
"""

import cv2
import numpy as np
import logging
from typing import Optional

from violations.base import ViolationEvent, ViolationType
from violations.helmet_seatbelt import HelmetDetector, SeatbeltDetector
from violations.detectors import (
    TripleRidingDetector, WrongSideDetector,
    StopLineDetector, RedLightDetector, IllegalParkingDetector
)
from core.detector import FrameResult
from core.roi_manager import ROIManager
from core.track_manager import TrackManager

logger = logging.getLogger("violation_pipeline")

# Colour overlays for evidence annotation (BGR)
VIOLATION_COLORS = {
    ViolationType.NO_HELMET:       (0,   80,  255),
    ViolationType.NO_SEATBELT:     (0,   140, 255),
    ViolationType.TRIPLE_RIDING:   (255, 50,  50),
    ViolationType.WRONG_SIDE:      (255, 0,   200),
    ViolationType.STOP_LINE:       (0,   200, 255),
    ViolationType.RED_LIGHT:       (0,   0,   255),
    ViolationType.ILLEGAL_PARKING: (255, 165, 0),
}


class ViolationPipeline:
    """
    Runs all seven violation detectors sequentially on each frame.
    Returns confirmed ViolationEvents ready for evidence generation.
    """

    def __init__(
        self,
        camera_id:          str             = "unknown",
        roi_manager:        Optional[ROIManager] = None,
        helmet_model_path:  Optional[str]   = None,
    ):
        self.camera_id   = camera_id
        self.roi_manager = roi_manager

        # Instantiate all detectors
        self.detectors = [
            HelmetDetector(camera_id, helmet_model_path),
            SeatbeltDetector(camera_id),
            TripleRidingDetector(camera_id),
            WrongSideDetector(camera_id),
            StopLineDetector(camera_id),
            RedLightDetector(camera_id),
            IllegalParkingDetector(camera_id),
        ]

        logger.info(f"ViolationPipeline ready | camera={camera_id} | {len(self.detectors)} detectors")

    def run(
        self,
        frame_result: FrameResult,
        track_manager: TrackManager,
    ) -> list[ViolationEvent]:
        """
        Run all detectors on a single FrameResult.
        Returns de-duplicated list of confirmed ViolationEvents.
        """
        all_events: list[ViolationEvent] = []

        for detector in self.detectors:
            try:
                if isinstance(detector, StopLineDetector):
                    # StopLine needs signal state; pass True as default (conservative)
                    events = detector.detect(
                        frame_result.detections,
                        frame_result.annotated_frame,
                        frame_idx=frame_result.frame_idx,
                        roi_manager=self.roi_manager,
                        track_manager=track_manager,
                        signal_is_red=True
                    )
                else:
                    events = detector.detect(
                        frame_result.detections,
                        frame_result.annotated_frame,
                        frame_idx=frame_result.frame_idx,
                        roi_manager=self.roi_manager,
                        track_manager=track_manager,
                    )
                all_events.extend(events)

            except Exception as e:
                logger.error(f"Detector {type(detector).__name__} error: {e}", exc_info=True)

        # De-duplicate: one event per (track_id, violation_type) per frame
        seen = set()
        unique_events = []
        for ev in all_events:
            key = (ev.track_id, ev.violation_type)
            if key not in seen:
                seen.add(key)
                unique_events.append(ev)

        if unique_events:
            logger.info(
                f"Frame {frame_result.frame_idx}: "
                f"{len(unique_events)} violation(s) → "
                f"{[e.violation_type.value for e in unique_events]}"
            )

        return unique_events

    def annotate_violations(
        self,
        frame: np.ndarray,
        events: list[ViolationEvent],
    ) -> np.ndarray:
        """
        Draw violation highlights on evidence frame.
        Returns annotated copy of the frame.
        """
        out = frame.copy()
        for ev in events:
            if not ev.bbox:
                continue

            x1, y1, x2, y2 = ev.bbox
            color = VIOLATION_COLORS.get(ev.violation_type, (255, 255, 255))

            # Thick violation box
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)

            # Red diagonal corners for emphasis
            corner = 18
            for (cx, cy, dx, dy) in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(out, (cx, cy), (cx + dx*corner, cy), color, 3)
                cv2.line(out, (cx, cy), (cx, cy + dy*corner), color, 3)

            # Label banner
            label = ev.violation_type.value.upper().replace("_", " ")
            conf_txt = f"CONF {ev.confidence:.2f}"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            ly = max(y1 - 6, lh + 8)
            cv2.rectangle(out, (x1, ly - lh - 6), (x1 + lw + 70, ly), color, -1)
            cv2.putText(out, f"{label}  {conf_txt}",
                        (x1 + 4, ly - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # Severity badge bottom-right of box
            sev = f"SEV {ev.severity}/5"
            cv2.putText(out, sev, (x2 - 70, y2 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

        return out
