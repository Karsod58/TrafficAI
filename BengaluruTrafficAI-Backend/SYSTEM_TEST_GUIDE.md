# 🧪 System Testing Guide

## Quick Test Commands for Your Video

Your video: `14985167_960_540_25fps.mp4` (960x540 resolution)

Run these tests in your terminal with venv activated:

---

## ✅ Test 1: Video Quality Analysis (30 seconds)

```bash
cd BengaluruTrafficAI-Backend
python core\low_res_handler.py ..\14985167_960_540_25fps.mp4
```

**Expected Output:**
```
📹 VIDEO QUALITY REPORT
Resolution:    960x540
Quality Tier:  LOW
Estimated ALPR: 40-60%
Performance Estimates:
  Violation Detection: 88-92%
  Tracking Accuracy: 85-90%
```

**✓ PASS if:** Shows resolution and quality tier
**✗ FAIL if:** Errors or crashes

---

## ✅ Test 2: Signal Detection Test (1 minute)

```bash
python test_signal_detection.py ..\14985167_960_540_25fps.mp4
```

**Expected Output:**
```
🚦 RED LIGHT SIGNAL DETECTION TEST
Video: 14985167_960_540_25fps.mp4
Resolution: 960x540

Frame    1: ✅ RED SIGNAL DETECTED (red pixels: 0.85%)
Frame   25: ⚪ No red signal
...

📊 RESULTS
Total frames tested: 100
Red signal detected: X frames
Detection rate: X.X%
```

**✓ PASS if:** 
- Detects at least some red signals (>5%)
- No crashes
- Window shows video with yellow box overlay

**✗ FAIL if:**
- 0% detection and video has red lights
- Python errors
- Cannot open video

---

## ✅ Test 3: Quick Detection Test (2-3 minutes)

```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_cam --skip 3 --max-frames 300 --show
```

**Expected Output:**
```
[INFO] BengaluruTrafficAI — Starting pipeline
[INFO] detector: Loading yolo11s.pt
[INFO] VideoPreprocessor initialized
[INFO] Auto-configured for low quality video

Processing frames...

[INFO] VIOLATION | <violation_type> | track=X | plate=XXX | conf=0.XX
[INFO] Evidence saved: output/evidence/...

PIPELINE COMPLETE
  Frames processed : ~100 (with skip=3)
  Violations found : X
```

**✓ PASS if:**
- Loads YOLO11 model successfully
- Processes frames (shows progress)
- Detects at least 1-2 violations (if video has violations)
- Shows video window with annotations
- Creates evidence files in `output/evidence/`

**✗ FAIL if:**
- Cannot load model
- Crashes during processing
- No violations detected (but video clearly has violations)

**Note:** Press 'Q' to stop video window

---

## ✅ Test 4: Full Detection Run (5-10 minutes)

```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_cam --skip 3
```

**Expected Output:**
```
[INFO] Processing...

Progress: 100 frames | avg inference: 45.2ms | violations: 3 | active tracks: 8
Progress: 200 frames | avg inference: 43.8ms | violations: 7 | active tracks: 12
...

PIPELINE COMPLETE
  Frames processed : XXXX
  Violations found : XX
  Avg inference    : XX.X ms/frame
  
  Violation Breakdown:
    triple_riding           : X
    red_light_violation     : X
    wrong_side_driving      : X
```

**✓ PASS if:**
- Completes without crashing
- Shows violation breakdown
- Creates evidence files
- Performance is reasonable (20-50ms/frame on CPU)

**✗ FAIL if:**
- Crashes mid-processing
- Extremely slow (>200ms/frame)
- No violations detected at all

---

## ✅ Test 5: API Integration Test

**Prerequisites:** Backend API must be running in another terminal:
```bash
uvicorn api.app:app --reload --port 8000
```

**Then run:**
```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_cam --skip 5 --max-frames 200
```

**After processing, test API:**
```bash
curl http://localhost:8000/violations
```

**Expected:** JSON response with violations list

**Or open in browser:** http://localhost:8000/docs

**✓ PASS if:**
- Violations appear in API response
- No database errors
- Can access API docs

---

## 🔍 Verification Checklist

After running tests, verify:

### Files Created:
```bash
# Check evidence folder
dir output\evidence\

# Should see files like:
# TRIPLE_RIDING_test_cam_frame123_track5.jpg
# RED_LIGHT_test_cam_frame456_track12.jpg
```

**✓ PASS if:** Evidence images exist and show violations

### Model Files:
```bash
# Check YOLO model
dir yolo11s.pt
```

