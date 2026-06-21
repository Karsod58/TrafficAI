"""
BengaluruTrafficAI — Evidence Generator
Component 4: Produces annotated evidence packages for each confirmed violation.

Each package contains:
  - Annotated JPEG (bounding boxes, violation label, timestamp, plate)
  - SHA-256 hash for tamper-proofing
  - JSON metadata record
"""

import cv2
import json
import hashlib
import time
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional

from violations.base import ViolationEvent, ViolationType

logger = logging.getLogger("evidence")

EVIDENCE_ROOT = Path("output/evidence")

VIOLATION_COLORS_BGR = {
    ViolationType.NO_HELMET:       (0,   80,  255),
    ViolationType.NO_SEATBELT:     (0,   140, 255),
    ViolationType.TRIPLE_RIDING:   (50,  50,  255),
    ViolationType.WRONG_SIDE:      (200, 0,   255),
    ViolationType.STOP_LINE:       (255, 200, 0),
    ViolationType.RED_LIGHT:       (0,   0,   255),
    ViolationType.ILLEGAL_PARKING: (0,   165, 255),
}


class EvidenceGenerator:
    """
    Generates tamper-evident evidence packages for violation events.

    Usage:
        ev_gen = EvidenceGenerator(camera_id="cam_07", output_dir="output/evidence")
        package = ev_gen.generate(violation_event, annotated_frame)
    """

    JPEG_QUALITY = 92

    def __init__(self, camera_id: str = "unknown", output_dir: str = "output/evidence"):
        self.camera_id  = camera_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"EvidenceGenerator ready → {self.output_dir}")

    def generate(
        self,
        event:            ViolationEvent,
        frame:            np.ndarray,
        plate_number:     Optional[str] = None,
        gps_coords:       Optional[tuple] = None,  # (lat, lon)
    ) -> dict:
        """
        Generate a complete evidence package for one violation event.
        Returns metadata dict including file paths and hash.
        """
        event.plate_number = plate_number

        # Build annotated evidence frame
        evidence_frame = self._build_evidence_frame(frame, event, plate_number, gps_coords)

        # Save image
        ts_str    = datetime.fromtimestamp(event.timestamp).strftime("%Y%m%d_%H%M%S")
        filename  = f"{event.violation_type.value}_{ts_str}_{event.event_id}"
        img_path  = self.output_dir / f"{filename}.jpg"
        json_path = self.output_dir / f"{filename}.json"

        cv2.imwrite(str(img_path), evidence_frame, [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY])

        # Compute hash
        img_hash = self._sha256(img_path)

        # Build metadata
        metadata = {
            **event.to_dict(),
            "plate_number":   plate_number,
            "gps_coords":     gps_coords,
            "image_path":     str(img_path),
            "image_hash_sha256": img_hash,
            "generated_at":   datetime.utcnow().isoformat() + "Z",
        }

        with open(json_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(
            f"Evidence saved | {event.violation_type.value} | "
            f"plate={plate_number} | conf={event.confidence:.2f} | {img_path.name}"
        )
        return metadata

    def _build_evidence_frame(
        self,
        frame:        np.ndarray,
        event:        ViolationEvent,
        plate_number: Optional[str],
        gps_coords:   Optional[tuple],
    ) -> np.ndarray:
        out   = frame.copy()
        color = VIOLATION_COLORS_BGR.get(event.violation_type, (255, 255, 255))

        # Violation bounding box
        if event.bbox:
            x1, y1, x2, y2 = event.bbox
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 3)

            # Corner markers
            for (cx, cy, sx, sy) in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(out, (cx, cy), (cx+sx*20, cy),    color, 3)
                cv2.line(out, (cx, cy), (cx, cy+sy*20),    color, 3)

        h, w = out.shape[:2]

        # ── Bottom info banner ────────────────────────────────────────────────
        banner_h = 60
        banner   = np.zeros((banner_h, w, 3), dtype=np.uint8)
        banner[:] = (20, 20, 20)

        vtype  = event.violation_type.value.upper().replace("_", " ")
        ts_str = datetime.fromtimestamp(event.timestamp).strftime("%d-%b-%Y  %H:%M:%S")
        plate  = plate_number or "PLATE N/A"
        conf   = f"CONF: {event.confidence:.2f}"
        fine   = f"FINE: ₹{event.fine_inr:,}"
        cam    = f"CAM: {self.camera_id.upper()}"

        cv2.putText(banner, vtype,  (10, 22),  cv2.FONT_HERSHEY_SIMPLEX, 0.60, color,      1, cv2.LINE_AA)
        cv2.putText(banner, plate,  (10, 46),  cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200,200,200), 1, cv2.LINE_AA)
        cv2.putText(banner, ts_str, (w//2-120, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180,180,180), 1, cv2.LINE_AA)
        cv2.putText(banner, conf,   (w//2-120, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150,150,150), 1, cv2.LINE_AA)
        cv2.putText(banner, fine,   (w-200, 22),    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0,200,120),   1, cv2.LINE_AA)
        cv2.putText(banner, cam,    (w-200, 46),    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150,150,150), 1, cv2.LINE_AA)

        if gps_coords:
            gps_text = f"GPS: {gps_coords[0]:.5f},{gps_coords[1]:.5f}"
            cv2.putText(banner, gps_text, (w//2+80, 46),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (100,180,255), 1, cv2.LINE_AA)

        # Watermark
        cv2.putText(out, "BengaluruTrafficAI  |  OFFICIAL EVIDENCE",
                    (10, h - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 100, 100), 1, cv2.LINE_AA)

        return np.vstack([out, banner])

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
