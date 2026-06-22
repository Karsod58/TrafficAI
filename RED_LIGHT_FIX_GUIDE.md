# 🚦 Red Light Detection - Quick Fix Guide

## ✅ Changes Applied

### 1. **Lowered Signal Detection Threshold** (More Sensitive)
- **File**: `violations/detectors.py`
- **Change**: Threshold reduced from `0.008` (0.8%) to `0.003` (0.3%)
- **Effect**: System will now detect weaker/smaller red signals

### 2. **Improved ROI Coordinates** for 960x540 Videos
- **File**: `main.py` - `build_demo_roi()` function
- **Change**: Updated signal box to cover center 60% of frame
- **Coordinates**: `(200, 150)` to `(760, 400)` for 960x540 resolution

### 3. **Created Testing Tools**
- **test_signal_detection.py** - Verify signal detection is working
- **tools/quick_roi_setup.py** - Interactive ROI configuration

---

## 🚀 Quick Start - Test Your Video

### **Step 1: Test Signal Detection**

First, verify the system can detect red signals in your video:

```bash
cd BengaluruTrafficAI-Backend
python test_signal_detection.py ../14985167_960_540_25fps.mp4
```

**Expected Output:**
```
🚦 RED LIGHT SIGNAL DETECTION TEST
Video: 14985167_960_540_25fps.mp4
Resolution: 960x540
Testing first 100 frames...

Frame    1: ✅ RED SIGNAL DETECTED (red pixels: 0.85%)
Frame   25: ⚪ No red signal
Frame   32: ✅ RED SIGNAL DETECTED (red pixels: 1.20%)

📊 RESULTS
Total frames tested: 100
Red signal detected: 45 frames
Detection rate: 45.0%

✅ SUCCESS: Red signal detected!
```

**If signal is NOT detected:**
- Video might not show red light
- Signal might be in different location
- Proceed to Step 2 for manual ROI setup

---

### **Step 2: Configure ROI (Signal Box)**

Red light detection needs TWO things:
1. ✅ **Signal detection** (can detect red color) ← Fixed with threshold change
2. ⚠️ **Signal box ROI** (defines where violations occur) ← Needs configuration

#### **Option A: Interactive ROI Setup** (Recommended)

```bash
python tools/quick_roi_setup.py ../14985167_960_540_25fps.mp4
```

**Interactive Steps:**
1. Video first frame appears
2. Click 4 corners of junction crossing area (signal box)
3. Press 'n' for next step
4. Click 2 points to draw stop line
5. Press 's' to save

**Output:** Creates `rois/14985167_960_540_25fps_roi.json`

#### **Option B: Use Default ROI**

The system now has improved default ROI for 960x540 videos. Try running directly:

```bash
python main.py --source ../14985167_960_540_25fps.mp4 --camera demo_cam --show
```

This uses the built-in `build_demo_roi()` with updated coordinates.

---

### **Step 3: Run Detection with ROI**

```bash
# If you created custom ROI:
python main.py \
  --source ../14985167_960_540_25fps.mp4 \
  --camera demo_cam \
  --roi rois/14985167_960_540_25fps_roi.json \
  --show \
  --skip 2

# If using default ROI:
python main.py \
  --source ../14985167_960_540_25fps.mp4 \
  --camera demo_cam \
  --show \
  --skip 2
```

**Expected Output:**
```
[INFO] BengaluruTrafficAI — Starting pipeline
[INFO] detector: Loading yolo11s.pt
[DEBUG] RedLightDetector: Signal is RED
[INFO] main: VIOLATION | red_light_violation | track=12 | plate=KA01AB1234 | conf=0.90
[INFO] main: Evidence saved: output/evidence/RED_LIGHT_demo_cam_frame450_track12.jpg
```

---

## 🔧 Troubleshooting

### **Issue 1: "No violations detected"**

**Check 1 - Is signal being detected?**
```bash
python test_signal_detection.py video.mp4
```

If **NO red signal detected:**
- Verify video actually shows red traffic light
- Adjust detection region (see "Advanced Configuration" below)

**Check 2 - Is ROI configured?**
- Look for log: `[WARNING] No ROI file found — using demo ROI`
- Run interactive ROI tool: `python tools/quick_roi_setup.py video.mp4`

**Check 3 - Are vehicles entering signal box?**
- With `--show` flag, verify:
  - Green polygon shows signal box
  - Vehicles pass through that area during red signal

---

### **Issue 2: "False positives" (detecting violations when signal is green)**

The threshold might be too low. Increase it:

**File**: `violations/detectors.py` line 290
```python
# Change from:
return red_ratio > 0.003

# To (less sensitive):
return red_ratio > 0.006
```

---

### **Issue 3: "Signal not detected" (threshold too strict)**

Lower the threshold further:

**File**: `violations/detectors.py` line 290
```python
# Change to:
return red_ratio > 0.001  # Very sensitive
```

---

## ⚙️ Advanced Configuration

### **Adjust Signal Detection Region**

If traffic light is not in top-right corner, modify the region:

**File**: `violations/detectors.py` - `RedLightDetector._detect_signal_state()`

```python
# CURRENT (top-right 30%):
signal_region = frame[:int(h * 0.30), int(w * 0.50):]

# If signal is on LEFT side:
signal_region = frame[:int(h * 0.30), :int(w * 0.50)]

# If signal is in CENTER:
signal_region = frame[:int(h * 0.30), int(w * 0.30):int(w * 0.70)]

# If signal is LOWER in frame:
signal_region = frame[int(h * 0.10):int(h * 0.40), int(w * 0.50):]

# If signal is on BOTTOM (overhead/underpass):
signal_region = frame[int(h * 0.60):, int(w * 0.30):int(w * 0.70)]
```

