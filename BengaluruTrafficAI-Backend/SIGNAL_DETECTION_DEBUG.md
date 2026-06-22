# 🚦 Signal/Red Light Detection Troubleshooting Guide

## ❗ Issue: Red Light Violations Not Detected

Red light detection requires **TWO components** to work:

1. **ROI Configuration** - Signal box must be defined
2. **Signal State Detection** - System must see the red light

---

## 🔍 **Why It's Not Working**

### **Problem 1: No ROI Configured** (Most Common)

The system needs to know:
- ✅ Where the signal box is (junction area)
- ✅ Where to look for the traffic light
- ✅ Which area vehicles shouldn't enter during red

**If ROI is not configured → NO violations detected**

### **Problem 2: Signal Not Detected**

The system looks for red color in:
- Top 30% of frame
- Right half of frame
- Red HSV threshold: > 0.8% red pixels

**If signal is in different location → Not detected**

---

## ✅ **Quick Fix: Configure ROI for Your Video**

### **Option 1: Use Interactive ROI Tool** (Recommended)

```bash
cd BengaluruTrafficAI-Backend

# Run interactive ROI configuration
python tools/roi_config_tool.py --video ../14985167_960_540_25fps.mp4
```

**Steps**:
1. Video will pause on first frame
2. Draw signal box polygon (junction crossing area)
3. Mark where traffic light is located
4. Save ROI configuration
5. Re-run detection with ROI file

### **Option 2: Manual ROI Configuration**

Create ROI file manually:

**File**: `rois/demo_cam_roi.json`

```json
{
  "camera_id": "demo_cam",
  "resolution": {
    "width": 960,
    "height": 540
  },
  "zones": [
    {
      "type": "signal_box",
      "name": "main_junction",
      "points": [
        [200, 150],
        [760, 150],
        [760, 400],
        [200, 400]
      ],
      "metadata": {
        "description": "Main junction crossing area"
      }
    },
    {
      "type": "stop_line",
      "name": "main_stop_line",
      "points": [
        [50, 380],
        [910, 380]
      ],
      "metadata": {
        "description": "Stop line before junction"
      }
    }
  ],
  "traffic_light_location": {
    "x": 800,
    "y": 100,
    "width": 100,
    "height": 150
  }
}
```

**Then run with ROI**:
```bash
python main.py \
  --source ../14985167_960_540_25fps.mp4 \
  --camera demo_cam \
  --roi rois/demo_cam_roi.json \
  --skip 3
```

### **Option 3: Quick Test with Default ROI**

Run with built-in demo ROI (may need adjustment):

```bash
python main.py \
  --source ../14985167_960_540_25fps.mp4 \
  --camera demo_cam \
  --skip 3
```

The system will use default ROI:
- Signal box: Center area (300,200 to 900,380)
- Signal location: Top-right 30% of frame

---

## 🎯 **Test Signal Detection**

Let me create a test script to verify signal detection:

**File**: `test_signal_detection.py`

```python
import cv2
import numpy as np
from violations.detectors import RedLightDetector

def test_signal_detection(video_path):
    """Test if red signal is being detected in your video."""
    
    cap = cv2.VideoCapture(video_path)
    detector = RedLightDetector("test_cam")
    
    print("Testing signal detection...")
    print("=" * 60)
    
    frame_count = 0
    red_detected_count = 0
    
    while frame_count < 100:  # Test first 100 frames
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Test signal detection
        is_red = detector._detect_signal_state(frame)
        
        if is_red:
            red_detected_count += 1
            print(f"Frame {frame_count}: ✅ RED SIGNAL DETECTED")
        else:
            if frame_count % 10 == 0:
                print(f"Frame {frame_count}: ❌ No red signal")
        
        # Display frame with signal region highlighted
        if frame_count == 1 or frame_count % 30 == 0:
            h, w = frame.shape[:2]
            # Highlight signal detection region
            cv2.rectangle(frame, 
                         (int(w*0.50), 0), 
                         (w, int(h*0.30)), 
                         (0, 255, 255), 2)
            cv2.putText(frame, f"Signal Region", 
                       (int(w*0.55), 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            cv2.imshow("Signal Detection Test", frame)
            cv2.waitKey(500)
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("=" * 60)
    print(f"Results:")
    print(f"Total frames tested: {frame_count}")
    print(f"Red signal detected in: {red_detected_count} frames")
    print(f"Detection rate: {red_detected_count/frame_count*100:.1f}%")
    
    if red_detected_count == 0:
        print("\n⚠️ WARNING: No red signal detected!")
        print("Possible issues:")
        print("  1. Signal is not in top-right 30% of frame")
        print("  2. Signal color is not bright red")
        print("  3. Video resolution is different than expected")
        print("\nSolutions:")
        print("  1. Adjust signal detection region in RedLightDetector")
        print("  2. Adjust HSV thresholds for your video")
        print("  3. Use manual signal annotation")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_signal_detection.py video.mp4")
        sys.exit(1)
    
    test_signal_detection(sys.argv[1])
```

