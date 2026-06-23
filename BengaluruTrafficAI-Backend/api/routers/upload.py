"""
Bengaluru Traffic AI - Video Upload & Processing Router
Allows users to upload videos for violation detection

Features:
- Video file upload (MP4, AVI, MOV)
- URL-based video (YouTube, direct links)
- Batch processing
- Processing status tracking
- Results retrieval
"""

import os
import uuid
import logging
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger("router.upload")
router = APIRouter(prefix="/upload", tags=["video-upload"])

# Configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# In-memory job tracking (in production, use Redis or database)
processing_jobs = {}


class VideoURLUpload(BaseModel):
    url: str
    camera_id: str = "upload_cam"
    skip_frames: int = 3
    max_frames: Optional[int] = None


class ProcessingStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0-100
    message: str
    camera_id: str
    video_source: str
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    results: Optional[dict] = None


@router.post("/video")
async def upload_video_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    camera_id: str = Form("upload_cam"),
    skip_frames: int = Form(3),
    max_frames: Optional[int] = Form(None)
):
    """
    Upload a video file for processing.
    
    Accepts: MP4, AVI, MOV, MKV, WEBM
    Max size: 500 MB
    
    Returns: job_id for tracking processing status
    
    Example:
    ```bash
    curl -X POST "http://localhost:8000/upload/video" \
      -F "file=@traffic_video.mp4" \
      -F "camera_id=demo_cam_01" \
      -F "skip_frames=3"
    ```
    """
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())[:8]
        
        # Save uploaded file
        file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)} MB"
            )
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Video uploaded: {file.filename} ({file_size / (1024*1024):.2f} MB) | job_id={job_id}")
        
        # Create job status
        processing_jobs[job_id] = ProcessingStatus(
            job_id=job_id,
            status="pending",
            progress=0,
            message="Video uploaded, queued for processing",
            camera_id=camera_id,
            video_source=file.filename,
            started_at=None
        )
        
        # Start processing in background
        background_tasks.add_task(
            process_video_background,
            job_id=job_id,
            video_path=str(file_path),
            camera_id=camera_id,
            skip_frames=skip_frames,
            max_frames=max_frames
        )
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Video uploaded successfully. Processing started.",
            "video_filename": file.filename,
            "status_url": f"/upload/status/{job_id}"
        }
    
    except Exception as e:
        logger.error(f"Video upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/url")
async def upload_video_url(
    background_tasks: BackgroundTasks,
    upload: VideoURLUpload
):
    """
    Process video from URL (YouTube, direct video link, RTSP).
    
    Example:
    ```json
    {
        "url": "https://youtu.be/VIDEO_ID",
        "camera_id": "youtube_cam",
        "skip_frames": 3,
        "max_frames": 1000
    }
    ```
    
    Returns: job_id for tracking
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())[:8]
        
        # Validate URL
        if not upload.url.startswith(("http://", "https://", "rtsp://")):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        logger.info(f"Video URL submitted: {upload.url} | job_id={job_id}")
        
        # Create job status
        processing_jobs[job_id] = ProcessingStatus(
            job_id=job_id,
            status="pending",
            progress=0,
            message="URL submitted, starting processing",
            camera_id=upload.camera_id,
            video_source=upload.url,
            started_at=None
        )
        
        # Start processing in background
        background_tasks.add_task(
            process_video_background,
            job_id=job_id,
            video_path=upload.url,
            camera_id=upload.camera_id,
            skip_frames=upload.skip_frames,
            max_frames=upload.max_frames
        )
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Video URL submitted. Processing started.",
            "video_url": upload.url,
            "status_url": f"/upload/status/{job_id}"
        }
    
    except Exception as e:
        logger.error(f"Video URL upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_processing_status(job_id: str):
    """
    Get processing status for a job.
    
    Returns current status, progress, and results (if completed).
    
    Status values:
    - pending: Waiting to start
    - processing: Currently processing
    - completed: Finished successfully
    - failed: Error occurred
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    return processing_jobs[job_id]


