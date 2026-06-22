"""
BengaluruTrafficAI — Performance Evaluation Module
Tracks and evaluates system performance using standard ML metrics

Metrics Tracked:
- Accuracy: Overall correctness
- Precision: True Positives / (True Positives + False Positives)
- Recall: True Positives / (True Positives + False Negatives)
- F1-Score: Harmonic mean of Precision and Recall
- mAP (mean Average Precision): For object detection quality
- Processing Speed: FPS, latency
- System Efficiency: CPU, Memory, GPU usage
"""

import time
import logging
import psutil
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger("performance_evaluator")


@dataclass
class DetectionMetrics:
    """Metrics for a single detection evaluation."""
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    
    @property
    def accuracy(self) -> float:
        """Accuracy = (TP + TN) / (TP + TN + FP + FN)"""
        total = self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total
    
    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP)"""
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator
    
    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)"""
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator
    
    @property
    def f1_score(self) -> float:
        """F1 = 2 * (Precision * Recall) / (Precision + Recall)"""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)
    
    @property
    def specificity(self) -> float:
        """Specificity = TN / (TN + FP)"""
        denominator = self.true_negatives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_negatives / denominator
    
    def to_dict(self) -> dict:
        """Convert to dictionary with calculated metrics."""
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "specificity": round(self.specificity, 4),
        }


