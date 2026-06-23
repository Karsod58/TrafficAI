# 🎯 Complete Testing Examples - Step by Step

## 🚀 Quick Start: Test Everything in 10 Minutes

### Step 1: Test Your Current Video (3 minutes)

```bash
cd D:\Desktop\BengaluruTrafficAI_src\BengaluruTrafficAI-Backend

python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_run1 --skip 3 --max-frames 300
```

**What to check:**
- Console shows "Loading yolo11s.pt" ✅
- Console shows "Processing frame..." ✅
- Console shows "VIOLATION | ..." (if violations exist) ✅
- Console shows "PIPELINE COMPLETE" ✅

**Check evidence:**
```bash
dir output\evidence\
```

---

### Step 2: Generate Sample Dashboard Data (2 minutes)

```bash
# Make sure backend API is running in another terminal:
# uvicorn api.app:app --reload --port 8000

python test_data_generator.py quick
```

**What happens:**
- Creates 20 sample violations
- Sends to API
- Shows in dashboard

**View results:**
- Open http://localhost:3000
- Check Dashboard tab
- Check Violations tab
- Check Analytics tab

---

### Step 3: Test Frontend Features (5 minutes)

With backend + frontend running:

1. **Dashboard Tab**
   - Should show recent violations
   - Should show evidence images
   - Should update automatically

2. **Violations Tab**
   - Search for a plate number
   - Filter by violation type
   - Sort by date/confidence

3. **Analytics Tab**
   - View violation trends chart
   - Check violation type distribution
   - See camera performance

4. **Upload Tab** (Optional)
   - Upload your test video
   - Watch processing status
   - See results appear

---

## 📊 Example Test Scenarios

### Example 1: Basic Traffic Monitoring

**Scenario:** Monitor a busy intersection

**Command:**
```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera busy_junction --skip 2 --max-frames 500
```

**Expected Output:**
```
[INFO] Loading yolo11s.pt
[INFO] Processing...

Progress: 100 frames | avg inference: 42.3ms | violations: 3 | active tracks: 12
Progress: 200 frames | avg inference: 41.8ms | violations: 7 | active tracks: 15

[INFO] VIOLATION | triple_riding | track=8 | plate=N/A | conf=0.88
[INFO] Evidence saved: output/evidence/TRIPLE_RIDING_busy_junction_frame245_track8.jpg

PIPELINE COMPLETE
  Frames processed : 166
  Violations found : 8
  Avg inference    : 42.1 ms/frame
  
  Violation Breakdown:
    triple_riding           : 5
    wrong_side_driving      : 2
    stop_line_violation     : 1
```

**Success:** ✅ Violations detected, evidence saved

---

### Example 2: Red Light Monitoring

**Scenario:** Catch red light violations at intersection

**Step 1: Configure ROI**
```bash
python tools\quick_roi_setup.py ..\14985167_960_540_25fps.mp4
```

**Interactive Steps:**
1. Video first frame appears
2. Click 4 corners of junction (signal box)
3. Press 'n'
4. Click 2 points for stop line
5. Press 's' to save

**Step 2: Run Detection**
```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --roi rois\14985167_960_540_25fps_roi.json --camera redlight_test --skip 3 --max-frames 500
```

**Expected Output:**
```
[INFO] ROI loaded: 1 signal_box, 1 stop_line
...
[INFO] VIOLATION | red_light_violation | track=24 | plate=KA01AB1234 | conf=0.90
[INFO] Evidence saved: output/evidence/RED_LIGHT_redlight_test_frame389_track24.jpg
```

**Success:** ✅ Red light violations detected with ROI

---

### Example 3: License Plate Recognition Test

**Scenario:** Test ALPR accuracy on your video

**Command:**
```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera alpr_test --skip 2 --max-frames 800
```

**Watch console for:**
```
[INFO] VIOLATION | triple_riding | track=12 | plate=KA05CD5678 | conf=0.88
[INFO] VIOLATION | wrong_side | track=24 | plate=N/A | conf=0.85
[INFO] VIOLATION | triple_riding | track=37 | plate=KA12AB9876 | conf=0.90
```

**Count results:**
- Violations WITH plates: ___
- Violations WITHOUT plates (N/A): ___
- ALPR Success Rate: ___ %

**For 960x540 video:** 40-60% is GOOD

---

### Example 4: Performance Testing

**Scenario:** Measure system performance

**Command:**
```bash
python main.py --source ..\14985167_960_540_25fps.mp4 --camera perf_test --skip 3 --max-frames 1000
```

**Record these numbers:**
```
PIPELINE COMPLETE
  Frames processed : 333
  Violations found : 15
  Avg inference    : 45.2 ms/frame  ← Record this
  
  Violation counts...
```

**Performance Benchmarks:**

| Resolution | Expected FPS | Expected Inference |
|------------|-------------|-------------------|
| 360p | 25-35 FPS | 25-40ms |
| 540p | 20-30 FPS | 30-50ms |
| 720p | 15-25 FPS | 40-70ms |
| 1080p | 12-20 FPS | 50-85ms |

**Your Results:**
- Resolution: 960x540
- FPS: ___ (calculate from inference time)
- Inference: ___ ms

**Success:** ✅ Within expected range

---

### Example 5: Generate Test Data for Dashboard

**Scenario:** Populate dashboard with sample data

**Quick 20 violations:**
```bash
python test_data_generator.py quick
```

**Full 100 violations:**
```bash
python test_data_generator.py full
```

**Realistic distribution:**
```bash
python test_data_generator.py distribution
```

**Hourly pattern (last 2 days):**
```bash
python test_data_generator.py hourly 2
```