### **Adjust HSV Color Range**

For different signal colors/brightness:

**File**: `violations/detectors.py` - `RedLightDetector` class

```python
# CURRENT (bright red):
RED_LOWER_1 = np.array([0,   120, 120])
RED_UPPER_1 = np.array([10,  255, 255])

# For DARKER signals:
RED_LOWER_1 = np.array([0,   80, 80])    # Lower saturation/value

# For BRIGHTER/OVEREXPOSED signals:
RED_LOWER_1 = np.array([0,   150, 180])  # Higher requirements
```

### **Custom Signal Box Coordinates**

For non-standard video resolutions, adjust ROI manually:

**File**: `main.py` - `build_demo_roi()` function

```python
# Example for 1280x720 video:
roi.add_signal_box([
    (300, 180),   # Top-left
    (980, 180),   # Top-right  
    (980, 540),   # Bottom-right
    (300, 540)    # Bottom-left
], name="signal_box_main")
```

**Rule of thumb for signal box:**
- Width: 60-70% of frame (center area)
- Height: From 25-30% down to 70-75% (junction crossing)

---

## 📊 Understanding Detection Logic

### **How Red Light Detection Works**

```
1. Signal Detection (Color-based)
   └─> Looks for red pixels in designated region
   └─> Threshold: > 0.3% red pixels
   └─> Returns: signal_is_red (True/False)

2. Vehicle Position Check (ROI-based)
   └─> Checks if vehicle center is inside signal_box
   └─> Only during red signal phase
   └─> If inside → VIOLATION

3. Track Confirmation
   └─> Requires multiple frames (anti-flicker)
   └─> Confidence: 0.90 for red light violations
   └─> Evidence saved with annotated frame
```

### **Why Both Components Are Needed**

| Component | Purpose | What Happens If Missing |
|-----------|---------|-------------------------|
| **Signal Detection** | Knows when light is red | Detects violations even when green |
| **Signal Box ROI** | Defines restricted area | No violations detected at all |

---

## 📁 Files Modified

### **Core Changes**
1. ✅ `violations/detectors.py` - Lowered threshold from 0.008 to 0.003
2. ✅ `main.py` - Updated `build_demo_roi()` with better coordinates

### **New Tools Created**
3. ✅ `test_signal_detection.py` - Test if signal detection works
4. ✅ `tools/quick_roi_setup.py` - Interactive ROI configuration
5. ✅ `RED_LIGHT_FIX_GUIDE.md` - This guide

---

## 🎯 Next Steps

### **For Your Specific Video:**

1. **Test signal detection:**
   ```bash
   python test_signal_detection.py ../14985167_960_540_25fps.mp4
   ```

2. **If signal detected, configure ROI:**
   ```bash
   python tools/quick_roi_setup.py ../14985167_960_540_25fps.mp4
   ```

3. **Run detection:**
   ```bash
   python main.py \
     --source ../14985167_960_540_25fps.mp4 \
     --camera demo_cam \
     --roi rois/14985167_960_540_25fps_roi.json \
     --show
   ```

### **For Production Deployment:**

1. Create ROI configuration for each camera location
2. Store ROI files in `rois/` directory
3. Update API upload endpoint to use camera-specific ROIs
4. Add ROI management UI in frontend (future enhancement)

---

## 💡 Tips

### **Good Signal Box Placement:**
- ✅ Covers the junction crossing area
- ✅ Large enough to catch all entering vehicles
- ✅ Not too large (avoids detecting vehicles in adjacent lanes)

### **Good Stop Line Placement:**
- ✅ Positioned before the junction
- ✅ Horizontal line across all lanes
- ✅ Where vehicles should stop during red

### **Testing Best Practices:**
- Test with `--show` flag first to verify ROI placement
- Use `--skip 2` or `--skip 3` for faster processing during testing
- Check evidence images in `output/evidence/` folder
- Verify plate numbers are being detected

---

## 🔗 Related Documentation

- **Signal Detection Debug Guide**: `SIGNAL_DETECTION_DEBUG.md`
- **ALPR Quality Guide**: `ALPR_AND_BATCH_IMPROVEMENTS.md`
- **Training Guide**: `../TRAINING_GUIDE.md`
- **Performance Evaluation**: `utils/performance_evaluator.py`

---

## ❓ FAQ

**Q: Do I need to create ROI for every video?**
A: Yes, each camera location needs its own ROI. For testing, default ROI works for standard intersection videos.

**Q: Can I use the same ROI for multiple cameras at same location?**
A: Only if they have identical mounting angle and resolution.

**Q: What if my video doesn't show traffic lights?**
A: Red light detection won't work without visible signal. Use stop line or other violation types instead.

**Q: Can I manually annotate signal states instead of auto-detection?**
A: Yes, but requires custom implementation. Check `SIGNAL_DETECTION_DEBUG.md` for manual annotation approach.

---

**Need help?** Check logs for these messages:
```
[DEBUG] RedLightDetector: Signal is RED
[DEBUG] RedLightDetector: Vehicle track=X in signal box
[INFO] VIOLATION | red_light_violation | ...
```

If you don't see these, signal detection or ROI is not configured correctly.
