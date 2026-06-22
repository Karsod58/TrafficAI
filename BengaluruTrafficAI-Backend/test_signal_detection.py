"""
Quick test script to debug red light signal detection.
Tests if the system can detect red signals in your video.
"""

import cv2
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from violations.detectors import RedLightDetector


def test_signal_detection(video_path: str, max_frames: int = 100):
    """Test if red signal is being detected in your video."""
    
    if not Path(video_path).exists():
        print(f"❌ Video file not found: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return
    
    # Get video info
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print("\n" + "=" * 70)
    print("🚦 RED LIGHT SIGNAL DETECTION TEST")
    print("=" * 70)
    print(f"Video: {Path(video_path).name}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps:.1f}")
    print(f"Total frames: {total_frames}")
    print(f"Testing first {min(max_frames, total_frames)} frames...")
    print("=" * 70)
    
    detector = RedLightDetector("test_cam")
    
    frame_count = 0
    red_detected_count = 0
    red_detected_frames = []
    
    # Show detection region info
    print(f"\n📍 Detection Region:")
    print(f"   Area: Top 30% of frame, Right 50%")
    print(f"   Coordinates: ({int(width*0.50)}, 0) to ({width}, {int(height*0.30)})")
    print(f"   Red threshold: 0.3% of pixels")
    print()
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Test signal detection
        is_red = detector._detect_signal_state(frame)
        
        if is_red:
            red_detected_count += 1
            red_detected_frames.append(frame_count)
            
            # Show detailed info for first few detections
            if red_detected_count <= 5:
                # Calculate red ratio manually for display
                h, w = frame.shape[:2]
                signal_region = frame[:int(h * 0.30), int(w * 0.50):]
                hsv = cv2.cvtColor(signal_region, cv2.COLOR_BGR2HSV)
                red_mask = cv2.inRange(hsv, detector.RED_LOWER_1, detector.RED_UPPER_1) | \
                          cv2.inRange(hsv, detector.RED_LOWER_2, detector.RED_UPPER_2)
                red_pixels = np.sum(red_mask > 0)
                total = signal_region.shape[0] * signal_region.shape[1]
                red_ratio = red_pixels / max(total, 1)
                
                print(f"Frame {frame_count:4d}: ✅ RED SIGNAL DETECTED (red pixels: {red_ratio*100:.2f}%)")
        else:
            if frame_count % 25 == 0:
                print(f"Frame {frame_count:4d}: ⚪ No red signal")
        
        # Display frame with signal region highlighted (every 30 frames)
        if frame_count == 1 or frame_count % 30 == 0:
            display_frame = frame.copy()
            h, w = display_frame.shape[:2]
            
            # Highlight signal detection region
            cv2.rectangle(display_frame, 
                         (int(w*0.50), 0), 
                         (w, int(h*0.30)), 
                         (0, 255, 255), 3)
            
            cv2.putText(display_frame, "Signal Detection Region", 
                       (int(w*0.52), 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            status = "RED DETECTED" if is_red else "No Red Signal"
            color = (0, 255, 0) if is_red else (0, 0, 255)
            cv2.putText(display_frame, f"Frame {frame_count}: {status}", 
                       (20, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # Resize if too large
            if w > 1280:
                scale = 1280 / w
                display_frame = cv2.resize(display_frame, None, fx=scale, fy=scale)
            
            cv2.imshow("Signal Detection Test (Press Q to quit)", display_frame)
            key = cv2.waitKey(100) & 0xFF
            if key == ord('q'):
                print("\n⏹️ Test stopped by user")
                break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Results summary
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    print(f"Total frames tested: {frame_count}")
    print(f"Red signal detected: {red_detected_count} frames")
    print(f"Detection rate: {red_detected_count/frame_count*100:.1f}%")
    
    if red_detected_count > 0:
        print(f"\n✅ SUCCESS: Red signal detected in frames: {red_detected_frames[:10]}")
        if len(red_detected_frames) > 10:
            print(f"   ... and {len(red_detected_frames)-10} more frames")
        print("\n✔️ Signal detection is working!")
        print("💡 Now check if ROI signal_box is configured correctly")
        print("   Run: python main.py --source <video> --camera demo --show")
    else:
        print("\n⚠️ WARNING: No red signal detected!")
        print("\n🔧 Possible issues:")
        print("   1. Signal is not in top-right 30% of frame")
        print("   2. Signal color is not bright red")
        print("   3. Video doesn't show red signal")
        print("   4. Threshold is too strict")
        print("\n💡 Solutions:")
        print("   1. Adjust detection region in violations/detectors.py")
        print("      Change line: signal_region = frame[:int(h * 0.30), int(w * 0.50):]")
        print("   2. Lower threshold (currently 0.003):")
        print("      Change line: return red_ratio > 0.003")
        print("   3. Verify video actually shows red traffic light")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n📖 Usage: python test_signal_detection.py <video_path> [max_frames]")
        print("\nExample:")
        print("  python test_signal_detection.py ../14985167_960_540_25fps.mp4")
        print("  python test_signal_detection.py video.mp4 200")
        sys.exit(1)
    
    video_path = sys.argv[1]
    max_frames = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    test_signal_detection(video_path, max_frames)
