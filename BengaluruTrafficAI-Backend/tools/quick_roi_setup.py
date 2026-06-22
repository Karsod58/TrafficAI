"""
Quick ROI Setup Tool
Interactive tool to draw signal box and stop line for red light detection
"""

import cv2
import numpy as np
import json
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ROIDrawer:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        ret, self.frame = self.cap.read()
        if not ret:
            raise ValueError("Cannot read first frame")
        
        self.original_frame = self.frame.copy()
        self.height, self.width = self.frame.shape[:2]
        
        # Scale for display if needed
        self.scale = 1.0
        if self.width > 1280:
            self.scale = 1280 / self.width
        
        self.display_frame = cv2.resize(self.frame, None, fx=self.scale, fy=self.scale)
        
        # Points for drawing
        self.signal_box_points = []
        self.stop_line_points = []
        self.mode = "signal_box"  # "signal_box" or "stop_line"
        
        self.window_name = "ROI Setup - Draw Signal Box"
        
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to draw ROI."""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Convert display coordinates to original frame coordinates
            orig_x = int(x / self.scale)
            orig_y = int(y / self.scale)
            
            if self.mode == "signal_box":
                self.signal_box_points.append((orig_x, orig_y))
                print(f"Signal box point {len(self.signal_box_points)}: ({orig_x}, {orig_y})")
                
                if len(self.signal_box_points) == 4:
                    print("✅ Signal box complete! Press 'n' for next step (stop line)")
                    
            elif self.mode == "stop_line":
                self.stop_line_points.append((orig_x, orig_y))
                print(f"Stop line point {len(self.stop_line_points)}: ({orig_x}, {orig_y})")
                
                if len(self.stop_line_points) == 2:
                    print("✅ Stop line complete! Press 's' to save")
            
            self.update_display()
    
    def update_display(self):
        """Redraw the frame with current ROI points."""
        self.display_frame = cv2.resize(self.original_frame, None, 
                                       fx=self.scale, fy=self.scale)
        
        # Draw signal box
        if len(self.signal_box_points) > 0:
            scaled_points = [(int(x*self.scale), int(y*self.scale)) 
                           for x, y in self.signal_box_points]
            
            # Draw points
            for i, pt in enumerate(scaled_points):
                cv2.circle(self.display_frame, pt, 5, (0, 255, 255), -1)
                cv2.putText(self.display_frame, str(i+1), 
                          (pt[0]+10, pt[1]-10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            # Draw lines between points
            for i in range(len(scaled_points)):
                pt1 = scaled_points[i]
                pt2 = scaled_points[(i+1) % len(scaled_points)]
                cv2.line(self.display_frame, pt1, pt2, (0, 255, 0), 2)
            
            # Fill if complete
            if len(scaled_points) == 4:
                overlay = self.display_frame.copy()
                cv2.fillPoly(overlay, [np.array(scaled_points)], (0, 255, 0))
                cv2.addWeighted(overlay, 0.3, self.display_frame, 0.7, 0, 
                              self.display_frame)
        
        # Draw stop line
        if len(self.stop_line_points) > 0:
            scaled_points = [(int(x*self.scale), int(y*self.scale)) 
                           for x, y in self.stop_line_points]
            
            for pt in scaled_points:
                cv2.circle(self.display_frame, pt, 5, (255, 0, 255), -1)
            
            if len(scaled_points) == 2:
                cv2.line(self.display_frame, scaled_points[0], scaled_points[1], 
                        (255, 0, 255), 3)
        
        # Instructions
        instructions = []
        if self.mode == "signal_box":
            instructions.append("SIGNAL BOX: Click 4 corners of junction area")
            instructions.append(f"Points: {len(self.signal_box_points)}/4")
        else:
            instructions.append("STOP LINE: Click 2 points for line")
            instructions.append(f"Points: {len(self.stop_line_points)}/2")
        
        instructions.append("Press 'r' to reset | 'q' to quit | 's' to save")
        
        y_offset = 30
        for i, text in enumerate(instructions):
            cv2.putText(self.display_frame, text, (10, y_offset + i*30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(self.display_frame, text, (10, y_offset + i*30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        cv2.imshow(self.window_name, self.display_frame)
    
    def run(self):
        """Main interaction loop."""
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        print("\n" + "=" * 70)
        print("🎯 ROI SETUP TOOL - Red Light Detection")
        print("=" * 70)
        print(f"Video: {Path(self.video_path).name}")
        print(f"Resolution: {self.width}x{self.height}")
        print("\n📍 STEP 1: Draw Signal Box (Junction Area)")
        print("   Click 4 corners of the area where vehicles shouldn't be during red")
        print("   Typically covers the center of the junction/intersection")
        print("\nControls:")
        print("   - Left Click: Add point")
        print("   - 'n': Next step (after signal box complete)")
        print("   - 'r': Reset current drawing")
        print("   - 'q': Quit without saving")
        print("   - 's': Save ROI configuration")
        print("=" * 70 + "\n")
        
        self.update_display()
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("❌ Cancelled by user")
                break
            
            elif key == ord('r'):
                if self.mode == "signal_box":
                    self.signal_box_points = []
                    print("🔄 Reset signal box")
                else:
                    self.stop_line_points = []
                    print("🔄 Reset stop line")
                self.update_display()
            
            elif key == ord('n'):
                if len(self.signal_box_points) == 4 and self.mode == "signal_box":
                    self.mode = "stop_line"
                    cv2.setWindowTitle(self.window_name, "ROI Setup - Draw Stop Line")
                    print("\n📍 STEP 2: Draw Stop Line")
                    print("   Click 2 points to draw the stop line")
                    print("   This is where vehicles should stop during red signal")
                    self.update_display()
            
            elif key == ord('s'):
                if len(self.signal_box_points) == 4 and len(self.stop_line_points) == 2:
                    self.save_roi()
                    break
                else:
                    print("⚠️ Complete both signal box (4 points) and stop line (2 points) first!")
        
        cv2.destroyAllWindows()
        self.cap.release()
    
    def save_roi(self):
        """Save ROI configuration to JSON."""
        roi_config = {
            "camera_id": "demo_cam",
            "resolution": {
                "width": self.width,
                "height": self.height
            },
            "zones": [
                {
                    "type": "signal_box",
                    "name": "main_junction",
                    "points": self.signal_box_points,
                    "metadata": {
                        "description": "Main junction crossing area - vehicles detected here during red signal are violations"
                    }
                },
                {
                    "type": "stop_line",
                    "name": "main_stop_line",
                    "points": self.stop_line_points,
                    "metadata": {
                        "description": "Stop line before junction"
                    }
                }
            ],
            "notes": "Generated by quick_roi_setup.py"
        }
        
        # Save to rois directory
        output_dir = Path(__file__).parent.parent / "rois"
        output_dir.mkdir(exist_ok=True)
        
        video_name = Path(self.video_path).stem
        output_file = output_dir / f"{video_name}_roi.json"
        
        with open(output_file, 'w') as f:
            json.dump(roi_config, f, indent=2)
        
        print("\n" + "=" * 70)
        print("✅ ROI Configuration Saved!")
        print("=" * 70)
        print(f"File: {output_file}")
        print("\nConfiguration:")
        print(f"  Signal Box: {self.signal_box_points}")
        print(f"  Stop Line: {self.stop_line_points}")
        print("\n💡 To use this ROI, run:")
        print(f"   python main.py --source {self.video_path} --roi {output_file} --show")
        print("=" * 70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("\n📖 Usage: python quick_roi_setup.py <video_path>")
        print("\nExample:")
        print("  python quick_roi_setup.py ../../14985167_960_540_25fps.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    if not Path(video_path).exists():
        print(f"❌ Video file not found: {video_path}")
        sys.exit(1)
    
    try:
        drawer = ROIDrawer(video_path)
        drawer.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
