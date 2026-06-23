# ⚡ Quick System Test (5 Minutes)

## Run These 3 Commands in Your Terminal (with venv activated)

### 1️⃣ Test Video Quality (30 seconds)
```bash
cd D:\Desktop\BengaluruTrafficAI_src\BengaluruTrafficAI-Backend
python core\low_res_handler.py ..\14985167_960_540_25fps.mp4
```

**Look for:**
- ✅ Resolution: 960x540
- ✅ Quality Tier: LOW
- ✅ No errors

---

### 2️⃣ Test Signal Detection (1 minute)
```bash
python test_signal_detection.py ..\14985167_960_540_25fps.mp4
```

**Look for:**
- ✅ Video window appears
- ✅ Shows detection region (yellow box)
- ✅ Some red signals detected (>0%)
- ❌ If 0% detected, video might not have red lights

---

### 3️⃣ Test Full Detection (3 minutes)
```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_cam --skip 3 --max-frames 300 --show
```

**Look for:**
- ✅ "Loading yolo11s.pt" message
- ✅ "Processing..." messages
- ✅ Video window with bounding boxes
- ✅ "VIOLATION | ..." messages (if violations exist)
- ✅ "PIPELINE COMPLETE" at end
- ✅ Evidence files created

**Press 'Q' to stop the video window**

---

## Check Results

### A. Check Evidence Files
```bash
dir output\evidence\
```

**Should see:** JPG files like `RED_LIGHT_test_cam_frame123_track5.jpg`

### B. Check What Was Detected
```bash
type test_results.txt
```

Or just scroll up in your terminal to see the summary.

---

## ✅ System is WORKING if:

1. All 3 commands run without Python errors
2. Video window shows (Test 3)
3. Bounding boxes appear on vehicles
4. At least 1 evidence file created (if video has violations)

---

## ❌ System has ISSUES if:

1. **"ModuleNotFoundError"** → Run: `pip install -r requirements.txt`
2. **"Cannot open video"** → Check video path is correct
3. **"Model not found"** → Check `yolo11s.pt` exists in Backend folder
4. **No violations detected** → May be normal if video has no violations, OR ROI not configured

---

## 🆘 Quick Fixes

### No violations detected for red lights:
```bash
python tools\quick_roi_setup.py ..\14985167_960_540_25fps.mp4
# Then re-run Test 3 with --roi parameter
```

### Very slow processing:
```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test --skip 5 --no-preproc
```

### Can't see video window on Windows:
```bash
# Remove --show flag
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test --skip 3 --max-frames 300
```

---

## 📊 Expected Output (Test 3)

```
[INFO] BengaluruTrafficAI — Starting pipeline
[INFO] Source: ..\14985167_960_540_25fps.mp4
[INFO] detector: Loading yolo11s.pt

📹 VIDEO QUALITY REPORT
Resolution: 960x540
Quality Tier: LOW

[INFO] Processing frame 1...
[INFO] Processing frame 50...
Progress: 100 frames | avg inference: 42.3ms | violations: 2 | active tracks: 8

[INFO] VIOLATION | red_light_violation | track=12 | plate=N/A | conf=0.90
[INFO] Evidence saved: output/evidence/RED_LIGHT_test_cam_frame156_track12.jpg

PIPELINE COMPLETE
  Frames processed : 100
  Violations found : 3
  Avg inference    : 42.3 ms/frame
  
  Violation Breakdown:
    red_light_violation     : 2
    triple_riding           : 1
```

---

## Report Back

Tell me:
1. ✅ or ❌ for each test
2. Any error messages (copy-paste)
3. How many violations detected
4. How many evidence files created

That's all I need to know if the system works!
