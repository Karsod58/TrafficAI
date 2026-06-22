"""
BengaluruTrafficAI — Main Pipeline Runner
Wires: Detector → TrackManager → ViolationPipeline → ALPR → EvidenceGenerator

Usage:
    python main.py --source silk_board.mp4 --camera cam_07 --show
    python main.py --source 0              --camera cam_01 --show   # webcam
    python main.py --source rtsp://...     --camera cam_03          # IP cam
"""

import argparse
import logging
import time
from pathlib import Path

from core import (
    TrafficDetector, TrackManager, ROIManager,
    VideoPreprocessor, PreprocessConfig, MultiSourceIngestion,
    RuleEngine, AlertPriority, AlertChannel
)
from core.api_client import APIClient
from violations import ViolationPipeline
from alpr.alpr import ALPRModule
from utils.evidence import EvidenceGenerator


def get_youtube_stream_url(youtube_url: str) -> str:
    """
    Extract direct video stream URL from YouTube using yt-dlp.
    Returns the best quality stream URL that OpenCV can read.
    """
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer MP4 for better OpenCV compatibility
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            stream_url = info['url']
            logger.info(f"YouTube stream extracted: {info.get('title', 'Unknown')}")
            logger.info(f"Resolution: {info.get('width', '?')}x{info.get('height', '?')}")
            return stream_url
            
    except ImportError:
        logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
        raise
    except Exception as e:
        logger.error(f"Failed to extract YouTube stream: {e}")
        raise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")


def build_demo_roi(camera_id: str = "demo") -> ROIManager:
    """
    Default ROI config for demo mode (no JSON file).
    Adjust coordinates to match your actual video resolution.
    For 960x540 videos, uses center 60% of frame for signal box.
    """
    roi = ROIManager(camera_id)
    # Stop line at 70% down from top (works for 960x540 and 1280x720)
    roi.add_stop_line([(50, 380), (910, 380)], name="stop_line_main")
    # No-parking zone on left shoulder
    roi.add_no_parking([(0, 100), (120, 100), (120, 400), (0, 400)], name="no_park_left")
    # Signal box — centre junction area (adjusted for typical intersection)
    # Covers center 60% of frame width, top 30% to 75% of frame height
    roi.add_signal_box([(200, 150), (760, 150), (760, 400), (200, 400)], name="signal_box_main")
    return roi


