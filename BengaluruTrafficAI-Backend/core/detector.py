"""
BengaluruTrafficAI — Core Detection Pipeline
Component 1: Vehicle & Road User Detection using YOLO11s

Detects and classifies:
  - Vehicles: car, truck, bus, motorcycle, bicycle, auto-rickshaw
  - Road users: person (rider, pedestrian, driver)
  - Traffic signals: traffic light state
  - Structural: stop line ROI, lane boundaries

GTX 1650 target: YOLO11s @ 640px → ~30ms inference per frame (better than YOLOv8s)
"""

import cv2
import torch
import numpy as np
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("detector")


# ─── COCO class IDs relevant to traffic ───────────────────────────────────────
VEHICLE_CLASSES = {
    2:  "car",
    3:  "motorcycle",
    5:  "bus",
    7:  "truck",
    1:  "bicycle",
}
PERSON_CLASS = 0
TRAFFIC_LIGHT_CLASS = 9

# Congestion thresholds (vehicles visible per frame)
CONGESTION_THRESHOLDS = {
    "free":     (0,  5),
    "slow":     (5,  15),
    "moderate": (15, 30),
    "jammed":   (30, float("inf")),
}


# ─── Data classes ─────────────────────────────────────────────────────────────

class VehicleType(str, Enum):
    CAR         = "car"
    MOTORCYCLE  = "motorcycle"
    BUS         = "bus"
    TRUCK       = "truck"
    BICYCLE     = "bicycle"
    AUTO        = "auto-rickshaw"   # detected as motorcycle class, refined by size
    UNKNOWN     = "unknown"


class CongestionLevel(str, Enum):
    FREE     = "free"
    SLOW     = "slow"
    MODERATE = "moderate"
    JAMMED   = "jammed"


@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self):  return self.x2 - self.x1
    @property
    def height(self): return self.y2 - self.y1
    @property
    def area(self):   return self.width * self.height
    @property
    def center(self): return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)
    @property
    def as_tuple(self): return (self.x1, self.y1, self.x2, self.y2)

    def iou(self, other: "BoundingBox") -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        return inter / (self.area + other.area - inter)

    def contains_center(self, other: "BoundingBox") -> bool:
        cx, cy = other.center
        return self.x1 <= cx <= self.x2 and self.y1 <= cy <= self.y2


@dataclass
class Detection:
    track_id:     Optional[int]
    class_id:     int
    class_name:   str
    vehicle_type: VehicleType
    bbox:         BoundingBox
    confidence:   float
    frame_idx:    int
    timestamp:    float = field(default_factory=time.time)

    # populated by violation modules downstream
    violations:   list = field(default_factory=list)

    @property
    def is_vehicle(self):    return self.class_id in VEHICLE_CLASSES
    @property
    def is_person(self):     return self.class_id == PERSON_CLASS
    @property
    def is_two_wheeler(self):
        return self.vehicle_type in (VehicleType.MOTORCYCLE, VehicleType.BICYCLE, VehicleType.AUTO)


@dataclass
class FrameResult:
    frame_idx:        int
    timestamp:        float
    detections:       list[Detection]
    congestion_level: CongestionLevel
    vehicle_count:    int
    person_count:     int
    inference_ms:     float
    annotated_frame:  Optional[np.ndarray] = None

    @property
    def has_vehicles(self): return self.vehicle_count > 0


# ─── Detector ─────────────────────────────────────────────────────────────────

