"""
BengaluruTrafficAI — ALPR (Automatic License Plate Recognition)
Component 3: Indian number plate detection + OCR

Pipeline:
  1. YOLOv8n detects plate region in vehicle crop
  2. PaddleOCR extracts text (handles KA, DL, MH, UP etc.)
  3. Regex normalises to Indian plate format
  4. Returns plate string + confidence

Indian plate formats supported:
  KA 01 AB 1234   (Karnataka)
  DL 4C AB 1234   (Delhi)
  MH 12 AB 1234   (Maharashtra)
  UP 32 GH 0012   (Uttar Pradesh)
"""

import re
import cv2
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("alpr")

# Indian plate regex — covers BH series too
PLATE_PATTERN = re.compile(
    r"([A-Z]{2})\s*(\d{2})\s*([A-Z]{1,3})\s*(\d{1,4})"
)
BH_PATTERN = re.compile(r"(\d{2})\s*BH\s*(\d{4})\s*([A-Z]{1,2})")


@dataclass
class PlateResult:
    raw_text:     str
    plate_number: str           # normalised e.g. "KA01AB1234"
    state_code:   str           # e.g. "KA"
    confidence:   float
    bbox:         Optional[tuple] = None   # plate bbox in original frame

    @property
    def is_valid(self) -> bool:
        return bool(self.plate_number) and len(self.plate_number) >= 6 and self.confidence > 0.30  # lowered from 0.40

    def to_dict(self) -> dict:
        return {
            "raw_text":     self.raw_text,
            "plate_number": self.plate_number,
            "state_code":   self.state_code,
            "confidence":   round(self.confidence, 3),
            "bbox":         self.bbox,
        }