@router.get("/jobs")
async def list_processing_jobs(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    List all processing jobs.
    
    Query params:
    - status: Filter by status (pending, processing, completed, failed)
    - limit: Max results (default 50)
    """
    jobs = list(processing_jobs.values())
    
    if status:
        jobs = [j for j in jobs if j.status == status]
    
    # Sort by started_at (most recent first)
    jobs.sort(key=lambda x: x.started_at or 0, reverse=True)
    
    return {
        "jobs": jobs[:limit],
        "total": len(jobs)
    }


@router.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a pending or processing job.
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    job = processing_jobs[job_id]
    
    if job.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed job")
    
    # Mark as failed
    job.status = "failed"
    job.message = "Cancelled by user"
    job.completed_at = datetime.now().timestamp()
    
    return {"message": "Job cancelled", "job_id": job_id}


@router.delete("/cleanup")
async def cleanup_completed_jobs():
    """
    Remove completed jobs and uploaded files.
    """
    removed_count = 0
    
    for job_id in list(processing_jobs.keys()):
        job = processing_jobs[job_id]
        
        if job.status in ["completed", "failed"]:
            # Remove uploaded file if exists
            for file in UPLOAD_DIR.glob(f"{job_id}_*"):
                try:
                    file.unlink()
                    logger.info(f"Deleted file: {file}")
                except Exception as e:
                    logger.error(f"Error deleting file {file}: {e}")
            
            # Remove job
            del processing_jobs[job_id]
            removed_count += 1
    
    return {
        "message": f"Cleaned up {removed_count} completed jobs",
        "removed": removed_count
    }


# ─── Background Processing ────────────────────────────────────────────────────

def process_video_background(
    job_id: str,
    video_path: str,
    camera_id: str,
    skip_frames: int,
    max_frames: Optional[int]
):
    """
    Process video in background using main.py pipeline.
    """
    import subprocess
    import sys
    from pathlib import Path
    
    try:
        # Update job status
        processing_jobs[job_id].status = "processing"
        processing_jobs[job_id].progress = 5
        processing_jobs[job_id].message = "Starting violation detection..."
        processing_jobs[job_id].started_at = datetime.now().timestamp()
        
        logger.info(f"Starting processing for job {job_id}")
        
        # Build command — ingest violations into the same API/DB (Railway Postgres)
        python_exe = sys.executable
        main_script = Path(__file__).parent.parent.parent / "main.py"
        api_base = os.getenv("API_BASE_URL") or f"http://127.0.0.1:{os.getenv('PORT', '8000')}"

        cmd = [
            python_exe,
            str(main_script),
            "--source", video_path,
            "--camera", camera_id,
            "--skip", str(skip_frames),
            "--api-url", api_base,
        ]
        
        if max_frames:
            cmd.extend(["--max-frames", str(max_frames)])
        
        # Run processing
        processing_jobs[job_id].progress = 10
        processing_jobs[job_id].message = "Processing video frames..."
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        # Parse results from output
        output = result.stdout
        violations_detected = output.count("VIOLATION")
        
        # Get violation breakdown from output
        violation_counts = {}
        for line in output.split('\n'):
            if ':' in line and any(v in line for v in ['triple_riding', 'red_light', 'wrong_side', 'stop_line', 'illegal_parking']):
                parts = line.strip().split(':')
                if len(parts) == 2:
                    vtype = parts[0].strip()
                    try:
                        count = int(parts[1].strip())
                        violation_counts[vtype] = count
                    except:
                        pass
        
        # Get processing stats
        frames_processed = 0
        avg_inference_ms = 0.0
        for line in output.split('\n'):
            if 'Frames processed' in line:
                try:
                    frames_processed = int(line.split(':')[1].strip())
                except:
                    pass
            if 'Avg inference' in line:
                try:
                    avg_inference_ms = float(line.split(':')[1].replace('ms/frame', '').strip())
                except:
                    pass
        
        if result.returncode == 0:
            processing_jobs[job_id].status = "completed"
            processing_jobs[job_id].progress = 100
            processing_jobs[job_id].message = f"Processing completed! {violations_detected} violations detected."
            processing_jobs[job_id].completed_at = datetime.now().timestamp()
            processing_jobs[job_id].results = {
                "violations_detected": violations_detected,
                "violation_breakdown": violation_counts,
                "frames_processed": frames_processed,
                "avg_inference_ms": avg_inference_ms,
                "camera_id": camera_id,
                "video_source": Path(video_path).name if Path(video_path).exists() else video_path,
                "evidence_url_pattern": f"/evidence/"  # Frontend will construct full URLs
            }
            logger.info(f"Job {job_id} completed successfully: {violations_detected} violations")
        else:
            raise Exception(f"Processing failed: {result.stderr}")
    
    except subprocess.TimeoutExpired:
        processing_jobs[job_id].status = "failed"
        processing_jobs[job_id].message = "Processing timeout (>1 hour)"
        processing_jobs[job_id].completed_at = datetime.now().timestamp()
        logger.error(f"Job {job_id} timed out")
    
    except Exception as e:
        processing_jobs[job_id].status = "failed"
        processing_jobs[job_id].message = f"Error: {str(e)}"
        processing_jobs[job_id].completed_at = datetime.now().timestamp()
        logger.error(f"Job {job_id} failed: {e}")