**✓ PASS if:** File exists (~20MB)

### Database (if API running):
```bash
# Check violations in database
curl http://localhost:8000/violations/stats
```

**Expected:**
```json
{
  "total_violations": XX,
  "pending_review": XX,
  "today_violations": XX
}
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Cannot open video source"
**Cause:** Wrong video path or file doesn't exist

**Solution:**
```bash
# Check file exists
dir ..\14985167_960_540_25fps.mp4

# Use absolute path
python main.py --source "D:\Desktop\BengaluruTrafficAI_src\14985167_960_540_25fps.mp4" --camera test
```

### Issue 2: "No module named 'cv2'"
**Cause:** Not in venv or dependencies not installed

**Solution:**
```bash
# Activate venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Issue 3: "No violations detected"
**Possible Causes:**
- Video doesn't actually show violations
- ROI not configured for red light detection
- Detection thresholds too strict

**Solution:**
```bash
# Check what's detected (verbose)
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test --skip 3 --max-frames 100 --show
# Watch the video window - are vehicles being detected?

# For red light issues, configure ROI:
python tools\quick_roi_setup.py ..\14985167_960_540_25fps.mp4
```

### Issue 4: "Model not found"
**Cause:** yolo11s.pt not in Backend folder

**Solution:**
```bash
# Check model exists
dir yolo11s.pt

# If missing, download:
# (Model should be in Backend folder already)
```

### Issue 5: Very slow processing
**Cause:** No GPU, high resolution, or no frame skipping

**Solution:**
```bash
# Use more frame skipping
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test --skip 5

# Disable preprocessing
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test --skip 5 --no-preproc
```

---

## 📊 Expected Performance Metrics

For your 960x540 video on CPU:

| Metric | Expected Value | Notes |
|--------|---------------|-------|
| **Inference Time** | 30-60ms/frame | YOLO11 detection |
| **FPS (skip=3)** | 15-25 FPS | Effective processing |
| **Violation Detection** | 88-92% | Accuracy |
| **ALPR Success** | 40-60% | Limited at 540p |
| **Memory Usage** | 500MB-1GB | During processing |

---

## ✅ Success Criteria

Your system is working correctly if:

1. ✅ **Video loads and processes** without crashing
2. ✅ **Vehicles are detected** (you see bounding boxes)
3. ✅ **Tracking works** (boxes follow vehicles)
4. ✅ **At least 1 violation detected** (if video has violations)
5. ✅ **Evidence images created** in output/evidence/
6. ✅ **No Python errors** during execution
7. ✅ **Reasonable performance** (20-60ms per frame)

---

## 🎯 What to Report Back

After running tests, report:

1. **Which tests passed/failed**
2. **Any error messages** (copy exact text)
3. **Performance numbers** (FPS, inference time)
4. **Violations detected** (types and count)
5. **Evidence files created** (yes/no)
6. **Video window showing** (yes/no, what you see)

---

## 🚀 Quick Start (Copy-Paste)

Run ALL tests in sequence:

```bash
cd D:\Desktop\BengaluruTrafficAI_src\BengaluruTrafficAI-Backend

echo "Test 1: Quality Analysis"
python core\low_res_handler.py ..\14985167_960_540_25fps.mp4
pause

echo "Test 2: Signal Detection"
python test_signal_detection.py ..\14985167_960_540_25fps.mp4
pause

echo "Test 3: Quick Detection (300 frames)"
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_cam --skip 3 --max-frames 300 --show
pause

echo "Test 4: Check Evidence"
dir output\evidence\
pause

echo "All tests complete!"
```

---

## 📝 Test Results Template

Copy this and fill in your results:

```
=== SYSTEM TEST RESULTS ===
Date: _________
Video: 14985167_960_540_25fps.mp4

Test 1 - Quality Analysis:
[ ] PASS  [ ] FAIL
Resolution detected: _______
Quality tier: _______

Test 2 - Signal Detection:
[ ] PASS  [ ] FAIL
Red signals detected: ____%
Errors: _______

Test 3 - Quick Detection:
[ ] PASS  [ ] FAIL
Frames processed: _______
Violations detected: _______
Inference time: _______ms
Errors: _______

Test 4 - Full Run:
[ ] PASS  [ ] FAIL
Total violations: _______
Types detected: _______
Evidence files: _______ (count)

Overall System Status:
[ ] WORKING PERFECTLY
[ ] WORKING WITH MINOR ISSUES
[ ] NOT WORKING (major issues)

Notes:
_______________________
_______________________
```

---

Need help? Check the error message against "Common Issues" section above!