class ALPRModule:
    """
    Automatic License Plate Recognition for Indian vehicles.

    Usage:
        alpr = ALPRModule()
        result = alpr.process(frame, vehicle_bbox)
        if result.is_valid:
            print(result.plate_number)  # "KA01AB1234"
    """

    # Plate detection uses a lightweight YOLO model
    # For the demo we'll use a colour + contour fallback if model not available
    PLATE_ASPECT_MIN = 1.5     # width/height ratio of valid plate (more lenient)
    PLATE_ASPECT_MAX = 8.0     # increased max for perspective variations
    PLATE_AREA_FRAC  = 0.005   # reduced to 0.5% for low-res videos

    def __init__(self, plate_model_path: Optional[str] = None):
        self.plate_model = None
        self.ocr = None

        # Load plate detector
        if plate_model_path:
            try:
                from ultralytics import YOLO
                self.plate_model = YOLO(plate_model_path)
                logger.info(f"Plate detector loaded: {plate_model_path}")
            except Exception as e:
                logger.warning(f"Could not load plate model: {e}")

        # Load PaddleOCR
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False
            )
            logger.info("PaddleOCR loaded")
        except ImportError:
            logger.warning("PaddleOCR not installed. Run: pip install paddleocr paddlepaddle")
        except Exception as e:
            logger.warning(f"PaddleOCR init error: {e}")

    def process(self, frame: np.ndarray, vehicle_bbox) -> Optional[PlateResult]:
        """
        Full ALPR pipeline on one vehicle detection.
        Returns PlateResult or None if no plate found.
        """
        # 1. Crop vehicle region
        vehicle_crop = self._crop_vehicle(frame, vehicle_bbox)
        if vehicle_crop is None:
            return None

        # 2. Detect plate region
        plate_crop, plate_bbox = self._detect_plate(vehicle_crop, vehicle_bbox)
        if plate_crop is None:
            return None

        # 3. Preprocess plate crop
        plate_enhanced = self._enhance_plate(plate_crop)

        # 4. OCR
        raw_text, ocr_conf = self._run_ocr(plate_enhanced)
        if not raw_text:
            return None

        # 5. Normalise
        plate_number, state_code = self._normalise(raw_text)

        return PlateResult(
            raw_text=raw_text,
            plate_number=plate_number,
            state_code=state_code,
            confidence=ocr_conf,
            bbox=plate_bbox,
        )

    def process_batch(self, frame: np.ndarray, vehicle_detections: list) -> dict:
        """
        Run ALPR on multiple vehicles in one frame.
        Returns {track_id: PlateResult} mapping.
        """
        results = {}
        for det in vehicle_detections:
            if not det.is_vehicle:
                continue
            result = self.process(frame, det.bbox)
            if result and result.is_valid:
                results[det.track_id] = result
                logger.debug(f"Plate: {result.plate_number} track={det.track_id} conf={result.confidence:.2f}")
        return results

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _crop_vehicle(self, frame: np.ndarray, bbox) -> Optional[np.ndarray]:
        h, w = frame.shape[:2]
        x1 = max(0, bbox.x1)
        y1 = max(0, bbox.y1)
        x2 = min(w, bbox.x2)
        y2 = min(h, bbox.y2)
        if x2 <= x1 or y2 <= y1:
            return None
        crop = frame[y1:y2, x1:x2]
        return crop if crop.size > 0 else None

    def _detect_plate(self, vehicle_crop: np.ndarray, vehicle_bbox) -> tuple:
        """
        Returns (plate_crop, plate_bbox_in_original_frame).
        Uses YOLO model if available, otherwise contour-based fallback.
        """
        if self.plate_model:
            return self._detect_plate_yolo(vehicle_crop, vehicle_bbox)
        return self._detect_plate_contour(vehicle_crop, vehicle_bbox)

    def _detect_plate_yolo(self, crop: np.ndarray, vehicle_bbox) -> tuple:
        try:
            results = self.plate_model(crop, verbose=False, conf=0.35)
            for r in results:
                if r.boxes is None or len(r.boxes) == 0:
                    continue
                box = r.boxes[0]
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                plate_crop = crop[y1:y2, x1:x2]
                abs_bbox = (
                    vehicle_bbox.x1 + x1, vehicle_bbox.y1 + y1,
                    vehicle_bbox.x1 + x2, vehicle_bbox.y1 + y2
                )
                return plate_crop, abs_bbox
        except Exception as e:
            logger.debug(f"YOLO plate detection error: {e}")
        return None, None

    def _detect_plate_contour(self, crop: np.ndarray, vehicle_bbox) -> tuple:
        """
        Contour-based plate detection fallback.
        Plates appear as white/yellow rectangles with specific aspect ratio
        in the lower portion of the vehicle bounding box.
        """
        h, w = crop.shape[:2]
        
        # Upscale crop for better detection in low-res videos
        if w < 300:
            scale_factor = 300 / w
            crop = cv2.resize(crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
            h, w = crop.shape[:2]
        
        # Search lower 60% of vehicle (plate is typically at bottom)
        search_region = crop[int(h*0.4):, :]

        # Enhanced preprocessing for plate detection
        gray = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
        
        # Use bilateral filter to preserve edges while reducing noise
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(filtered)
        
        # Multiple edge detection strategies
        edges1 = cv2.Canny(enhanced, 30, 150)
        edges2 = cv2.Canny(enhanced, 50, 200)
        edges = cv2.bitwise_or(edges1, edges2)

        # More aggressive dilation to connect plate characters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
        dilated = cv2.dilate(edges, kernel, iterations=3)
        
        # Morphological closing to fill gaps
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel_close)
        
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        vehicle_area = h * w
        candidates = []

        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            if ch == 0 or cw == 0:
                continue

            aspect = cw / ch
            area_ratio = (cw * ch) / max(vehicle_area, 1)

            # More lenient criteria for low-res videos
            if (self.PLATE_ASPECT_MIN <= aspect <= self.PLATE_ASPECT_MAX
                    and area_ratio >= self.PLATE_AREA_FRAC
                    and cw >= 30  # minimum width reduced
                    and ch >= 8):  # minimum height
                
                # Calculate score based on aspect ratio and position
                # Prefer candidates closer to standard plate aspect (3.5-4.5)
                aspect_score = 1.0 - abs(aspect - 4.0) / 4.0
                # Prefer candidates in lower part of search region
                position_score = y / search_region.shape[0]
                score = aspect_score * 0.7 + position_score * 0.3
                
                candidates.append({
                    'rect': (x, y, cw, ch),
                    'aspect': aspect,
                    'score': score
                })
        
        # Sort by score and try best candidates
        candidates.sort(key=lambda c: c['score'], reverse=True)
        
        for candidate in candidates[:3]:  # Try top 3 candidates
            x, y, cw, ch = candidate['rect']
            
            # Extract plate region
            plate_crop = search_region[y:y+ch, x:x+cw]
            
            # Adjust coordinates back to original frame
            y_offset = int(h * 0.4)
            abs_bbox = (
                vehicle_bbox.x1 + int(x / (300 / vehicle_bbox.width if w >= 300 else 1)),
                vehicle_bbox.y1 + y_offset + int(y / (300 / vehicle_bbox.width if w >= 300 else 1)),
                vehicle_bbox.x1 + int((x + cw) / (300 / vehicle_bbox.width if w >= 300 else 1)),
                vehicle_bbox.y1 + y_offset + int((y + ch) / (300 / vehicle_bbox.width if w >= 300 else 1))
            )
            
            return plate_crop, abs_bbox

        return None, None

    def _enhance_plate(self, plate: np.ndarray) -> np.ndarray:
        """
        Enhance plate crop for better OCR:
          - Upscale to at least 300px wide for better OCR
          - Multiple preprocessing strategies
          - Sharpen and enhance contrast
        """
        if plate is None or plate.size == 0:
            return plate

        h, w = plate.shape[:2]
        
        # Aggressive upscaling for low-res plates
        target_width = 400  # increased from 200
        if w < target_width:
            scale = target_width / w
            plate = cv2.resize(plate, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            h, w = plate.shape[:2]

        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while preserving edges
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Multiple thresholding strategies - try to capture both black and white plates
        # Adaptive threshold
        thresh1 = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 10
        )
        
        # Otsu's thresholding
        _, thresh2 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Combine both thresholds
        thresh = cv2.bitwise_and(thresh1, thresh2)
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        # Sharpen
        kernel_sharpen = np.array([[-1,-1,-1],
                                    [-1, 9,-1],
                                    [-1,-1,-1]])
        sharpened = cv2.filter2D(cleaned, -1, kernel_sharpen)
        
        # Add border to help OCR
        bordered = cv2.copyMakeBorder(sharpened, 10, 10, 10, 10, 
                                       cv2.BORDER_CONSTANT, value=255)
        
        return cv2.cvtColor(bordered, cv2.COLOR_GRAY2BGR)

    def _run_ocr(self, plate: np.ndarray) -> tuple[str, float]:
        """Returns (raw_text, confidence)."""
        if plate is None or plate.size == 0:
            return "", 0.0

        # PaddleOCR path
        if self.ocr:
            try:
                # Run OCR multiple times with different preprocessing for better accuracy
                results_list = []
                
                # Try original
                result1 = self.ocr.ocr(plate, cls=True)
                if result1 and result1[0]:
                    results_list.append(result1)
                
                # Try inverted (for white text on dark background)
                inverted = cv2.bitwise_not(plate)
                result2 = self.ocr.ocr(inverted, cls=True)
                if result2 and result2[0]:
                    results_list.append(result2)
                
                # Process all results and pick the best one
                best_text = ""
                best_conf = 0.0
                
                for result in results_list:
                    if result and result[0]:
                        texts = [line[1][0] for line in result[0] if line[1]]
                        confs = [line[1][1] for line in result[0] if line[1]]
                        
                        if texts and confs:
                            raw = " ".join(texts).upper().replace(" ", "")
                            avg_cf = sum(confs) / len(confs)
                            
                            # Check if this looks like a valid Indian plate
                            if len(raw) >= 6 and avg_cf > best_conf:
                                best_text = raw
                                best_conf = avg_cf
                
                if best_text:
                    logger.debug(f"OCR result: {best_text} (conf={best_conf:.2f})")
                    return best_text, best_conf
                    
            except Exception as e:
                logger.debug(f"PaddleOCR error: {e}")

        # Fallback: return empty
        return "", 0.0

    def _normalise(self, raw: str) -> tuple[str, str]:
        """
        Normalise raw OCR text to Indian plate format.
        Returns (normalised_plate, state_code).
        """
        # Remove common OCR noise characters
        cleaned = re.sub(r"[^A-Z0-9]", "", raw.upper())

        # Try standard format KA01AB1234
        match = PLATE_PATTERN.search(cleaned)
        if match:
            state = match.group(1)
            district = match.group(2)
            series = match.group(3)
            number = match.group(4).zfill(4)
            plate = f"{state}{district}{series}{number}"
            return plate, state

        # Try BH series 22BH1234AB
        bh_match = BH_PATTERN.search(cleaned)
        if bh_match:
            plate = f"{bh_match.group(1)}BH{bh_match.group(2)}{bh_match.group(3)}"
            return plate, "BH"

        # Return cleaned text even if format doesn't match
        return cleaned[:12] if cleaned else "", cleaned[:2] if cleaned else ""
