"""
BengaluruTrafficAI — Roboflow Dataset Management
Streamlined dataset creation, labeling, and versioning

Features:
- Download annotated datasets
- Upload images for labeling
- Version management
- Augmentation pipelines
- Train/val/test splits
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict
from roboflow import Roboflow

logger = logging.getLogger("roboflow")


class RoboflowDatasetManager:
    """
    Manages datasets through Roboflow platform.
    
    Usage:
        manager = RoboflowDatasetManager(api_key="your_key")
        dataset = manager.download_dataset(
            workspace="bengaluru-traffic",
            project="violations-v2",
            version=3
        )
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        
        if not self.api_key:
            logger.warning("ROBOFLOW_API_KEY not set. Dataset operations will fail.")
            self.rf = None
        else:
            self.rf = Roboflow(api_key=self.api_key)
            logger.info("Roboflow client initialized")
    
    def download_dataset(
        self,
        workspace: str,
        project: str,
        version: int,
        format: str = "yolov8",
        download_path: str = "./datasets",
        overwrite: bool = False,
    ) -> Dict:
        """
        Download dataset from Roboflow.
        
        Args:
            workspace: Roboflow workspace name
            project: Project name
            version: Dataset version number
            format: Export format ('yolov8', 'yolov11', 'coco', 'voc')
            download_path: Local download directory
            overwrite: Whether to re-download if exists
        
        Returns:
            Dataset info dict with 'location', 'yaml_path', 'classes'
        """
        if not self.rf:
            raise ValueError("Roboflow API key not configured")
        
        logger.info(f"Downloading {workspace}/{project} v{version}")
        
        try:
            project_obj = self.rf.workspace(workspace).project(project)
            dataset = project_obj.version(version).download(
                format,
                location=download_path,
                overwrite=overwrite
            )
            
            # Parse dataset info
            yaml_path = Path(dataset.location) / "data.yaml"
            
            info = {
                "location": dataset.location,
                "yaml_path": str(yaml_path),
                "workspace": workspace,
                "project": project,
                "version": version,
            }
            
            logger.info(f"Dataset downloaded to: {dataset.location}")
            return info
        
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    def upload_for_labeling(
        self,
        images_path: str,
        workspace: str,
        project: str,
        batch_name: Optional[str] = None
    ):
        """
        Upload unlabeled images to Roboflow for annotation.
        
        Args:
            images_path: Path to folder with images
            workspace: Roboflow workspace
            project: Project name
            batch_name: Optional batch identifier
        """
        if not self.rf:
            raise ValueError("Roboflow API key not configured")
        
        images_path = Path(images_path)
        if not images_path.exists():
            raise FileNotFoundError(f"Images path not found: {images_path}")
        
        logger.info(f"Uploading images from {images_path}")
        
        try:
            project_obj = self.rf.workspace(workspace).project(project)
            
            # Upload all images in folder
            image_files = list(images_path.glob("*.jpg")) + \
                         list(images_path.glob("*.png"))
            
            for img_path in image_files:
                project_obj.upload(
                    str(img_path),
                    batch_name=batch_name,
                    tag_names=["unlabeled"]
                )
            
            logger.info(f"Uploaded {len(image_files)} images")
        
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
    
    def create_project(
        self,
        workspace: str,
        project_name: str,
        project_type: str = "object-detection",
        annotation_type: str = "bounding-box"
    ):
        """
        Create a new Roboflow project.
        
        Args:
            workspace: Workspace name
            project_name: New project name
            project_type: 'object-detection', 'classification', 'segmentation'
            annotation_type: 'bounding-box', 'polygon', 'semantic'
        """
        if not self.rf:
            raise ValueError("Roboflow API key not configured")
        
        try:
            workspace_obj = self.rf.workspace(workspace)
            project = workspace_obj.create_project(
                project_name=project_name,
                project_type=project_type,
                annotation=annotation_type
            )
            
            logger.info(f"Created project: {project_name}")
            return project
        
        except Exception as e:
            logger.error(f"Project creation failed: {e}")
            raise
    
    def list_projects(self, workspace: str):
        """List all projects in workspace"""
        if not self.rf:
            raise ValueError("Roboflow API key not configured")
        
        workspace_obj = self.rf.workspace(workspace)
        projects = workspace_obj.projects()
        
        for proj in projects:
            logger.info(f"  - {proj['name']} ({proj['id']})")
        
        return projects
    
    def get_project_stats(self, workspace: str, project: str):
        """Get project statistics"""
        if not self.rf:
            raise ValueError("Roboflow API key not configured")
        
        project_obj = self.rf.workspace(workspace).project(project)
        
        # Get latest version stats
        versions = project_obj.versions()
        if versions:
            latest = versions[-1]
            logger.info(f"Latest version: v{latest['id']}")
            logger.info(f"  Images: {latest.get('images', 0)}")
            logger.info(f"  Classes: {latest.get('classes', [])}")
        
        return versions


# Example usage
if __name__ == "__main__":
    # Set API key in environment:
    # export ROBOFLOW_API_KEY="your_key_here"
    
    manager = RoboflowDatasetManager()
    
    # Download dataset
    dataset = manager.download_dataset(
        workspace="bengaluru-traffic",
        project="traffic-violations",
        version=2
    )
    
    print(f"Dataset ready at: {dataset['yaml_path']}")
    
    # Train YOLO11 with downloaded dataset
    from ultralytics import YOLO
    model = YOLO('yolo11s.pt')
    
    model.train(
        data=dataset['yaml_path'],
        epochs=100,
        imgsz=640,
        batch=16,
        device=0,  # GTX 1650
        project="bengaluru_traffic_models",
        name="yolo11s_violations_v2"
    )
