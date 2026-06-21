"""
BengaluruTrafficAI — ROI (Region of Interest) Manager
Component 1b: Defines and manages spatial zones used by violation detectors.

Each camera has its own ROI config because junctions differ in layout.
ROIs are drawn once using the setup tool and saved as JSON per camera.
"""

import json
import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger("roi_manager")


@dataclass
class ROIZone:
    """A named spatial region for violation detection."""
    name:        str                    # e.g. "stop_line", "no_parking_left"
    zone_type:   str                    # stop_line | lane | no_parking | signal_box | count_line
    points:      list[tuple[int, int]]  # polygon vertices or line endpoints
    direction:   Optional[str] = None   # permitted travel direction for lanes: "up","down","left","right"
    color:       tuple = (0, 255, 100)  # display color (BGR)

    @property
    def as_numpy(self) -> np.ndarray:
        return np.array(self.points, dtype=np.int32)

    def contains_point(self, x: int, y: int) -> bool:
        """Check if (x,y) is inside this polygon zone."""
        pt = np.array([[x, y]], dtype=np.float32)
        result = cv2.pointPolygonTest(self.as_numpy, (float(x), float(y)), False)
        return result >= 0

    def line_crossed(self, prev_center: tuple, curr_center: tuple) -> bool:
        """
        Check if a vehicle track crossed this zone's line between two frames.
        Only valid for stop_line and count_line types (2-point line).
        """
        if len(self.points) != 2:
            return False
        p1, p2 = self.points
        # Cross product sign change = line crossed
        def cross(o, a, b):
            return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
        d1 = cross(p1, p2, prev_center)
        d2 = cross(p1, p2, curr_center)
        return (d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)