def run(
    source:      str,
    camera_id:   str  = "cam_01",
    roi_path:    str  = None,
    skip_frames: int  = 2,
    show_live:   bool = False,
    output_path: str  = None,
    max_frames:  int  = None,
    save_evidence: bool = True,
    enable_api:  bool = True,
    enable_preprocessing: bool = True,
    enable_alert_routing: bool = True,
):
    logger.info("=" * 60)
    logger.info("  BengaluruTrafficAI  —  Starting pipeline")
    logger.info(f"  Source:    {source}")
    logger.info(f"  Camera:    {camera_id}")
    logger.info(f"  Skip:      every {skip_frames} frames")
    logger.info(f"  API:       {'enabled' if enable_api else 'disabled'}")
    logger.info(f"  Preproc:   {'enabled' if enable_preprocessing else 'disabled'}")
    logger.info("=" * 60)

    # ── Initialise components ─────────────────────────────────────────────────
    
    # Preprocessing layer with automatic quality detection
    preprocessor = None
    if enable_preprocessing:
        source_normalized, source_type = MultiSourceIngestion.normalize_source(str(source))
        
        # Auto-detect video quality for local files
        if source_type == "file":
            try:
                from core.low_res_handler import LowResolutionHandler
                handler = LowResolutionHandler()
                quality_info = handler.analyze_video(str(source))
                handler.print_quality_report(quality_info)
                preproc_config = handler.get_optimal_config(quality_info)
                logger.info(f"Auto-configured for {quality_info.quality_tier} quality video")
            except Exception as e:
                logger.warning(f"Quality detection failed: {e}, using default config")
                preproc_config = MultiSourceIngestion.get_optimal_config(source_type)
        else:
            preproc_config = MultiSourceIngestion.get_optimal_config(source_type)
        
        preprocessor = VideoPreprocessor(preproc_config)
        logger.info(f"Preprocessing enabled for source type: {source_type}")
    
    # Detection layer
    detector  = TrafficDetector()
    tracks    = TrackManager()

    if roi_path and Path(roi_path).exists():
        roi = ROIManager(camera_id)
        roi.load(roi_path)
    else:
        logger.warning("No ROI file found — using demo ROI (tune coordinates for your video)")
        roi = build_demo_roi(camera_id)

    # Violation detection
    pipeline  = ViolationPipeline(camera_id=camera_id, roi_manager=roi)
    alpr      = ALPRModule()
    ev_gen    = EvidenceGenerator(camera_id=camera_id) if save_evidence else None
    
    # Alert routing
    rule_engine = RuleEngine() if enable_alert_routing else None
    
    # API client
    api_client = None
    if enable_api:
        api_client = APIClient()
        if api_client.health_check():
            logger.info("API client connected and ready")
        else:
            logger.warning("API not reachable - violations will not be synced")
            api_client = None

    # ── Stats ─────────────────────────────────────────────────────────────────
    stats = {
        "frames_processed": 0,
        "frames_skipped": 0,
        "violations_detected": 0,
        "violations_auto_approved": 0,
        "total_inference_ms": 0.0,
        "violation_counts": {},
        "alert_priorities": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    }

    # ── Main loop ─────────────────────────────────────────────────────────────
    for frame_result in detector.process_video(
        source=source,
        skip_frames=skip_frames,
        max_frames=max_frames,
        show_live=show_live,
        output_path=output_path,
    ):
        # Preprocessing layer
        if preprocessor:
            processed_frame, should_process = preprocessor.process(frame_result.annotated_frame)
            if not should_process:
                stats["frames_skipped"] += 1
                continue
            frame_result.annotated_frame = processed_frame
        
        stats["frames_processed"] += 1
        stats["total_inference_ms"] += frame_result.inference_ms

        # Update trajectory tracking
        tracks.update(frame_result.detections)

        # Run violation pipeline
        events = pipeline.run(frame_result, tracks)

        for event in events:
            stats["violations_detected"] += 1
            vtype = event.violation_type.value
            stats["violation_counts"][vtype] = stats["violation_counts"].get(vtype, 0) + 1

            # Run ALPR on the offending vehicle
            if frame_result.annotated_frame is not None:
                vehicle_detections = [
                    d for d in frame_result.detections
                    if d.track_id == event.track_id
                ]
                plate_results = alpr.process_batch(
                    frame_result.annotated_frame, vehicle_detections
                )
                plate = plate_results.get(event.track_id)
                plate_number = plate.plate_number if plate else None
            else:
                plate_number = None

            event.plate_number = plate_number
            
            # Alert routing & rule engine
            alert_action = None
            auto_approve_override = None
            if rule_engine:
                alert_action = rule_engine.evaluate(event.to_dict())
                auto_approve_override = alert_action.auto_approve
                
                # Record for repeat offender tracking
                if plate_number:
                    rule_engine.record_violation(plate_number)
                
                # Update stats
                stats["alert_priorities"][alert_action.priority.value] = \
                    stats["alert_priorities"].get(alert_action.priority.value, 0) + 1
            
            # Use override if available, otherwise use event's property
            final_auto_approve = auto_approve_override if auto_approve_override is not None else event.auto_approve
            if final_auto_approve:
                stats["violations_auto_approved"] += 1

            # Generate evidence package
            evidence_path = None
            if ev_gen and frame_result.annotated_frame is not None:
                annotated = pipeline.annotate_violations(
                    frame_result.annotated_frame, [event]
                )
                evidence_metadata = ev_gen.generate(event, annotated, plate_number=plate_number)
                evidence_path = evidence_metadata.get("image_path")

            # Submit to API (with final auto_approve value)
            if api_client:
                try:
                    # Create payload with override auto_approve if needed
                    event_dict = event.to_dict()
                    if auto_approve_override is not None:
                        event_dict['auto_approve'] = auto_approve_override
                    api_client.queue_violation_dict(event_dict)
                except Exception as e:
                    logger.error(f"API submission error: {e}")

            # Logging
            priority_str = f"priority={alert_action.priority.value}" if alert_action else ""
            logger.info(
                f"  VIOLATION | {event.violation_type.value:<20} | "
                f"plate={plate_number or 'N/A':<14} | "
                f"conf={event.confidence:.2f} | "
                f"auto_approve={final_auto_approve} | "
                f"{priority_str}"
            )

        # Print periodic stats
        if stats["frames_processed"] % 100 == 0:
            avg_ms = stats["total_inference_ms"] / stats["frames_processed"]
            logger.info(
                f"Progress: {stats['frames_processed']} frames | "
                f"skipped: {stats['frames_skipped']} | "
                f"avg inference: {avg_ms:.1f}ms | "
                f"violations: {stats['violations_detected']} | "
                f"active tracks: {tracks.active_count}"
            )

    # Flush any remaining API queue
    if api_client:
        api_client.close()

    # ── Final summary ─────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  PIPELINE COMPLETE")
    logger.info(f"  Frames processed : {stats['frames_processed']}")
    logger.info(f"  Frames skipped   : {stats['frames_skipped']}")
    logger.info(f"  Violations found : {stats['violations_detected']}")
    logger.info(f"  Auto-approved    : {stats['violations_auto_approved']}")
    if stats["frames_processed"]:
        avg = stats["total_inference_ms"] / stats["frames_processed"]
        logger.info(f"  Avg inference    : {avg:.1f} ms/frame")
    
    if enable_alert_routing:
        logger.info("  Alert Priorities:")
        for priority, count in stats["alert_priorities"].items():
            if count > 0:
                logger.info(f"    {priority:<12} : {count}")
    
    logger.info("  Violation Breakdown:")
    for vtype, count in sorted(stats["violation_counts"].items(), key=lambda x: -x[1]):
        logger.info(f"    {vtype:<25} : {count}")
    logger.info("=" * 60)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BengaluruTrafficAI Pipeline")
    parser.add_argument("--source",      default="0",        help="Video file, RTSP URL, YouTube URL, or camera index")
    parser.add_argument("--camera",      default="cam_01",   help="Camera ID for evidence metadata")
    parser.add_argument("--roi",         default=None,       help="Path to ROI JSON config file")
    parser.add_argument("--skip",        default=2, type=int,help="Process every Nth frame")
    parser.add_argument("--show",        action="store_true", help="Display live annotated video")
    parser.add_argument("--output",      default=None,       help="Save annotated video to path")
    parser.add_argument("--max-frames",  default=None, type=int)
    parser.add_argument("--no-evidence", action="store_true", help="Skip evidence file saving")
    parser.add_argument("--no-api",      action="store_true", help="Disable API submission")
    parser.add_argument("--no-preproc",  action="store_true", help="Disable preprocessing")
    parser.add_argument("--no-routing",  action="store_true", help="Disable alert routing")
    args = parser.parse_args()

    source = args.source
    
    # Handle different source types
    if source.isdigit():
        # Webcam index
        source = int(source)
    elif "youtube.com" in source or "youtu.be" in source:
        # YouTube URL - extract stream
        logger.info(f"Extracting YouTube stream from: {source}")
        source = get_youtube_stream_url(source)
    elif source.startswith("http://") or source.startswith("https://"):
        # Direct HTTP/HTTPS stream (non-YouTube)
        logger.info(f"Using direct HTTP stream: {source}")
    elif source.startswith("rtsp://"):
        # RTSP stream
        logger.info(f"Using RTSP stream: {source}")
    else:
        # Local file path
        logger.info(f"Using local video file: {source}")

    run(
        source=source,
        camera_id=args.camera,
        roi_path=args.roi,
        skip_frames=args.skip,
        show_live=args.show,
        output_path=args.output,
        max_frames=args.max_frames,
        save_evidence=not args.no_evidence,
        enable_api=not args.no_api,
        enable_preprocessing=not args.no_preproc,
        enable_alert_routing=not args.no_routing,
    )
