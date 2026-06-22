"""
BengaluruTrafficAI — Batch Video Processor
Handles large video files efficiently by processing in chunks

Features:
- Process videos in configurable batch sizes
- Progress tracking and ETA calculation
- Memory-efficient frame iteration
- Resume capability from last processed frame
- Automatic cleanup of temporary files
"""

import cv2
import logging
import time
from pathlib import Path
from typing import Iterator, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger("batch_processor")


@dataclass
class BatchConfig:
    """Configuration for batch video processing."""
    batch_size: int = 100  # Frames per batch
    skip_frames: int = 3   # Process every Nth frame
    max_frames: Optional[int] = None  # Limit total frames (None = process all)
    save_progress: bool = True  # Save progress for resume
    checkpoint_interval: int = 500  # Save checkpoint every N frames


@dataclass
class ProcessingProgress:
    """Track processing progress."""
    total_frames: int
    processed_frames: int
    current_frame: int
    start_time: float
    batches_completed: int
    violations_detected: int
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_frames == 0:
            return 0.0
        return (self.processed_frames / self.total_frames) * 100
    
    @property
    def eta_seconds(self) -> float:
        """Estimate time remaining in seconds."""
        if self.processed_frames == 0:
            return 0.0
        
        elapsed = time.time() - self.start_time
        frames_per_sec = self.processed_frames / elapsed
        remaining_frames = self.total_frames - self.processed_frames
        
        return remaining_frames / frames_per_sec if frames_per_sec > 0 else 0.0
    
    @property
    def fps(self) -> float:
        """Calculate processing speed (frames per second)."""
        if self.processed_frames == 0:
            return 0.0
        
        elapsed = time.time() - self.start_time
        return self.processed_frames / elapsed if elapsed > 0 else 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "total_frames": self.total_frames,
            "processed_frames": self.processed_frames,
            "current_frame": self.current_frame,
            "progress_percent": round(self.progress_percent, 2),
            "eta_seconds": round(self.eta_seconds, 1),
            "fps": round(self.fps, 2),
            "batches_completed": self.batches_completed,
            "violations_detected": self.violations_detected,
        }


class BatchVideoProcessor:
    """
    Process large videos in batches to reduce memory usage and improve performance.
    
    Usage:
        processor = BatchVideoProcessor("video.mp4", config=BatchConfig(batch_size=100))
        
        for batch_frames, batch_info in processor.process_batches():
            # Process each batch
            for frame_idx, frame in batch_frames:
                result = detector.process_frame(frame)
                # Handle result
            
            # Update progress
            processor.update_progress(violations_count=5)
            print(f"Progress: {processor.progress.progress_percent:.1f}%")
    """
    
    def __init__(
        self,
        video_source: str,
        config: Optional[BatchConfig] = None,
        resume_from: int = 0
    ):
        """
        Initialize batch processor.
        
        Args:
            video_source: Path to video file or stream URL
            config: Batch processing configuration
            resume_from: Frame number to resume from (for interrupted processing)
        """
        self.video_source = video_source
        self.config = config or BatchConfig()
        self.resume_from = resume_from
        
        # Open video capture
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {video_source}")
        
        # Get video properties
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Apply max_frames limit if set
        if self.config.max_frames:
            self.total_frames = min(self.total_frames, self.config.max_frames)
        
        # Calculate actual frames to process (considering skip_frames)
        self.frames_to_process = self.total_frames // (self.config.skip_frames + 1)
        
        # Initialize progress tracker
        self.progress = ProcessingProgress(
            total_frames=self.frames_to_process,
            processed_frames=0,
            current_frame=resume_from,
            start_time=time.time(),
            batches_completed=0,
            violations_detected=0,
        )
        
        # Seek to resume position if needed
        if resume_from > 0:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, resume_from)
            logger.info(f"Resuming from frame {resume_from}")
        
        logger.info(f"Video: {self.width}x{self.height} @ {self.fps:.1f}fps")
        logger.info(f"Total frames: {self.total_frames}, Will process: {self.frames_to_process}")
        logger.info(f"Batch size: {self.config.batch_size}, Skip: {self.config.skip_frames}")
    
    def process_batches(self) -> Iterator[Tuple[list, dict]]:
        """
        Generator that yields batches of frames for processing.
        
        Yields:
            Tuple of (batch_frames, batch_info)
            - batch_frames: List of (frame_idx, frame_array) tuples
            - batch_info: Dictionary with batch metadata
        """
        batch_frames = []
        batch_start_idx = self.progress.current_frame
        
        frame_idx = self.progress.current_frame
        frames_read = 0
        
        while frame_idx < self.total_frames:
            # Read frame
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning(f"Failed to read frame {frame_idx}")
                break
            
            # Skip frames if configured
            if frames_read % (self.config.skip_frames + 1) != 0:
                frame_idx += 1
                frames_read += 1
                continue
            
            # Add to current batch
            batch_frames.append((frame_idx, frame))
            frame_idx += 1
            frames_read += 1
            
            # Yield batch when full or at end
            if len(batch_frames) >= self.config.batch_size or frame_idx >= self.total_frames:
                batch_info = {
                    "batch_number": self.progress.batches_completed + 1,
                    "batch_start_frame": batch_start_idx,
                    "batch_end_frame": frame_idx - 1,
                    "batch_size": len(batch_frames),
                    "progress": self.progress.to_dict(),
                }
                
                yield batch_frames, batch_info
                
                # Reset for next batch
                batch_frames = []
                batch_start_idx = frame_idx
        
        # Yield any remaining frames
        if batch_frames:
            batch_info = {
                "batch_number": self.progress.batches_completed + 1,
                "batch_start_frame": batch_start_idx,
                "batch_end_frame": frame_idx - 1,
                "batch_size": len(batch_frames),
                "progress": self.progress.to_dict(),
            }
            yield batch_frames, batch_info
    
    def update_progress(self, frames_processed: int = 1, violations_count: int = 0):
        """
        Update processing progress.
        
        Args:
            frames_processed: Number of frames processed in this update
            violations_count: Number of violations detected in this update
        """
        self.progress.processed_frames += frames_processed
        self.progress.current_frame += frames_processed * (self.config.skip_frames + 1)
        self.progress.violations_detected += violations_count
        
        # Log progress periodically
        if self.progress.processed_frames % 100 == 0:
            logger.info(
                f"Progress: {self.progress.progress_percent:.1f}% "
                f"({self.progress.processed_frames}/{self.frames_to_process} frames) | "
                f"Speed: {self.progress.fps:.1f} fps | "
                f"ETA: {self.progress.eta_seconds/60:.1f}min | "
                f"Violations: {self.progress.violations_detected}"
            )
    
    def complete_batch(self):
        """Mark current batch as completed."""
        self.progress.batches_completed += 1
    
    def get_progress(self) -> dict:
        """Get current progress as dictionary."""
        return self.progress.to_dict()
    
    def cleanup(self):
        """Release video capture and cleanup resources."""
        if self.cap:
            self.cap.release()
            logger.info("Video capture released")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.cleanup()


