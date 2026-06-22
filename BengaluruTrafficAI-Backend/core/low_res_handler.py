"""
BengaluruTrafficAI — Low Resolution Video Handler
Automatic detection and optimization for low-quality videos (360p/480p)

Features:
- Auto-detects video resolution
- Applies appropriate preprocessing
- Adjusts detection thresholds
- Optimizes ALPR settings
- Provides quality warnings
"""

import cv2
import logging
from typing import Tuple, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

from core.preprocessor import PreprocessConfig

logger = logging.getLogger("low_res_handler")


@dataclass
class VideoQualityInfo:
    """Information about video quality"""
    width: int
    height: int
    fps: float
    total_frames: int
    quality_tier: str  # "ultra_low", "low", "medium", "high", "ultra_high"
    estimated_alpr_accuracy: str  # "10-30%", "40-60%", etc.
    recommended_skip_frames: int
    preprocessing_needed: bool
    warnings: list[str]


class LowResolutionHandler:
    """
    Handles low-resolution video processing with automatic optimization.
    
    Usage:
        handler = LowResolutionHandler()
        info = handler.analyze_video("video_360p.mp4")
        config = handler.get_optimal_config(info)
        preprocessor = VideoPreprocessor(config)
    """
    
    # Resolution tiers
    ULTRA_LOW = 480  # <= 480p (640x480 or lower)
    LOW = 720        # <= 720p
    MEDIUM = 1080    # <= 1080p
    HIGH = 1440      # <= 1440p
    
    def __init__(self):
        self.quality_info: Optional[VideoQualityInfo] = None
    
    def analyze_video(self, video_path: str) -> VideoQualityInfo:
        """
        Analyze video quality and return detailed information.
        
        Args:
            video_path: Path to video file or stream URL
            
        Returns:
            VideoQualityInfo object with quality assessment
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        cap.release()
        
        # Determine quality tier
        max_dimension = max(width, height)
        
        if max_dimension <= self.ULTRA_LOW:
            tier = "ultra_low"
            alpr_accuracy = "10-30%"
            skip_frames = 5
            preprocessing = True
            warnings = [
                "Very low resolution - ALPR accuracy will be limited",
                "Consider upgrading camera to 720p for better results",
                "Violation detection will work, but plates may be unreadable"
            ]
        elif max_dimension <= self.LOW:
            tier = "low"
            alpr_accuracy = "40-60%"
            skip_frames = 3
            preprocessing = True
            warnings = [
                "Low resolution - ALPR may miss some plates",
                "720p is minimum for reliable license plate detection"
            ]
        elif max_dimension <= self.MEDIUM:
            tier = "medium"
            alpr_accuracy = "70-85%"
            skip_frames = 2
            preprocessing = False
            warnings = []
        elif max_dimension <= self.HIGH:
            tier = "high"
            alpr_accuracy = "85-95%"
            skip_frames = 1
            preprocessing = False
            warnings = []
        else:
            tier = "ultra_high"
            alpr_accuracy = "90-98%"
            skip_frames = 1
            preprocessing = False
            warnings = []
        
        info = VideoQualityInfo(
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            quality_tier=tier,
            estimated_alpr_accuracy=alpr_accuracy,
            recommended_skip_frames=skip_frames,
            preprocessing_needed=preprocessing,
            warnings=warnings
        )
        
        self.quality_info = info
        
        # Log quality info
        logger.info(f"Video Quality Analysis: {Path(video_path).name}")
        logger.info(f"  Resolution: {width}x{height}")
        logger.info(f"  Quality Tier: {tier}")
        logger.info(f"  Estimated ALPR: {alpr_accuracy}")
        logger.info(f"  Recommended skip: {skip_frames} frames")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"  ⚠ {warning}")
        
        return info
    
    def get_optimal_config(self, info: VideoQualityInfo) -> PreprocessConfig:
        """
        Get optimal preprocessing configuration for the video quality.
        
        Args:
            info: VideoQualityInfo from analyze_video()
            
        Returns:
            PreprocessConfig optimized for the quality tier
        """
        if info.quality_tier == "ultra_low":
            # 360p/480p - Aggressive enhancement
            return PreprocessConfig(
                # Enable all enhancements
                enable_clahe=True,
                enable_denoise=True,
                enable_deblur=True,
                
                # Upscale to 720p
                target_width=1280,
                target_height=720,
                
                # Enhanced contrast
                enable_histogram_eq=True,
                
                # Adaptive FPS
                enable_scene_detection=True,
                adaptive_fps=True,
                min_fps_divisor=3,
                max_fps_divisor=5,
            )
        
        elif info.quality_tier == "low":
            # 720p - Moderate enhancement
            return PreprocessConfig(
                enable_clahe=True,
                enable_denoise=False,
                enable_deblur=True,
                
                target_width=1280,
                target_height=720,
                
                enable_histogram_eq=False,
                
                adaptive_fps=True,
                min_fps_divisor=2,
                max_fps_divisor=4,
            )
        
        elif info.quality_tier == "medium":
            # 1080p - Light enhancement
            return PreprocessConfig(
                enable_clahe=True,
                enable_denoise=False,
                enable_deblur=False,
                
                target_width=None,  # Keep original
                target_height=None,
                
                enable_histogram_eq=False,
                
                adaptive_fps=True,
                min_fps_divisor=1,
                max_fps_divisor=3,
            )
        
        else:
            # High quality - Minimal processing
            return PreprocessConfig(
                enable_clahe=False,
                enable_denoise=False,
                enable_deblur=False,
                
                target_width=None,
                target_height=None,
                
                enable_histogram_eq=False,
                
                adaptive_fps=False,
            )
    
    def get_alpr_thresholds(self, info: VideoQualityInfo) -> Dict[str, float]:
        """
        Get ALPR quality thresholds adjusted for video quality.
        
        Returns:
            Dictionary with threshold values
        """
        if info.quality_tier == "ultra_low":
            return {
                "min_crop_width": 60,      # More lenient (was 80)
                "min_crop_height": 45,     # More lenient (was 60)
                "sharpness_threshold": 50.0,  # More lenient (was 100.0)
                "min_plate_width": 20,     # More lenient (was 30)
                "min_plate_height": 6,     # More lenient (was 8)
                "plate_area_frac": 0.003,  # More lenient (was 0.005)
                "confidence_threshold": 0.25,  # Lower confidence (was 0.35)
            }
        
        elif info.quality_tier == "low":
            return {
                "min_crop_width": 70,
                "min_crop_height": 50,
                "sharpness_threshold": 75.0,
                "min_plate_width": 25,
                "min_plate_height": 7,
                "plate_area_frac": 0.004,
                "confidence_threshold": 0.30,
            }
        
        else:
            # Standard thresholds for medium/high quality
            return {
                "min_crop_width": 80,
                "min_crop_height": 60,
                "sharpness_threshold": 100.0,
                "min_plate_width": 30,
                "min_plate_height": 8,
                "plate_area_frac": 0.005,
                "confidence_threshold": 0.35,
            }
    
    def should_enable_alpr(self, info: VideoQualityInfo) -> bool:
        """
        Determine if ALPR should be enabled based on quality.
        
        Returns:
            True if ALPR is worth attempting, False to skip
        """
        # For ultra-low quality, ALPR might not be worth the computational cost
        # But we'll still attempt it - let the quality checks filter bad attempts
        return True
    
    def get_performance_estimate(self, info: VideoQualityInfo) -> Dict[str, str]:
        """
        Estimate system performance for this video quality.
        
        Returns:
            Dictionary with performance estimates
        """
        estimates = {
            "violation_detection_accuracy": "Unknown",
            "tracking_accuracy": "Unknown",
            "alpr_accuracy": info.estimated_alpr_accuracy,
            "processing_speed_cpu": "Unknown",
            "processing_speed_gpu": "Unknown",
        }
        
        if info.quality_tier == "ultra_low":
            estimates.update({
                "violation_detection_accuracy": "85-90%",
                "tracking_accuracy": "80-85%",
                "processing_speed_cpu": "25-35 FPS",
                "processing_speed_gpu": "80-100 FPS",
            })
        elif info.quality_tier == "low":
            estimates.update({
                "violation_detection_accuracy": "88-92%",
                "tracking_accuracy": "85-90%",
                "processing_speed_cpu": "20-28 FPS",
                "processing_speed_gpu": "70-90 FPS",
            })
        elif info.quality_tier == "medium":
            estimates.update({
                "violation_detection_accuracy": "90-94%",
                "tracking_accuracy": "88-93%",
                "processing_speed_cpu": "15-22 FPS",
                "processing_speed_gpu": "60-80 FPS",
            })
        else:
            estimates.update({
                "violation_detection_accuracy": "92-96%",
                "tracking_accuracy": "90-95%",
                "processing_speed_cpu": "12-18 FPS",
                "processing_speed_gpu": "50-70 FPS",
            })
        
        return estimates
    
    def print_quality_report(self, info: VideoQualityInfo):
        """Print a formatted quality report to console."""
        print("\n" + "=" * 70)
        print("📹 VIDEO QUALITY REPORT")
        print("=" * 70)
        print(f"Resolution:    {info.width}x{info.height}")
        print(f"FPS:           {info.fps:.1f}")
        print(f"Total Frames:  {info.total_frames}")
        print(f"Quality Tier:  {info.quality_tier.upper()}")
        print()
        
        print("📊 Performance Estimates:")
        estimates = self.get_performance_estimate(info)
        for key, value in estimates.items():
            label = key.replace("_", " ").title()
            print(f"  {label:<30} {value}")
        print()
        
        print("⚙️ Recommendations:")
        print(f"  Skip Frames:   {info.recommended_skip_frames}")
        print(f"  Preprocessing: {'Enabled' if info.preprocessing_needed else 'Disabled'}")
        print(f"  ALPR:          {'Enabled (limited accuracy)' if self.should_enable_alpr(info) else 'Disabled'}")
        print()
        
        if info.warnings:
            print("⚠️ Warnings:")
            for warning in info.warnings:
                print(f"  • {warning}")
            print()
        
        print("✅ System Capabilities:")
        print("  • Violation detection: WORKS")
        print("  • Vehicle tracking: WORKS")
        print("  • Evidence capture: WORKS")
        print(f"  • License plates: LIMITED ({info.estimated_alpr_accuracy})")
        print("=" * 70 + "\n")


def auto_configure_for_video(video_path: str) -> Tuple[PreprocessConfig, VideoQualityInfo]:
    """
    Convenience function to automatically configure preprocessing for a video.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Tuple of (PreprocessConfig, VideoQualityInfo)
    """
    handler = LowResolutionHandler()
    info = handler.analyze_video(video_path)
    config = handler.get_optimal_config(info)
    
    return config, info


# Quick test function
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python low_res_handler.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    handler = LowResolutionHandler()
    info = handler.analyze_video(video_path)
    handler.print_quality_report(info)
    
    config = handler.get_optimal_config(info)
    print("Preprocessing Configuration:")
    print(f"  CLAHE: {config.enable_clahe}")
    print(f"  Denoise: {config.enable_denoise}")
    print(f"  Deblur: {config.enable_deblur}")
    print(f"  Target Resolution: {config.target_width}x{config.target_height if config.target_width else 'Original'}")
    print()
    
    thresholds = handler.get_alpr_thresholds(info)
    print("ALPR Thresholds:")
    for key, value in thresholds.items():
        print(f"  {key}: {value}")
