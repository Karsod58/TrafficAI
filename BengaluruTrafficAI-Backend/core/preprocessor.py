"""
BengaluruTrafficAI — Video Preprocessing Layer
Ingestion layer preprocessing: image enhancement, frame selection, normalization

Components:
- Image enhancement (CLAHE, deblur, denoise)
- Frame selection (scene change detection, adaptive FPS)
- Normalization (resize, histogram equalization, format conversion)
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("preprocessor")


@dataclass
class PreprocessConfig:
    """Configuration for preprocessing pipeline"""
    # Image enhancement
    enable_clahe: bool = True
    enable_denoise: bool = False
    enable_deblur: bool = False
    
    # Frame selection
    enable_scene_detection: bool = True
    scene_threshold: float = 30.0  # Histogram difference threshold
    adaptive_fps: bool = True
    min_fps_divisor: int = 1
    max_fps_divisor: int = 5
    
    # Normalization
    target_width: Optional[int] = 1280
    target_height: Optional[int] = 720
    enable_histogram_eq: bool = False
    output_format: str = "BGR"  # BGR, RGB, or GRAY


class VideoPreprocessor:
    """
    Preprocesses video frames before feeding to detection pipeline.
    
    Usage:
        preprocessor = VideoPreprocessor(config)
        enhanced_frame = preprocessor.process(frame)
    """
    
    def __init__(self, config: PreprocessConfig = None):
        self.config = config or PreprocessConfig()
        self.prev_histogram = None
        self.frame_count = 0
        self.skip_counter = 0
        self.current_skip = self.config.min_fps_divisor
        
        # CLAHE for contrast enhancement
        if self.config.enable_clahe:
            self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        logger.info(f"VideoPreprocessor initialized | config={self.config}")
    
    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Process a single frame through the preprocessing pipeline.
        
        Returns:
            (processed_frame, should_process)
            should_process = False if frame should be skipped
        """
        if frame is None or frame.size == 0:
            return frame, False
        
        self.frame_count += 1
        
        # Frame selection - decide if we should process this frame
        should_process = self._should_process_frame(frame)
        
        if not should_process:
            return frame, False
        
        # Image enhancement
        processed = self._enhance_image(frame)
        
        # Normalization
        processed = self._normalize(processed)
        
        return processed, True
    
    def _should_process_frame(self, frame: np.ndarray) -> bool:
        """
        Frame selection logic:
        - Scene change detection: process frames with significant changes
        - Adaptive FPS: skip frames based on motion/activity level
        """
        # Always process first frame
        if self.frame_count == 1:
            self.prev_histogram = self._compute_histogram(frame)
            return True
        
        # Skip counter logic
        if self.skip_counter < self.current_skip:
            self.skip_counter += 1
            return False
        
        self.skip_counter = 0
        
        # Scene change detection
        if self.config.enable_scene_detection:
            curr_hist = self._compute_histogram(frame)
            hist_diff = cv2.compareHist(
                self.prev_histogram, 
                curr_hist, 
                cv2.HISTCMP_BHATTACHARYYA
            ) * 100
            
            self.prev_histogram = curr_hist
            
            # Scene change detected - process this frame
            if hist_diff > self.config.scene_threshold:
                logger.debug(f"Scene change detected: {hist_diff:.2f}")
                return True
            
            # Adaptive FPS based on activity
            if self.config.adaptive_fps:
                # More activity = lower skip rate
                if hist_diff > 15:
                    self.current_skip = self.config.min_fps_divisor
                elif hist_diff < 5:
                    self.current_skip = self.config.max_fps_divisor
                else:
                    # Gradual adjustment
                    self.current_skip = min(
                        self.current_skip + 1, 
                        self.config.max_fps_divisor
                    )
        
        return True
    
    def _compute_histogram(self, frame: np.ndarray) -> np.ndarray:
        """Compute histogram for scene change detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
        cv2.normalize(hist, hist)
        return hist
    
    def _enhance_image(self, frame: np.ndarray) -> np.ndarray:
        """
        Image enhancement pipeline:
        - CLAHE (Contrast Limited Adaptive Histogram Equalization)
        - Denoising
        - Deblurring
        """
        enhanced = frame.copy()
        
        # CLAHE for better contrast
        if self.config.enable_clahe:
            # Apply CLAHE to luminance channel only
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = self.clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Denoise for low-light or noisy feeds
        if self.config.enable_denoise:
            enhanced = cv2.fastNlMeansDenoisingColored(
                enhanced, None, 10, 10, 7, 21
            )
        
        # Deblur using unsharp masking
        if self.config.enable_deblur:
            gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
            enhanced = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
        
        return enhanced
    
    def _normalize(self, frame: np.ndarray) -> np.ndarray:
        """
        Normalize frame:
        - Resize to target resolution
        - Histogram equalization (optional)
        - Format conversion
        """
        normalized = frame.copy()
        
        # Resize
        if self.config.target_width and self.config.target_height:
            h, w = normalized.shape[:2]
            if w != self.config.target_width or h != self.config.target_height:
                normalized = cv2.resize(
                    normalized, 
                    (self.config.target_width, self.config.target_height),
                    interpolation=cv2.INTER_AREA
                )
        
        # Histogram equalization
        if self.config.enable_histogram_eq:
            ycrcb = cv2.cvtColor(normalized, cv2.COLOR_BGR2YCrCb)
            ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
            normalized = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
        
        # Format conversion
        if self.config.output_format == "RGB":
            normalized = cv2.cvtColor(normalized, cv2.COLOR_BGR2RGB)
        elif self.config.output_format == "GRAY":
            normalized = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
        
        return normalized
    
    def reset(self):
        """Reset preprocessor state for new video"""
        self.prev_histogram = None
        self.frame_count = 0
        self.skip_counter = 0
        self.current_skip = self.config.min_fps_divisor
        logger.info("Preprocessor state reset")


class MultiSourceIngestion:
    """
    Ingestion layer for multiple video sources:
    - CCTV/IP cameras
    - Mobile units
    - Drone feeds
    - Edge gateway
    """
    
    @staticmethod
    def normalize_source(source: str) -> Tuple[str, str]:
        """
        Normalize and categorize video source.
        
        Returns:
            (normalized_url, source_type)
        """
        source_lower = source.lower()
        
        # RTSP streams (IP cameras)
        if source.startswith("rtsp://"):
            return source, "ip_camera"
        
        # HTTP/HTTPS streams
        if source.startswith(("http://", "https://")):
            if "youtube" in source or "youtu.be" in source:
                return source, "youtube"
            return source, "http_stream"
        
        # Local webcam
        if source.isdigit():
            return int(source), "webcam"
        
        # File path
        return source, "file"
    
    @staticmethod
    def get_optimal_config(source_type: str) -> PreprocessConfig:
        """Get optimal preprocessing config for source type"""
        
        if source_type == "ip_camera":
            # IP cameras often have good quality but may have compression artifacts
            return PreprocessConfig(
                enable_clahe=True,
                enable_denoise=False,
                enable_deblur=False,
                adaptive_fps=True,
                min_fps_divisor=1,
                max_fps_divisor=3,
            )
        
        elif source_type == "mobile":
            # Mobile units may have motion blur and varying lighting
            return PreprocessConfig(
                enable_clahe=True,
                enable_denoise=True,
                enable_deblur=True,
                adaptive_fps=True,
                min_fps_divisor=2,
                max_fps_divisor=5,
            )
        
        elif source_type == "drone":
            # Drone feeds have high resolution but may have stability issues
            return PreprocessConfig(
                enable_clahe=False,
                enable_denoise=True,
                enable_deblur=True,
                adaptive_fps=True,
                target_width=1920,
                target_height=1080,
            )
        
        else:
            # Default config
            return PreprocessConfig()
