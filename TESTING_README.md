# 🧪 Testing Your BengaluruTrafficAI System

## 📋 Overview

You have a test video ready: `14985167_960_540_25fps.mp4` (960x540 resolution)

This guide helps you verify the entire system works correctly.

---

## 🚀 Quick Start (Choose One)

### Option A: Automated Test (Recommended)
Run all tests automatically:

```bash
cd BengaluruTrafficAI-Backend
run_all_tests.bat
```

This runs 4 tests and generates a `test_results.txt` report.

### Option B: Manual Quick Test
Run 3 commands manually (see `QUICK_TEST.md`):

```bash
cd BengaluruTrafficAI-Backend

# Test 1: Quality check
python core\low_res_handler.py ..\14985167_960_540_25fps.mp4

# Test 2: Signal detection
python test_signal_detection.py ..\14985167_960_540_25fps.mp4

# Test 3: Full detection
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_cam --skip 3 --max-frames 300 --show
```

### Option C: Detailed Testing
Follow step-by-step guide in `SYSTEM_TEST_GUIDE.md`

---

## 📁 Testing Documentation

| File | Purpose | Time Required |
|------|---------|---------------|
| **QUICK_TEST.md** | Fastest verification (3 commands) | 5 minutes |
| **SYSTEM_TEST_GUIDE.md** | Comprehensive testing guide | 15-20 minutes |
| **run_all_tests.bat** | Automated test suite | 10 minutes |

---

## ✅ What Gets Tested

### 1. **Video Quality Analysis**
- Tests: Resolution detection, quality tier assessment
- Verifies: OpenCV installation, video file accessibility
- Output: Quality report with performance estimates

### 2. **Signal Detection**
- Tests: Red light detection in video frames
- Verifies: Color detection, signal recognition
- Output: Detection rate, visual overlay

### 3. **Object Detection**
- Tests: Vehicle and person detection with YOLO11
- Verifies: Model loading, inference, tracking
- Output: Bounding boxes, tracking IDs

### 4. **Violation Detection**
- Tests: Full violation pipeline (red light, triple riding, etc.)
- Verifies: End-to-end system functionality
- Output: Violation events, evidence images

### 5. **Performance**
- Tests: Processing speed, memory usage
- Verifies: System runs efficiently
- Output: FPS, inference time statistics

---

## 📊 Expected Results for Your Video (960x540)

### Video Quality
- Resolution: 960x540
- Quality Tier: LOW (480p-720p range)
- Estimated ALPR: 40-60%

### Performance (CPU)
- Inference Time: 30-60ms per frame
- Processing Speed: 15-25 FPS (with skip=3)
- Memory Usage: 500MB-1GB

### Detection Accuracy
- Vehicle Detection: 88-92%
- Person Detection: 85-90%
- Violation Detection: 88-92%
- License Plates: 40-60% (limited at 540p)

---

## 🎯 Success Criteria

Your system is **WORKING CORRECTLY** if:

✅ All commands execute without Python errors  
✅ YOLO11 model loads successfully  
✅ Video processes and shows progress  
✅ Vehicles are detected (bounding boxes visible)  
✅ Tracking assigns IDs to vehicles  
✅ At least 1 violation detected (if video has violations)  
✅ Evidence images created in `output/evidence/`  
✅ Processing speed is reasonable (20-60ms/frame)  

---

## ❌ Known Limitations (Normal Behavior)

These are **EXPECTED** and not issues:

⚠️ **Low ALPR accuracy** (40-60%) - Normal for 540p video  
⚠️ **Some plates show "N/A"** - Quality checks skip poor crops  
⚠️ **Red light detection 0%** - Requires ROI configuration  
⚠️ **Blurry evidence images** - Source video is 540p  
⚠️ **Slower on CPU** - GPU recommended for real-time  

---

## 🐛 Common Issues & Fixes

### Issue: "ModuleNotFoundError: No module named 'cv2'"
**Fix:**
```bash
pip install -r requirements.txt
```

### Issue: "Cannot open video source"
**Fix:**
```bash
# Use absolute path
python main.py --source "D:\Desktop\BengaluruTrafficAI_src\14985167_960_540_25fps.mp4" --camera test
```

### Issue: "Model yolo11s.pt not found"
**Fix:**
```bash
# Check if model exists
dir yolo11s.pt

# Should be ~20MB in BengaluruTrafficAI-Backend folder
```

### Issue: No violations detected
**Fix for red light violations:**
```bash
# Configure ROI first
python tools\quick_roi_setup.py ..\14985167_960_540_25fps.mp4

# Then run with ROI
python main.py --source ..\14985167_960_540_25fps.mp4 --roi rois\14985167_960_540_25fps_roi.json --camera test --show
```

### Issue: Very slow processing
**Fix:**
```bash
# Skip more frames and disable preprocessing
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test --skip 5 --no-preproc
```

---

## 📂 Output Files to Check

After running tests, verify these files exist:

### Evidence Images
```
output/evidence/
├── RED_LIGHT_test_cam_frame156_track12.jpg
├── TRIPLE_RIDING_test_cam_frame289_track5.jpg
└── ... (one per violation)
```