class TrafficDetector:
    """
    YOLO11s-based detector for Bengaluru traffic surveillance.
    
    YOLO11 is the latest version with improved accuracy and speed over YOLOv8.

    Usage:
        detector = TrafficDetector()
        for result in detector.process_video("silk_board.mp4"):
            print(result.congestion_level, result.vehicle_count)
    """

    MODEL_NAME = "yolo11s.pt"   # YOLO11s - latest version, better accuracy than YOLOv8s
    INPUT_SIZE = 640
    CONF_THRESHOLD = 0.40       # lower = more sensitive; raise if too many false positives
    IOU_THRESHOLD  = 0.45       # NMS overlap threshold

    # Visual config
    COLORS = {
        "car":          (86, 180, 233),
        "motorcycle":   (230, 159, 0),
        "bus":          (0, 158, 115),
        "truck":        (213, 94, 0),
        "bicycle":      (204, 121, 167),
        "auto-rickshaw":(0, 114, 178),
        "person":       (240, 228, 66),
        "unknown":      (150, 150, 150),
    }
    CONGESTION_COLORS = {
        CongestionLevel.FREE:     (0, 200, 80),
        CongestionLevel.SLOW:     (255, 200, 0),
        CongestionLevel.MODERATE: (255, 120, 0),
        CongestionLevel.JAMMED:   (220, 30, 30),
    }

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        model_path  = model_path or self.MODEL_NAME

        logger.info(f"Loading {model_path} on {self.device}")
        self.model = YOLO(model_path)
        self.model.to(self.device)

        logger.info(f"Detector ready | device={self.device} | conf={self.CONF_THRESHOLD}")

    # ── Frame-level inference ──────────────────────────────────────────────────

    def detect_frame(self, frame: np.ndarray, frame_idx: int = 0) -> FrameResult:
        """Run detection on a single BGR frame. Returns a FrameResult."""
        t0 = time.perf_counter()

        results = self.model.track(
            frame,
            persist=True,                  # maintain track IDs across frames
            imgsz=self.INPUT_SIZE,
            conf=self.CONF_THRESHOLD,
            iou=self.IOU_THRESHOLD,
            device=self.device,
            verbose=False,
            classes=list(VEHICLE_CLASSES.keys()) + [PERSON_CLASS, TRAFFIC_LIGHT_CLASS]
        )

        inference_ms = (time.perf_counter() - t0) * 1000
        detections   = self._parse_results(results, frame_idx)

        vehicle_count    = sum(1 for d in detections if d.is_vehicle)
        person_count     = sum(1 for d in detections if d.is_person)
        congestion_level = self._classify_congestion(vehicle_count)

        annotated = self._annotate(frame.copy(), detections, congestion_level, vehicle_count, inference_ms)

        return FrameResult(
            frame_idx=frame_idx,
            timestamp=time.time(),
            detections=detections,
            congestion_level=congestion_level,
            vehicle_count=vehicle_count,
            person_count=person_count,
            inference_ms=inference_ms,
            annotated_frame=annotated,
        )

    # ── Video processing ───────────────────────────────────────────────────────

    def process_video(
        self,
        source: str,
        skip_frames: int = 2,           # process every Nth frame (2 = 15fps from 30fps source)
        max_frames: Optional[int] = None,
        show_live: bool = False,
        output_path: Optional[str] = None,
    ):
        """
        Generator — yields FrameResult for each processed frame.

        Args:
            source:      video file path or RTSP URL or camera index (0, 1 ...)
            skip_frames: process 1 in every N frames to stay within latency budget
            max_frames:  stop after N frames (useful for demos)
            show_live:   display annotated output in a window (requires display)
            output_path: save annotated video to this path (.mp4)
        """
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source}")

        fps    = cap.get(cv2.CAP_PROP_FPS) or 30
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(f"Source: {source} | {width}x{height} @ {fps:.1f}fps | {total} frames total")

        writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps / max(skip_frames, 1), (width, height))

        frame_idx  = 0
        processed  = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                if frame_idx % skip_frames != 0:
                    continue

                result = self.detect_frame(frame, frame_idx)
                processed += 1

                if writer and result.annotated_frame is not None:
                    writer.write(result.annotated_frame)

                if show_live and result.annotated_frame is not None:
                    cv2.imshow("BengaluruTrafficAI", result.annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                yield result

                if max_frames and processed >= max_frames:
                    break

        finally:
            cap.release()
            if writer:
                writer.release()
            if show_live:
                cv2.destroyAllWindows()
            logger.info(f"Processed {processed} frames from {frame_idx} total")

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _parse_results(self, results, frame_idx: int) -> list[Detection]:
        detections = []
        for r in results:
            if r.boxes is None:
                continue
            boxes = r.boxes
            for i in range(len(boxes)):
                try:
                    class_id   = int(boxes.cls[i].item())
                    confidence = float(boxes.conf[i].item())
                    x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
                    track_id   = int(boxes.id[i].item()) if boxes.id is not None else None

                    class_name   = VEHICLE_CLASSES.get(class_id, "person" if class_id == PERSON_CLASS else "unknown")
                    vehicle_type = self._infer_vehicle_type(class_id, BoundingBox(x1, y1, x2, y2))

                    detections.append(Detection(
                        track_id=track_id,
                        class_id=class_id,
                        class_name=class_name,
                        vehicle_type=vehicle_type,
                        bbox=BoundingBox(x1, y1, x2, y2),
                        confidence=confidence,
                        frame_idx=frame_idx,
                    ))
                except Exception as e:
                    logger.debug(f"Skipping detection parse error: {e}")
        return detections

    def _infer_vehicle_type(self, class_id: int, bbox: BoundingBox) -> VehicleType:
        """
        Refine vehicle type beyond raw COCO class.
        Auto-rickshaws appear as motorcycles in COCO but are wider.
        """
        if class_id == PERSON_CLASS:
            return VehicleType.UNKNOWN
        if class_id == 2:  return VehicleType.CAR
        if class_id == 5:  return VehicleType.BUS
        if class_id == 7:  return VehicleType.TRUCK
        if class_id == 1:  return VehicleType.BICYCLE
        if class_id == 3:
            # Auto-rickshaw heuristic: wider aspect ratio than motorcycle
            aspect = bbox.width / max(bbox.height, 1)
            return VehicleType.AUTO if aspect > 1.15 else VehicleType.MOTORCYCLE
        return VehicleType.UNKNOWN

    def _classify_congestion(self, vehicle_count: int) -> CongestionLevel:
        for level, (low, high) in CONGESTION_THRESHOLDS.items():
            if low <= vehicle_count < high:
                return CongestionLevel(level)
        return CongestionLevel.JAMMED

    def _annotate(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        congestion: CongestionLevel,
        vehicle_count: int,
        inference_ms: float,
    ) -> np.ndarray:
        """Draw bounding boxes, labels, and HUD overlay on frame."""
        h, w = frame.shape[:2]

        for det in detections:
            color = self.COLORS.get(det.class_name, self.COLORS["unknown"])
            if det.is_person:
                color = self.COLORS["person"]

            b = det.bbox
            cv2.rectangle(frame, (b.x1, b.y1), (b.x2, b.y2), color, 2)

            label = f"{det.vehicle_type.value if det.is_vehicle else 'person'}"
            if det.track_id is not None:
                label += f" #{det.track_id}"
            label += f" {det.confidence:.2f}"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            ly = max(b.y1 - 4, th + 4)
            cv2.rectangle(frame, (b.x1, ly - th - 4), (b.x1 + tw + 4, ly), color, -1)
            cv2.putText(frame, label, (b.x1 + 2, ly - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # ── HUD bar ─────────────────────────────────────────────────────────
        hud_h = 48
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, hud_h), (15, 15, 15), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

        cong_color = self.CONGESTION_COLORS[congestion]
        cv2.putText(frame, "BengaluruTrafficAI", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Vehicles: {vehicle_count}", (220, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Congestion: {congestion.value.upper()}", (370, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, cong_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{inference_ms:.0f}ms", (w - 80, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)

        return frame