class BatchProgressCallback:
    """Callback handler for batch processing progress updates."""
    
    def __init__(self, callback_fn=None):
        """
        Initialize callback.
        
        Args:
            callback_fn: Function to call with progress updates
                        Signature: callback_fn(progress_dict: dict)
        """
        self.callback_fn = callback_fn
    
    def on_batch_complete(self, batch_info: dict):
        """Called when a batch completes processing."""
        if self.callback_fn:
            self.callback_fn({
                "event": "batch_complete",
                "data": batch_info
            })
    
    def on_progress_update(self, progress: dict):
        """Called on progress updates."""
        if self.callback_fn:
            self.callback_fn({
                "event": "progress_update",
                "data": progress
            })
    
    def on_error(self, error: Exception):
        """Called when an error occurs."""
        if self.callback_fn:
            self.callback_fn({
                "event": "error",
                "data": {"error": str(error)}
            })
    
    def on_complete(self, summary: dict):
        """Called when processing completes."""
        if self.callback_fn:
            self.callback_fn({
                "event": "complete",
                "data": summary
            })


# ── Utility Functions ──────────────────────────────────────────────────────────

def estimate_video_memory(video_path: str, batch_size: int = 100) -> dict:
    """
    Estimate memory requirements for batch processing.
    
    Args:
        video_path: Path to video file
        batch_size: Number of frames per batch
    
    Returns:
        Dictionary with memory estimates in MB
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return {"error": "Cannot open video"}
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    cap.release()
    
    # Calculate memory per frame (3 channels, 8 bits per channel)
    bytes_per_frame = width * height * 3
    mb_per_frame = bytes_per_frame / (1024 * 1024)
    
    # Batch memory (including overhead for processing)
    batch_memory_mb = mb_per_frame * batch_size * 1.5  # 1.5x for overhead
    
    # Total video memory (if loaded entirely)
    total_memory_mb = mb_per_frame * total_frames
    
    return {
        "frame_size_mb": round(mb_per_frame, 2),
        "batch_memory_mb": round(batch_memory_mb, 2),
        "total_video_mb": round(total_memory_mb, 2),
        "recommended_batch_size": int(500 / mb_per_frame),  # Target 500MB per batch
        "video_info": {
            "width": width,
            "height": height,
            "total_frames": total_frames,
        }
    }


def optimize_batch_size(video_path: str, available_memory_mb: int = 2048) -> int:
    """
    Calculate optimal batch size based on available memory.
    
    Args:
        video_path: Path to video file
        available_memory_mb: Available system memory in MB
    
    Returns:
        Recommended batch size
    """
    estimates = estimate_video_memory(video_path)
    
    if "error" in estimates:
        return 50  # Default fallback
    
    frame_size_mb = estimates["frame_size_mb"]
    
    # Use 70% of available memory for batch
    usable_memory = available_memory_mb * 0.7
    
    # Calculate batch size with overhead
    batch_size = int(usable_memory / (frame_size_mb * 1.5))
    
    # Clamp between reasonable values
    return max(10, min(batch_size, 500))