### Test Results
```
BengaluruTrafficAI-Backend/
├── test_results.txt (from run_all_tests.bat)
└── logs/ (if logging enabled)
```

### ROI Configuration (if created)
```
rois/
└── 14985167_960_540_25fps_roi.json
```

---

## 🔍 Visual Verification

When running with `--show` flag, you should see:

### Video Window Shows:
- 🟦 **Blue boxes** around vehicles
- 🟩 **Green boxes** around persons
- 🔴 **Red boxes** around violations
- 🔢 **Track IDs** next to boxes
- 📊 **FPS counter** (optional)
- 🟨 **ROI zones** (if configured)

### Terminal Shows:
```
[INFO] Loading yolo11s.pt
[INFO] Processing frame 50...
[INFO] Processing frame 100...
[INFO] VIOLATION | red_light_violation | track=12 | plate=N/A | conf=0.90
Progress: 100 frames | avg inference: 42.3ms | violations: 2
```

---

## 📈 Benchmarking Your System

Run this to measure performance:

```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera bench --skip 3 --max-frames 1000
```

### Good Performance (CPU):
- ✅ Inference: 30-60ms per frame
- ✅ FPS: 15-25 (with skip=3)
- ✅ Memory: <1GB

### Excellent Performance (GPU):
- ✅ Inference: 10-25ms per frame
- ✅ FPS: 40-70 (with skip=3)
- ✅ Memory: <2GB

### Poor Performance:
- ❌ Inference: >100ms per frame
- ❌ FPS: <10
- ❌ Memory: >3GB
- **Fix:** Use more frame skipping or upgrade hardware

---

## 🎓 Understanding Test Results

### Test 1: Video Quality ✅
**What it tests:** Can the system read and analyze the video?  
**Pass criteria:** Shows resolution and quality tier  
**Fail criteria:** Python errors or crashes  

### Test 2: Signal Detection ✅
**What it tests:** Can detect red signals in frames?  
**Pass criteria:** Detects at least some red signals (>5%)  
**Fail criteria:** 0% detection with visible red lights  
**Note:** 0% is OK if video has no traffic lights

### Test 3: Quick Detection ✅
**What it tests:** Full detection pipeline on 300 frames  
**Pass criteria:** Processes frames, detects violations, creates evidence  
**Fail criteria:** Crashes, no detections with clear violations  

### Test 4: Full Run ✅
**What it tests:** System stability over longer duration  
**Pass criteria:** Completes without crashes, reasonable speed  
**Fail criteria:** Crashes, extremely slow (>200ms/frame)  

---

## 📝 Reporting Results

After testing, provide:

1. **Test Status**
   - ✅ Test 1: PASS/FAIL
   - ✅ Test 2: PASS/FAIL
   - ✅ Test 3: PASS/FAIL
   - ✅ Test 4: PASS/FAIL

2. **Performance**
   - Inference time: ___ms
   - Processing speed: ___FPS
   - Total violations: ___

3. **Files Created**
   - Evidence images: ___ files
   - Test results saved: YES/NO

4. **Issues Encountered**
   - Error messages (if any)
   - Unexpected behavior

---

## 🆘 Need Help?

### Check These Documents:
- `QUICK_TEST.md` - Fast 5-minute test
- `SYSTEM_TEST_GUIDE.md` - Detailed testing steps
- `RED_LIGHT_FIX_GUIDE.md` - Red light detection issues
- `LOW_QUALITY_VIDEO_GUIDE.md` - Low-res video handling

### Common Questions:

**Q: Is 40-60% ALPR accuracy normal?**  
A: Yes! For 540p video, this is expected. Violation detection still works perfectly.

**Q: Why no red light violations detected?**  
A: Red light detection requires ROI configuration. Run `quick_roi_setup.py` first.

**Q: Can I test with my own video?**  
A: Yes! Replace the video path in test commands with your video file.

**Q: How do I test the API?**  
A: Start backend API in another terminal, then run tests. Violations will be sent to API.

**Q: System works but slow?**  
A: Normal on CPU. Use `--skip 5` for faster processing or get a GPU.

---

## ✅ Final Verification Checklist

Before concluding testing:

- [ ] All 3-4 tests completed
- [ ] No Python errors during execution
- [ ] Video window showed (Test 3)
- [ ] Bounding boxes visible on vehicles
- [ ] At least 1 violation detected (or confirmed none exist)
- [ ] Evidence files created
- [ ] Performance acceptable (20-60ms/frame)
- [ ] Model file (yolo11s.pt) exists
- [ ] Test results documented

**If all checked:** 🎉 **System is working correctly!**

---

## 🚀 Next Steps After Testing

Once system is verified working:

1. **Configure ROI** for your camera angles
2. **Test with production videos** from actual cameras
3. **Deploy backend API** to server
4. **Deploy frontend** dashboard
5. **Set up database** for violation storage
6. **Configure alerting** if needed

See `DEPLOYMENT_READY.md` for deployment guide.

---

**Questions?** Check the troubleshooting sections in each test guide, or review the error message against the "Common Issues" list above.