**Run test**:
```bash
python test_signal_detection.py ../14985167_960_540_25fps.mp4
```

---

## 🔧 **Adjust Signal Detection for Your Video**

If signal is not detected, adjust these parameters in `violations/detectors.py`:

### **1. Change Signal Detection Region**

```python
# In RedLightDetector._detect_signal_state()

# CURRENT (default):
signal_region = frame[:int(h * 0.30), int(w * 0.50):]
# Looks in: Top 30%, Right 50%

# IF signal is on LEFT side:
signal_region = frame[:int(h * 0.30), :int(w * 0.50)]

# IF signal is in CENTER:
signal_region = frame[:int(h * 0.30), int(w * 0.30):int(w * 0.70)]

# IF signal is LOWER in frame:
signal_region = frame[int(h * 0.10):int(h * 0.40), int(w * 0.50):]
```

### **2. Adjust HSV Thresholds**

```python
# In RedLightDetector class

# CURRENT (strict):
RED_LOWER_1 = np.array([0,   120, 120])  # Bright red only
RED_UPPER_1 = np.array([10,  255, 255])

# FOR DARKER SIGNALS (more lenient):
RED_LOWER_1 = np.array([0,   80, 80])    # Allow darker reds
RED_UPPER_1 = np.array([15,  255, 255])

# FOR BRIGHTER/OVEREXPOSED:
RED_LOWER_1 = np.array([0,   150, 150])  # Require brighter red
```

### **3. Adjust Detection Threshold**

```python
# In RedLightDetector._detect_signal_state()

# CURRENT (strict):
return red_ratio > 0.008  # 0.8% red pixels

# MORE SENSITIVE (detect smaller signals):
return red_ratio > 0.003  # 0.3% red pixels

# LESS SENSITIVE (avoid false positives):
return red_ratio > 0.015  # 1.5% red pixels
```

---

## 🎯 **Alternative: Manual Signal Annotation**

If automatic signal detection doesn't work, use manual annotation:

### **Option A: Annotate Signal State Per Frame**

Create signal state file:

**File**: `signal_states/demo_video_signals.json`

```json
{
  "video": "14985167_960_540_25fps.mp4",
  "fps": 25,
  "signal_states": [
    {"frame_start": 0, "frame_end": 150, "state": "red"},
    {"frame_start": 151, "frame_end": 300, "state": "green"},
    {"frame_start": 301, "frame_end": 450, "state": "red"},
    {"frame_start": 451, "frame_end": 600, "state": "green"}
  ]
}
```

Modify `main.py` to load signal states from file.

### **Option B: Force Red Signal Mode**

For testing, force all frames to be treated as red:

```python
# In main.py, ViolationPipeline initialization

# Add this parameter
pipeline = ViolationPipeline(
    camera_id=camera_id,
    roi_manager=roi,
    force_red_signal=True  # ← Treat ALL frames as red signal
)
```

---

## 📊 **Debug Output**

Enable detailed logging to see what's happening:

```bash
# In main.py or run command
export LOG_LEVEL=DEBUG

python main.py \
  --source ../14985167_960_540_25fps.mp4 \
  --camera demo_cam \
  --skip 3 \
  --debug
```

Look for these log messages:
```
[DEBUG] RedLightDetector: Signal region shape: (162, 480, 3)
[DEBUG] RedLightDetector: Red pixels: 1250 / 77760 = 1.61%
[DEBUG] RedLightDetector: Signal is RED
[DEBUG] RedLightDetector: Vehicle track=42 in signal box during red
[DEBUG] RedLightDetector: Red-light violation: track=42
```

If you see:
```
[DEBUG] RedLightDetector: Red pixels: 50 / 77760 = 0.06%  ← Too low!
[DEBUG] RedLightDetector: Signal is NOT RED
```

**→ Adjust HSV thresholds or detection region**

---

## 🎬 **Quick Start for Your Video**

Since you have a red light violation video, here's the quickest way to get it working:

### **Step 1: Check Video Resolution**

```bash
ffprobe ../14985167_960_540_25fps.mp4
```

Look for: `Stream #0:0: Video: ... 960x540`

### **Step 2: Adjust ROI Coordinates**

Based on 960x540 resolution, use these ROI settings:

```python
# In main.py, build_demo_roi() function

def build_demo_roi(camera_id: str = "demo") -> ROIManager:
    roi = ROIManager(camera_id)
    
    # Signal box covering center 60% of frame
    roi.add_signal_box([
        (200, 150),   # Top-left
        (760, 150),   # Top-right
        (760, 400),   # Bottom-right
        (200, 400)    # Bottom-left
    ], name="main_junction")
    
    # Stop line at 70% down from top
    roi.add_stop_line([
        (50, 380), 
        (910, 380)
    ], name="stop_line_main")
    
    return roi
```

### **Step 3: Lower Signal Detection Threshold**

```python
# In violations/detectors.py, RedLightDetector class

# Change threshold to be more sensitive
return red_ratio > 0.003  # Was 0.008, now 0.3%
```

### **Step 4: Run with Debug Output**

```bash
python main.py \
  --source ../14985167_960_540_25fps.mp4 \
  --camera demo_cam \
  --skip 2 \
  --show  # Show video output to verify
```

---

## ✅ **Expected Output When Working**

```
2026-06-22 15:30:45 [INFO] detector: Loading yolo11s.pt
2026-06-22 15:30:46 [INFO] main: Processing demo_cam
2026-06-22 15:30:48 [DEBUG] RedLightDetector: Signal is RED
2026-06-22 15:30:48 [DEBUG] RedLightDetector: Vehicle track=12 in signal box
2026-06-22 15:30:48 [INFO] main: VIOLATION | red_light_violation | track=12 | plate=KA01AB1234
2026-06-22 15:30:48 [INFO] main: Evidence saved: output/evidence/RED_LIGHT_demo_cam_frame450_track12.jpg
```

---

## 🐛 **Common Issues & Solutions**

| Issue | Cause | Solution |
|-------|-------|----------|
| **No violations detected** | No ROI configured | Create ROI file or use build_demo_roi() |
| **Signal not detected** | Wrong detection region | Adjust signal_region coordinates |
| **False negatives** | Threshold too strict | Lower threshold from 0.008 to 0.003 |
| **False positives** | Threshold too lenient | Raise threshold or adjust HSV range |
| **Wrong signal box** | ROI doesn't match video | Redraw signal_box for your video |

---

## 📞 **Quick Help Commands**

```bash
# Test signal detection only
python test_signal_detection.py video.mp4

# Run with debug output
python main.py --source video.mp4 --camera demo --debug

# Generate ROI visually
python tools/roi_config_tool.py --video video.mp4

# Check what detectors are active
python -c "from violations import *; print([d.VIOLATION_TYPE for d in [RedLightDetector('test')]])"
```

---

**Need immediate fix?** Lower the threshold in `violations/detectors.py` line 290:
```python
return red_ratio > 0.003  # More sensitive
```

Then re-run your video!