class ROIManager:
    """
    Manages ROI zones per camera.

    Usage:
        roi = ROIManager("cam_07")
        roi.load("data/rois/cam_07.json")       # load saved config
        # or define programmatically:
        roi.add_stop_line([(300,400),(900,400)])
        roi.add_no_parking([(50,200),(200,200),(200,500),(50,500)])
    """

    ZONE_COLORS = {
        "stop_line":   (0, 80, 255),
        "lane":        (0, 200, 255),
        "no_parking":  (255, 50, 50),
        "signal_box":  (255, 200, 0),
        "count_line":  (0, 255, 150),
    }

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.zones: list[ROIZone] = []

    def add_stop_line(self, points: list[tuple], name: str = "stop_line"):
        self.zones.append(ROIZone(
            name=name, zone_type="stop_line", points=points,
            color=self.ZONE_COLORS["stop_line"]
        ))

    def add_lane(self, points: list[tuple], direction: str, name: str = "lane"):
        self.zones.append(ROIZone(
            name=name, zone_type="lane", points=points,
            direction=direction, color=self.ZONE_COLORS["lane"]
        ))

    def add_no_parking(self, points: list[tuple], name: str = "no_parking"):
        self.zones.append(ROIZone(
            name=name, zone_type="no_parking", points=points,
            color=self.ZONE_COLORS["no_parking"]
        ))

    def add_signal_box(self, points: list[tuple], name: str = "signal_box"):
        self.zones.append(ROIZone(
            name=name, zone_type="signal_box", points=points,
            color=self.ZONE_COLORS["signal_box"]
        ))

    def get_zones_by_type(self, zone_type: str) -> list[ROIZone]:
        return [z for z in self.zones if z.zone_type == zone_type]

    # ── Persistence ────────────────────────────────────────────────────────────

    def save(self, path: str):
        data = {
            "camera_id": self.camera_id,
            "zones": [
                {"name": z.name, "zone_type": z.zone_type,
                 "points": z.points, "direction": z.direction}
                for z in self.zones
            ]
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.zones)} ROI zones to {path}")

    def load(self, path: str):
        with open(path) as f:
            data = json.load(f)
        self.zones = []
        for z in data["zones"]:
            self.zones.append(ROIZone(
                name=z["name"],
                zone_type=z["zone_type"],
                points=[tuple(p) for p in z["points"]],
                direction=z.get("direction"),
                color=self.ZONE_COLORS.get(z["zone_type"], (100, 100, 100))
            ))
        logger.info(f"Loaded {len(self.zones)} ROI zones from {path}")

    # ── Visual overlay ─────────────────────────────────────────────────────────

    def draw(self, frame: np.ndarray, alpha: float = 0.25) -> np.ndarray:
        """Draw all ROI zones on frame with semi-transparent fill."""
        overlay = frame.copy()
        for zone in self.zones:
            pts = zone.as_numpy
            if zone.zone_type == "stop_line" and len(zone.points) == 2:
                cv2.line(frame, tuple(zone.points[0]), tuple(zone.points[1]),
                         zone.color, 3, cv2.LINE_AA)
                mid = ((zone.points[0][0]+zone.points[1][0])//2,
                       (zone.points[0][1]+zone.points[1][1])//2 - 8)
                cv2.putText(frame, "STOP LINE", mid,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, zone.color, 1, cv2.LINE_AA)
            elif len(zone.points) >= 3:
                cv2.fillPoly(overlay, [pts], zone.color)
                cv2.polylines(frame, [pts], True, zone.color, 2)
                cx = int(np.mean([p[0] for p in zone.points]))
                cy = int(np.mean([p[1] for p in zone.points]))
                cv2.putText(frame, zone.name.upper(), (cx - 30, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, zone.color, 1, cv2.LINE_AA)
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # ── Interactive setup tool ─────────────────────────────────────────────────

    @classmethod
    def setup_interactive(cls, camera_id: str, frame: np.ndarray, save_path: str):
        """
        Opens an OpenCV window to draw ROIs by clicking.
        Press:
            S = stop line (click 2 points)
            L = lane polygon (click 4+ points, Enter to confirm)
            P = no-parking zone (click 4+ points, Enter to confirm)
            G = signal box (click 4 points)
            Z = undo last zone
            Q = save and quit
        """
        roi = cls(camera_id)
        current_pts = []
        current_mode = None
        clone = frame.copy()
        display = frame.copy()

        MODE_NAMES = {"s":"stop_line","l":"lane","p":"no_parking","g":"signal_box"}
        HELP = "S=StopLine L=Lane P=NoParking G=SignalBox Z=Undo Q=Save+Quit"

        def mouse_cb(event, x, y, flags, param):
            nonlocal display
            if event == cv2.EVENT_LBUTTONDOWN and current_mode:
                current_pts.append((x, y))
                display = roi.draw(clone.copy())
                for pt in current_pts:
                    cv2.circle(display, pt, 5, (255,255,0), -1)
                if len(current_pts) > 1:
                    cv2.polylines(display, [np.array(current_pts)], False, (255,255,0), 1)
                cv2.imshow("ROI Setup", display)

        cv2.namedWindow("ROI Setup")
        cv2.setMouseCallback("ROI Setup", mouse_cb)

        while True:
            show = display.copy()
            cv2.putText(show, HELP, (10, frame.shape[0]-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)
            if current_mode:
                cv2.putText(show, f"Mode: {MODE_NAMES.get(current_mode,'?')} | pts: {len(current_pts)} | Enter=confirm",
                            (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,0), 1)
            cv2.imshow("ROI Setup", show)
            key = cv2.waitKey(20) & 0xFF

            if key in [ord("s"),ord("l"),ord("p"),ord("g")]:
                current_mode = chr(key)
                current_pts.clear()
            elif key == 13:  # Enter — confirm current zone
                if current_mode == "s" and len(current_pts) >= 2:
                    roi.add_stop_line(current_pts[:2])
                elif current_mode == "l" and len(current_pts) >= 4:
                    direction = input("Lane direction (up/down/left/right): ").strip()
                    roi.add_lane(current_pts, direction)
                elif current_mode == "p" and len(current_pts) >= 3:
                    roi.add_no_parking(current_pts)
                elif current_mode == "g" and len(current_pts) >= 4:
                    roi.add_signal_box(current_pts)
                current_pts.clear()
                display = roi.draw(clone.copy())
            elif key == ord("z") and roi.zones:
                roi.zones.pop()
                display = roi.draw(clone.copy())
            elif key == ord("q"):
                roi.save(save_path)
                break

        cv2.destroyAllWindows()
        return roi