@dataclass
class PerformanceMetrics:
    """System performance and efficiency metrics."""
    total_frames_processed: int = 0
    total_violations_detected: int = 0
    processing_time_seconds: float = 0.0
    
    # Per violation type
    violation_counts: Dict[str, int] = None
    
    # Speed metrics
    avg_fps: float = 0.0
    avg_latency_ms: float = 0.0
    
    # Resource usage
    avg_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    avg_gpu_percent: float = 0.0
    
    def __post_init__(self):
        if self.violation_counts is None:
            self.violation_counts = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_frames_processed": self.total_frames_processed,
            "total_violations_detected": self.total_violations_detected,
            "processing_time_seconds": round(self.processing_time_seconds, 2),
            "violation_counts": self.violation_counts,
            "avg_fps": round(self.avg_fps, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_cpu_percent": round(self.avg_cpu_percent, 2),
            "avg_memory_mb": round(self.avg_memory_mb, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "avg_gpu_percent": round(self.avg_gpu_percent, 2),
        }


@dataclass
class mAPMetrics:
    """Mean Average Precision metrics for object detection."""
    ap_per_class: Dict[str, float]  # Average Precision per class
    map_50: float  # mAP at IoU=0.5
    map_75: float  # mAP at IoU=0.75
    map_50_95: float  # mAP at IoU=0.5:0.95
    
    def to_dict(self) -> dict:
        return {
            "ap_per_class": {k: round(v, 4) for k, v in self.ap_per_class.items()},
            "map_50": round(self.map_50, 4),
            "map_75": round(self.map_75, 4),
            "map_50_95": round(self.map_50_95, 4),
        }


class PerformanceEvaluator:
    """
    Comprehensive performance evaluation for traffic violation detection.
    
    Tracks:
    - Detection accuracy (TP, FP, TN, FN)
    - Classification metrics (Precision, Recall, F1)
    - Object detection quality (mAP)
    - System efficiency (CPU, Memory, FPS)
    
    Usage:
        evaluator = PerformanceEvaluator()
        
        # Start evaluation
        evaluator.start_evaluation()
        
        # Process frames
        for frame in frames:
            evaluator.start_frame()
            
            detections = detector.detect(frame)
            ground_truth = load_ground_truth(frame_id)
            
            # Evaluate detections
            evaluator.evaluate_detections(detections, ground_truth)
            
            evaluator.end_frame()
        
        # Get results
        report = evaluator.generate_report()
        evaluator.save_report("evaluation_results.json")
    """
    
    def __init__(self, output_dir: str = "evaluation_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Metrics per violation type
        self.metrics_per_type: Dict[str, DetectionMetrics] = defaultdict(DetectionMetrics)
        
        # Overall metrics
        self.overall_metrics = DetectionMetrics()
        
        # Performance metrics
        self.performance = PerformanceMetrics()
        
        # Timing
        self.start_time: Optional[float] = None
        self.frame_start_time: Optional[float] = None
        self.frame_times: List[float] = []
        
        # Resource tracking
        self.cpu_samples: List[float] = []
        self.memory_samples: List[float] = []
        self.gpu_samples: List[float] = []
        
        # Detection history for mAP calculation
        self.detection_history: List[Tuple[List, List]] = []  # (predictions, ground_truth)
        
        logger.info("Performance Evaluator initialized")
    
    def start_evaluation(self):
        """Start timing the evaluation."""
        self.start_time = time.time()
        logger.info("Evaluation started")
    
    def start_frame(self):
        """Mark start of frame processing."""
        self.frame_start_time = time.time()
        
        # Sample resource usage
        self._sample_resources()
    
    def end_frame(self):
        """Mark end of frame processing."""
        if self.frame_start_time:
            frame_time = time.time() - self.frame_start_time
            self.frame_times.append(frame_time)
            self.performance.total_frames_processed += 1
    
    def evaluate_detections(
        self,
        predictions: List[dict],
        ground_truth: List[dict],
        iou_threshold: float = 0.5
    ):
        """
        Evaluate predictions against ground truth.
        
        Args:
            predictions: List of predicted violations with format:
                [{"type": "no_helmet", "bbox": [x1,y1,x2,y2], "confidence": 0.9}, ...]
            ground_truth: List of ground truth violations with same format
            iou_threshold: IoU threshold for matching (default 0.5)
        """
        # Store for mAP calculation
        self.detection_history.append((predictions, ground_truth))
        
        # Match predictions to ground truth using IoU
        matched_gt = set()
        matched_pred = set()
        
        for i, pred in enumerate(predictions):
            best_iou = 0
            best_gt_idx = -1
            
            for j, gt in enumerate(ground_truth):
                if j in matched_gt:
                    continue
                
                # Check if same violation type
                if pred["type"] != gt["type"]:
                    continue
                
                # Calculate IoU
                iou = self._calculate_iou(pred["bbox"], gt["bbox"])
                
                if iou > best_iou and iou >= iou_threshold:
                    best_iou = iou
                    best_gt_idx = j
            
            if best_gt_idx >= 0:
                # True Positive
                violation_type = pred["type"]
                self.metrics_per_type[violation_type].true_positives += 1
                self.overall_metrics.true_positives += 1
                matched_gt.add(best_gt_idx)
                matched_pred.add(i)
                
                # Count violation
                self.performance.total_violations_detected += 1
                self.performance.violation_counts[violation_type] = \
                    self.performance.violation_counts.get(violation_type, 0) + 1
        
        # False Positives (predictions not matched)
        for i, pred in enumerate(predictions):
            if i not in matched_pred:
                violation_type = pred["type"]
                self.metrics_per_type[violation_type].false_positives += 1
                self.overall_metrics.false_positives += 1
        
        # False Negatives (ground truth not matched)
        for j, gt in enumerate(ground_truth):
            if j not in matched_gt:
                violation_type = gt["type"]
                self.metrics_per_type[violation_type].false_negatives += 1
                self.overall_metrics.false_negatives += 1
        
        # True Negatives (frames with no violations correctly identified)
        if len(predictions) == 0 and len(ground_truth) == 0:
            self.overall_metrics.true_negatives += 1
    
    def calculate_map(self, iou_thresholds: List[float] = None) -> mAPMetrics:
        """
        Calculate mAP (mean Average Precision) across all detections.
        
        Args:
            iou_thresholds: List of IoU thresholds (default: [0.5, 0.75, 0.5:0.95])
        
        Returns:
            mAPMetrics object with AP per class and mAP values
        """
        if iou_thresholds is None:
            iou_thresholds = [0.5, 0.75] + [i/100 for i in range(50, 100, 5)]
        
        # Calculate AP per class and IoU threshold
        ap_results = defaultdict(list)
        
        # Get unique violation types
        all_types = set()
        for preds, gts in self.detection_history:
            for p in preds:
                all_types.add(p["type"])
            for g in gts:
                all_types.add(g["type"])
        
        # Calculate AP for each class at each IoU threshold
        for violation_type in all_types:
            for iou_thresh in iou_thresholds:
                ap = self._calculate_average_precision(violation_type, iou_thresh)
                ap_results[violation_type].append(ap)
        
        # Calculate mean AP per class (averaged across IoU thresholds)
        ap_per_class = {
            vtype: sum(aps) / len(aps) if aps else 0.0
            for vtype, aps in ap_results.items()
        }
        
        # Calculate mAP@0.5
        map_50 = self._calculate_map_at_iou(0.5, all_types)
        
        # Calculate mAP@0.75
        map_75 = self._calculate_map_at_iou(0.75, all_types)
        
        # Calculate mAP@0.5:0.95
        map_50_95 = sum(ap_per_class.values()) / len(ap_per_class) if ap_per_class else 0.0
        
        return mAPMetrics(
            ap_per_class=ap_per_class,
            map_50=map_50,
            map_75=map_75,
            map_50_95=map_50_95
        )
    
    def generate_report(self) -> dict:
        """
        Generate comprehensive evaluation report.
        
        Returns:
            Dictionary with all metrics and analysis
        """
        # Calculate timing metrics
        if self.start_time:
            self.performance.processing_time_seconds = time.time() - self.start_time
        
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.performance.avg_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
            self.performance.avg_latency_ms = avg_frame_time * 1000
        
        # Calculate resource metrics
        if self.cpu_samples:
            self.performance.avg_cpu_percent = sum(self.cpu_samples) / len(self.cpu_samples)
        
        if self.memory_samples:
            self.performance.avg_memory_mb = sum(self.memory_samples) / len(self.memory_samples)
            self.performance.peak_memory_mb = max(self.memory_samples)
        
        if self.gpu_samples:
            self.performance.avg_gpu_percent = sum(self.gpu_samples) / len(self.gpu_samples)
        
        # Calculate mAP
        map_metrics = self.calculate_map()
        
        # Build report
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_metrics": self.overall_metrics.to_dict(),
            "metrics_per_violation_type": {
                vtype: metrics.to_dict()
                for vtype, metrics in self.metrics_per_type.items()
            },
            "map_metrics": map_metrics.to_dict(),
            "performance": self.performance.to_dict(),
            "summary": self._generate_summary(),
        }
        
        return report
    
    def save_report(self, filename: str = None):
        """
        Save evaluation report to JSON file.
        
        Args:
            filename: Output filename (default: evaluation_TIMESTAMP.json)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        report = self.generate_report()
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Evaluation report saved to: {filepath}")
        
        # Also save human-readable summary
        summary_file = filepath.with_suffix('.txt')
        self._save_summary_text(report, summary_file)
        
        return filepath
    
    # ── Internal Methods ──────────────────────────────────────────────────────
    
    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Calculate Intersection over Union between two bounding boxes."""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union
        bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        bbox2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = bbox1_area + bbox2_area - intersection_area
        
        if union_area == 0:
            return 0.0
        
        return intersection_area / union_area
    
    def _calculate_average_precision(self, violation_type: str, iou_threshold: float) -> float:
        """Calculate Average Precision for a specific class at given IoU threshold."""
        # Collect all predictions and ground truths for this class
        all_preds = []
        all_gts = []
        
        for preds, gts in self.detection_history:
            for p in preds:
                if p["type"] == violation_type:
                    all_preds.append(p)
            for g in gts:
                if g["type"] == violation_type:
                    all_gts.append(g)
        
        if not all_preds or not all_gts:
            return 0.0
        
        # Sort predictions by confidence (descending)
        all_preds = sorted(all_preds, key=lambda x: x.get("confidence", 1.0), reverse=True)
        
        # Calculate precision-recall curve
        tp = 0
        fp = 0
        matched_gts = set()
        precisions = []
        recalls = []
        
        for pred in all_preds:
            matched = False
            best_iou = 0
            best_gt_idx = -1
            
            for idx, gt in enumerate(all_gts):
                if idx in matched_gts:
                    continue
                
                iou = self._calculate_iou(pred["bbox"], gt["bbox"])
                if iou >= iou_threshold and iou > best_iou:
                    best_iou = iou
                    best_gt_idx = idx
                    matched = True
            
            if matched:
                tp += 1
                matched_gts.add(best_gt_idx)
            else:
                fp += 1
            
            precision = tp / (tp + fp)
            recall = tp / len(all_gts)
            
            precisions.append(precision)
            recalls.append(recall)
        
        # Calculate AP using 11-point interpolation
        ap = 0.0
        for t in [i/10.0 for i in range(11)]:
            if sum(r >= t for r in recalls) == 0:
                p = 0
            else:
                p = max([precisions[i] for i, r in enumerate(recalls) if r >= t])
            ap += p / 11.0
        
        return ap
    
    def _calculate_map_at_iou(self, iou_threshold: float, violation_types: set) -> float:
        """Calculate mAP at specific IoU threshold."""
        aps = []
        for vtype in violation_types:
            ap = self._calculate_average_precision(vtype, iou_threshold)
            aps.append(ap)
        
        return sum(aps) / len(aps) if aps else 0.0
    
    def _sample_resources(self):
        """Sample current CPU and memory usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_samples.append(cpu_percent)
            
            # Memory usage
            memory_info = psutil.Process().memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            self.memory_samples.append(memory_mb)
            
            # GPU usage (if available)
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_percent = torch.cuda.utilization()
                    self.gpu_samples.append(gpu_percent)
            except:
                pass
        except Exception as e:
            logger.debug(f"Resource sampling error: {e}")
    
    def _generate_summary(self) -> dict:
        """Generate human-readable summary of results."""
        overall = self.overall_metrics
        perf = self.performance
        
        return {
            "detection_quality": {
                "overall_accuracy": f"{overall.accuracy * 100:.2f}%",
                "precision": f"{overall.precision * 100:.2f}%",
                "recall": f"{overall.recall * 100:.2f}%",
                "f1_score": f"{overall.f1_score * 100:.2f}%",
                "grade": self._get_performance_grade(overall.f1_score),
            },
            "system_efficiency": {
                "processing_speed": f"{perf.avg_fps:.2f} FPS",
                "avg_latency": f"{perf.avg_latency_ms:.2f} ms",
                "cpu_usage": f"{perf.avg_cpu_percent:.1f}%",
                "memory_usage": f"{perf.avg_memory_mb:.1f} MB",
                "scalability": self._assess_scalability(perf),
            },
            "throughput": {
                "frames_processed": perf.total_frames_processed,
                "violations_detected": perf.total_violations_detected,
                "processing_time": f"{perf.processing_time_seconds:.2f} seconds",
            }
        }
    
    def _get_performance_grade(self, f1_score: float) -> str:
        """Assign performance grade based on F1-score."""
        if f1_score >= 0.90:
            return "Excellent (A)"
        elif f1_score >= 0.80:
            return "Good (B)"
        elif f1_score >= 0.70:
            return "Satisfactory (C)"
        elif f1_score >= 0.60:
            return "Needs Improvement (D)"
        else:
            return "Poor (F)"
    
    def _assess_scalability(self, perf: PerformanceMetrics) -> str:
        """Assess system scalability based on resource usage."""
        if perf.avg_cpu_percent < 50 and perf.avg_memory_mb < 2000 and perf.avg_fps > 20:
            return "Excellent - Can handle multiple streams"
        elif perf.avg_cpu_percent < 70 and perf.avg_memory_mb < 4000 and perf.avg_fps > 15:
            return "Good - Can handle 2-4 streams"
        elif perf.avg_cpu_percent < 85 and perf.avg_fps > 10:
            return "Moderate - Single stream recommended"
        else:
            return "Limited - Optimization needed"
    
    def _save_summary_text(self, report: dict, filepath: Path):
        """Save human-readable summary to text file."""
        with open(filepath, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("BENGALURU TRAFFIC AI - PERFORMANCE EVALUATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Generated: {report['timestamp']}\n\n")
            
            # Overall Metrics
            f.write("DETECTION QUALITY METRICS\n")
            f.write("-" * 80 + "\n")
            overall = report['overall_metrics']
            f.write(f"Accuracy:    {overall['accuracy']*100:.2f}%\n")
            f.write(f"Precision:   {overall['precision']*100:.2f}%\n")
            f.write(f"Recall:      {overall['recall']*100:.2f}%\n")
            f.write(f"F1-Score:    {overall['f1_score']*100:.2f}%\n\n")
            
            # mAP Metrics
            f.write("OBJECT DETECTION QUALITY (mAP)\n")
            f.write("-" * 80 + "\n")
            map_metrics = report['map_metrics']
            f.write(f"mAP@0.5:     {map_metrics['map_50']*100:.2f}%\n")
            f.write(f"mAP@0.75:    {map_metrics['map_75']*100:.2f}%\n")
            f.write(f"mAP@0.5:0.95: {map_metrics['map_50_95']*100:.2f}%\n\n")
            
            # Performance
            f.write("SYSTEM EFFICIENCY\n")
            f.write("-" * 80 + "\n")
            perf = report['performance']
            f.write(f"Processing Speed: {perf['avg_fps']:.2f} FPS\n")
            f.write(f"Avg Latency:      {perf['avg_latency_ms']:.2f} ms\n")
            f.write(f"CPU Usage:        {perf['avg_cpu_percent']:.1f}%\n")
            f.write(f"Memory Usage:     {perf['avg_memory_mb']:.1f} MB\n")
            f.write(f"Peak Memory:      {perf['peak_memory_mb']:.1f} MB\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            summary = report['summary']
            f.write(f"Grade: {summary['detection_quality']['grade']}\n")
            f.write(f"Scalability: {summary['system_efficiency']['scalability']}\n")
        
        logger.info(f"Summary text saved to: {filepath}")


# ── Utility Functions ──────────────────────────────────────────────────────────

def load_ground_truth(annotation_file: str) -> List[dict]:
    """
    Load ground truth annotations from file.
    
    Expected format (JSON):
    [
        {"type": "no_helmet", "bbox": [x1, y1, x2, y2]},
        {"type": "signal_jump", "bbox": [x1, y1, x2, y2]},
        ...
    ]
    """
    with open(annotation_file, 'r') as f:
        return json.load(f)


def create_sample_evaluation():
    """Create sample evaluation for demonstration."""
    evaluator = PerformanceEvaluator()
    evaluator.start_evaluation()
    
    # Simulate 100 frames
    for i in range(100):
        evaluator.start_frame()
        
        # Simulate predictions and ground truth
        if i % 10 == 0:  # Violations every 10 frames
            predictions = [
                {"type": "no_helmet", "bbox": [100, 100, 200, 200], "confidence": 0.9}
            ]
            ground_truth = [
                {"type": "no_helmet", "bbox": [105, 105, 205, 205]}
            ]
        else:
            predictions = []
            ground_truth = []
        
        evaluator.evaluate_detections(predictions, ground_truth)
        evaluator.end_frame()
        
        time.sleep(0.01)  # Simulate processing time
    
    # Generate and save report
    filepath = evaluator.save_report("sample_evaluation.json")
    print(f"Sample evaluation report saved to: {filepath}")
    
    return evaluator


if __name__ == "__main__":
    # Run sample evaluation
    create_sample_evaluation()