**Output:**
```
======================================================================
   Generating 20 sample violations (last 2 hours)
======================================================================

✓   1/20 | triple_riding            | cam_01 | KA01AB1234
✓   2/20 | red_light_violation      | cam_02 | KA05CD5678
✓   3/20 | wrong_side_driving       | cam_01 | N/A
...
✓  20/20 | phone_usage              | cam_03 | KA15MN6789

======================================================================
   SUMMARY
======================================================================
Total generated:     20
Successfully created: 20 ✓
Failed:              0 ✗

✅ Test data created successfully!

View violations:
  Dashboard: http://localhost:3000
  API:       http://localhost:8000/violations
  Stats:     http://localhost:8000/violations/stats
```

**Success:** ✅ Dashboard shows data

---

### Example 6: End-to-End Workflow Test

**Scenario:** Complete workflow from video to dashboard

**Terminal 1: Start Backend**
```bash
cd BengaluruTrafficAI-Backend
uvicorn api.app:app --reload --port 8000
```

**Terminal 2: Start Frontend**
```bash
cd BengaluruTrafficAI-Frontend
npm start
```

**Terminal 3: Process Video**
```bash
cd BengaluruTrafficAI-Backend
python main.py --source ..\14985167_960_540_25fps.mp4 --camera workflow_test --skip 3 --max-frames 300
```

**Open Browser:**
http://localhost:3000

**Watch:**
- Violations appear in Dashboard (real-time)
- Evidence images load
- Analytics update
- Stats increase

**Success:** ✅ Full pipeline working

---

## 📹 Download Sample Videos

### Option 1: Pexels (Free, No Login)

1. Go to: https://www.pexels.com/search/videos/traffic/
2. Search: "traffic india" or "busy road"
3. Download videos like:
   - "Busy Traffic in India"
   - "Motorcycles at Traffic Light"
   - "Highway Traffic"

### Option 2: Pixabay (Free, No Login)

1. Go to: https://pixabay.com/videos/search/traffic/
2. Download any traffic video
3. Place in project root

### Option 3: Use Your Current Video

You already have `14985167_960_540_25fps.mp4` - use it!

---

## 🎨 Frontend Testing Checklist

With backend running and data generated:

### Dashboard Tab ✅
- [ ] Shows recent violations
- [ ] Evidence images load
- [ ] Violation cards have all details
- [ ] Real-time updates work
- [ ] No errors in console

### Violations List Tab ✅
- [ ] Shows violations table
- [ ] Pagination works
- [ ] Search works (plate number)
- [ ] Filter by type works
- [ ] Filter by camera works
- [ ] Sort by date/confidence works
- [ ] Approve/Reject buttons work

### Analytics Tab ✅
- [ ] Hourly trends chart displays
- [ ] Violation type chart displays
- [ ] Camera performance shows
- [ ] Heatmap displays (if location data)
- [ ] Stats cards show numbers
- [ ] No "undefined" errors

### Upload Tab ✅
- [ ] Drag-and-drop works
- [ ] File upload starts
- [ ] Progress shows
- [ ] Job status updates
- [ ] Completed jobs show results
- [ ] URL upload works (if enabled)

### Camera View Tab ✅
- [ ] Camera list shows
- [ ] Camera cards have info
- [ ] Status indicators work
- [ ] Recent violations per camera

---

## 🧪 API Testing Examples

### Test 1: Get All Violations
```bash
curl http://localhost:8000/violations
```

**Expected:** JSON array of violations

### Test 2: Get Stats
```bash
curl http://localhost:8000/violations/stats
```

**Expected:**
```json
{
  "total_violations": 50,
  "pending_review": 25,
  "approved": 20,
  "rejected": 5,
  "today_violations": 8
}
```

### Test 3: Get Analytics
```bash
curl http://localhost:8000/analytics/hourly
```

**Expected:** Hourly violation counts

### Test 4: Upload Video (API)
```bash
curl -X POST "http://localhost:8000/upload/video" -F "file=@../14985167_960_540_25fps.mp4" -F "camera_id=api_test"
```

**Expected:** Job ID returned

### Test 5: Check Upload Status
```bash
curl http://localhost:8000/upload/status/<job_id>
```

**Expected:** Processing status

---

## 📊 Test Results Template

Copy this to record your results:

```
=== TEST RESULTS ===
Date: __________
Tester: __________

VIDEO TEST:
[ ] Video loaded successfully
[ ] YOLO11 model loaded
[ ] Frames processed: ___
[ ] Violations detected: ___
[ ] Evidence files created: ___
[ ] Avg inference time: ___ ms
[ ] Performance: GOOD / ACCEPTABLE / SLOW

DATA GENERATION:
[ ] Test data generated
[ ] API received data
[ ] Dashboard shows data
[ ] Violations count: ___

FRONTEND:
[ ] Dashboard tab works
[ ] Violations list works
[ ] Analytics tab works
[ ] Upload tab works
[ ] Search/filter works
[ ] No console errors

API:
[ ] GET /violations works
[ ] GET /violations/stats works
[ ] POST /violations/ingest works
[ ] GET /analytics works

ISSUES FOUND:
_________________________
_________________________

OVERALL: PASS / FAIL
```

---

## 🎯 Quick Commands Reference

```bash
# Test with your video
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test --skip 3 --max-frames 300

# Generate 20 test violations
python test_data_generator.py quick

# Generate 100 test violations
python test_data_generator.py full

# Check evidence
dir output\evidence\

# Check API
curl http://localhost:8000/violations/stats

# Start backend
uvicorn api.app:app --reload --port 8000

# Start frontend
cd ..\BengaluruTrafficAI-Frontend & npm start

# Configure ROI
python tools\quick_roi_setup.py <video.mp4>
```

---

**Ready to test? Start with your video and the quick test data generator!** 🚀
