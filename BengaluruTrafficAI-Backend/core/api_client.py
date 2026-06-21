"""
BengaluruTrafficAI — API Client
Integration module: CV pipeline → FastAPI backend

Handles:
- Violation ingestion (POST to /violations/ingest)
- Camera status updates
- Retry logic with exponential backoff
- Async batch submission
"""

import requests
import logging
import time
from typing import Optional, Dict, List
from dataclasses import asdict
from violations.base import ViolationEvent

logger = logging.getLogger("api_client")


class APIClient:
    """
    Client for sending violations from CV pipeline to API backend.
    
    Usage:
        client = APIClient("http://localhost:8000")
        client.submit_violation(violation_event)
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 5,
        max_retries: int = 3,
        batch_size: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.session = requests.Session()
        self.batch_queue: List[Dict] = []
        
        # Test connection
        try:
            response = self.session.get(f"{self.base_url}/", timeout=2)
            if response.status_code == 200:
                logger.info(f"API client connected: {self.base_url}")
            else:
                logger.warning(f"API returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to API: {e}")
    
    def submit_violation(self, event: ViolationEvent) -> bool:
        """
        Submit a single violation to the API.
        
        Returns:
            True if submission successful, False otherwise
        """
        payload = self._event_to_payload(event)
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    f"{self.base_url}/violations/ingest",
                    json=payload,
                    timeout=self.timeout,
                )
                
                if response.status_code == 201:
                    logger.info(f"Violation ingested: {event.event_id} | {event.violation_type.value}")
                    return True
                elif response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "duplicate":
                        logger.debug(f"Duplicate violation: {event.event_id}")
                        return True
                else:
                    logger.error(f"API returned {response.status_code}: {response.text}")
            
            except requests.exceptions.Timeout:
                logger.warning(f"API timeout (attempt {attempt + 1}/{self.max_retries})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"API connection error (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                logger.error(f"API submission error: {e}")
            
            # Exponential backoff
            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)
        
        logger.error(f"Failed to submit violation after {self.max_retries} attempts: {event.event_id}")
        return False
    
    def submit_batch(self, events: List[ViolationEvent]) -> Dict[str, int]:
        """
        Submit multiple violations in batch.
        
        Returns:
            {"success": count, "failed": count}
        """
        results = {"success": 0, "failed": 0}
        
        for event in events:
            if self.submit_violation(event):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def queue_violation(self, event: ViolationEvent):
        """
        Add violation to batch queue.
        Automatically submits when batch_size is reached.
        """
        payload = self._event_to_payload(event)
        self.batch_queue.append(payload)
        
        if len(self.batch_queue) >= self.batch_size:
            self.flush_queue()
    
    def queue_violation_dict(self, event_dict: dict):
        """
        Add violation from dictionary to batch queue (allows overrides).
        Automatically submits when batch_size is reached.
        """
        self.batch_queue.append(event_dict)
        
        if len(self.batch_queue) >= self.batch_size:
            self.flush_queue()
    
    def flush_queue(self):
        """Submit all queued violations"""
        if not self.batch_queue:
            return
        
        logger.info(f"Flushing batch queue: {len(self.batch_queue)} violations")
        
        # Submit individually (could be optimized with bulk endpoint)
        for payload in self.batch_queue:
            try:
                self.session.post(
                    f"{self.base_url}/violations/ingest",
                    json=payload,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.error(f"Batch submission error: {e}")
        
        self.batch_queue.clear()
    
    def update_camera_status(self, camera_id: str, status: str):
        """
        Send camera status update.
        
        Args:
            camera_id: Camera identifier
            status: "online", "offline", "error"
        """
        try:
            # Future endpoint: POST /cameras/{camera_id}/status
            logger.debug(f"Camera status: {camera_id} -> {status}")
        except Exception as e:
            logger.error(f"Camera status update error: {e}")
    
    def _event_to_payload(self, event: ViolationEvent) -> Dict:
        """Convert ViolationEvent to API payload format"""
        return {
            "event_id": event.event_id,
            "violation_type": event.violation_type.value,
            "camera_id": event.camera_id,
            "track_id": event.track_id,
            "plate_number": event.plate_number,
            "confidence": round(event.confidence, 3),
            "severity": event.severity,
            "fine_inr": event.fine_inr,
            "auto_approve": event.auto_approve,
            "frame_idx": event.frame_idx,
            "timestamp": event.timestamp,
            "bbox": list(event.bbox) if event.bbox else None,
            "image_path": event.evidence_frame is not None,  # Simplified
        }
    
    def health_check(self) -> bool:
        """Check if API is reachable"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def close(self):
        """Close the session and flush any remaining queue"""
        self.flush_queue()
        self.session.close()
        logger.info("API client closed")
