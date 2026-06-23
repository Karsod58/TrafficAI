# 🎬 Example Test Scenarios for BengaluruTrafficAI

## 📹 Sample Videos to Test

### Option 1: Use Your Current Video
You already have: `14985167_960_540_25fps.mp4`

**Run test:**
```bash
cd BengaluruTrafficAI-Backend
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test_cam --skip 3 --max-frames 500
```

---

### Option 2: Download Free Traffic Videos

Here are sources for FREE traffic violation test videos:

#### **A. Pexels (Free Stock Videos)**
1. Go to: https://www.pexels.com/search/videos/traffic/
2. Search for: "traffic intersection", "busy road", "motorcycle traffic"
3. Download MP4 files (free, no attribution required)

**Example searches:**
- "India traffic" → Shows bikes, cars, mixed traffic
- "traffic signal" → Shows red lights and violations
- "highway traffic" → Shows vehicles, lane changes

**Recommended videos:**
- Traffic intersection with signals
- Busy motorcycle traffic
- Multi-lane highway

#### **B. Pixabay (Free Videos)**
1. Go to: https://pixabay.com/videos/search/traffic/
2. Download any traffic video
3. Place in project root folder

#### **C. YouTube (for testing only)**
```bash
# System supports YouTube URLs directly
python main.py --source "https://www.youtube.com/watch?v=<VIDEO_ID>" --camera youtube_test --skip 5
```

**Note:** YouTube URLs may be blocked by bot detection. Better to download first.

---

### Option 3: Create Test Video with Webcam

```bash
# Use your webcam to create test video
python main.py --source 0 --camera webcam_test --skip 2 --max-frames 300
```

This will process your webcam feed for testing object detection.

---

## 🧪 Test Scenarios

### Scenario 1: Basic Object Detection Test
**Purpose:** Verify vehicles and persons are detected

**Video needed:** Any traffic video with cars, bikes, people

**Command:**
```bash
python main.py --source <video.mp4> --camera scenario1 --skip 3 --max-frames 200
```

**Expected results:**
- ✅ Detects cars (blue boxes)
- ✅ Detects motorcycles (blue boxes)
- ✅ Detects persons (green boxes)
- ✅ Assigns tracking IDs
- ✅ Creates bounding boxes

**Success criteria:** Console shows detections, tracking IDs assigned

---

### Scenario 2: Triple Riding Detection
**Purpose:** Test triple riding violation detection

**Video needed:** Video with 3+ people on one motorcycle

**Command:**
```bash
python main.py --source <video.mp4> --camera scenario2_triple --skip 2 --max-frames 300
```

**How it works:**
- System detects motorcycle
- Counts persons sitting on/near bike
- If count > 2 → VIOLATION

**Expected results:**
- ✅ "VIOLATION | triple_riding | track=X | conf=0.XX"
- ✅ Evidence image saved
- ✅ Shows 3+ persons on bike

**Success criteria:** Triple riding violation logged, evidence created

---

### Scenario 3: Red Light Violation
**Purpose:** Test red light detection

**Video needed:** Traffic intersection with visible red light

**Step 1: Configure ROI**
```bash
python tools\quick_roi_setup.py <video.mp4>
# Draw signal box (junction area)
# Draw stop line
# Press 's' to save
```

**Step 2: Run detection**
```bash
python main.py --source <video.mp4> --roi rois\<video>_roi.json --camera scenario3_redlight --skip 3
```

**Expected results:**
- ✅ "VIOLATION | red_light_violation | track=X"
- ✅ Vehicles crossing during red detected
- ✅ Evidence shows vehicle in junction during red

**Success criteria:** Red light violations detected when vehicles enter junction during red signal

---

### Scenario 4: Wrong Side Driving
**Purpose:** Test wrong-side detection

**Video needed:** Video with vehicles in opposite lanes

**Requires:** ROI configuration with lane directions

**Command:**
```bash
python main.py --source <video.mp4> --roi rois\lanes_roi.json --camera scenario4_wrongside --skip 3
```

**Expected results:**
- ✅ "VIOLATION | wrong_side_driving | track=X"
- ✅ Vehicle moving opposite to lane direction

**Success criteria:** Vehicles going wrong way are flagged

---

### Scenario 5: License Plate Recognition
**Purpose:** Test ALPR accuracy

**Video needed:** HD video (720p+) with clear license plates

**Command:**
```bash
python main.py --source <video_hd.mp4> --camera scenario5_alpr --skip 2 --max-frames 500
```

**Expected results:**
- ✅ Some plates detected (40-85% depending on quality)
- ✅ "plate=KA01AB1234" in violations
- ✅ Some show "plate=N/A" (quality checks working)

**Success criteria:** At least 40-60% of clear plates detected

---

### Scenario 6: Low Quality Video
**Purpose:** Test 360p/480p handling

**Video needed:** Low resolution video (360p-480p)

**Command:**
```bash
python main.py --source <video_360p.mp4> --camera scenario6_lowres --skip 5 --max-frames 300
```

**Expected results:**
- ✅ Quality auto-detected (ULTRA_LOW or LOW)
- ✅ Preprocessing enabled automatically
- ✅ Violations still detected (85-90%)
- ✅ ALPR limited (10-60%)

**Success criteria:** System processes and detects violations despite low quality

---

### Scenario 7: Performance Benchmark
**Purpose:** Measure system performance

**Command:**
```bash
python main.py --source <video.mp4> --camera scenario7_perf --skip 3 --max-frames 1000
```

**Measure:**
- FPS (frames per second)
- Inference time (ms per frame)
- Memory usage
- Violations per minute

**Expected results:**
- ✅ CPU: 15-25 FPS
- ✅ Inference: 30-60ms
- ✅ Memory: <1GB

**Success criteria:** Performance within expected ranges

---

### Scenario 8: Long Video Processing
**Purpose:** Test system stability over time

**Video needed:** Long video (5-10 minutes)

**Command:**
```bash
python main.py --source <long_video.mp4> --camera scenario8_long --skip 5
```

**Expected results:**
- ✅ Processes entire video without crashing
- ✅ Consistent performance throughout
- ✅ Multiple violations detected
- ✅ Evidence files created

**Success criteria:** Completes full video, no crashes, steady performance

---

## 🎯 Quick Test Suite

Run all scenarios in sequence:

```bash
# Scenario 1: Basic detection
python main.py --source ..\14985167_960_540_25fps.mp4 --camera s1_basic --skip 3 --max-frames 200

# Scenario 2: Triple riding (if video has bikes with multiple riders)
python main.py --source ..\14985167_960_540_25fps.mp4 --camera s2_triple --skip 2 --max-frames 300

# Scenario 3: Red light (need ROI first)
python tools\quick_roi_setup.py ..\14985167_960_540_25fps.mp4
python main.py --source ..\14985167_960_540_25fps.mp4 --roi rois\14985167_960_540_25fps_roi.json --camera s3_redlight --skip 3

# Scenario 6: Low-res handling (your video is 540p - MEDIUM quality)
python main.py --source ..\14985167_960_540_25fps.mp4 --camera s6_lowres --skip 5 --max-frames 300

# Scenario 7: Performance
python main.py --source ..\14985167_960_540_25fps.mp4 --camera s7_perf --skip 3 --max-frames 1000

# Check results
dir output\evidence\
```

---

## 📊 Test Data Generator

I'll create a script to generate sample test data:

### Generate Sample Violations (For Frontend Testing)

```python
# test_data_generator.py
import requests
import random
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

violation_types = [
    "triple_riding",
    "red_light_violation",
    "wrong_side_driving",
    "stop_line_violation",
    "illegal_parking",
    "no_helmet",
    "phone_usage"
]

cameras = ["cam_01", "cam_02", "cam_03", "cam_04"]

def generate_sample_violation():
    """Generate a sample violation for testing"""
    return {
        "violation_type": random.choice(violation_types),
        "camera_id": random.choice(cameras),
        "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat(),
        "confidence": round(random.uniform(0.7, 0.95), 2),
        "plate_number": f"KA{random.randint(1,99):02d}{random.choice(['AB','CD','EF','GH'])}{random.randint(1000,9999)}" if random.random() > 0.3 else None,
        "location": {"lat": 12.9716 + random.uniform(-0.1, 0.1), "lon": 77.5946 + random.uniform(-0.1, 0.1)},
        "metadata": {
            "vehicle_type": random.choice(["car", "motorcycle", "bus", "truck", "auto"]),
            "frame_number": random.randint(100, 10000),
            "track_id": random.randint(1, 100)
        }
    }

def populate_test_data(count=50):
    """Populate database with sample violations"""
    print(f"Generating {count} sample violations...")
    
    for i in range(count):
        violation = generate_sample_violation()
        try:
            response = requests.post(f"{API_URL}/violations/ingest", json=violation)
            if response.status_code == 200:
                print(f"✓ Created violation {i+1}/{count}")
            else:
                print(f"✗ Failed violation {i+1}: {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print("\nDone! Check dashboard to see violations.")

if __name__ == "__main__":
    populate_test_data(50)
```

**Usage:**
```bash
# Make sure API is running first
python test_data_generator.py
```

---

## 🎨 Visual Test Cases

### Test Case 1: Dashboard Display
**Purpose:** Verify frontend shows data correctly

**Steps:**
1. Generate sample data (above script)
2. Open frontend: http://localhost:3000
3. Check Dashboard tab shows violations
4. Check Analytics tab shows charts
5. Check Camera View shows cameras

**Success criteria:** All tabs display data, no errors

---

### Test Case 2: Real-Time Updates
**Purpose:** Test WebSocket real-time updates

**Steps:**
1. Open dashboard
2. Run detection: `python main.py --source video.mp4 --camera cam_01`
3. Watch Dashboard tab for real-time violation cards

**Success criteria:** New violations appear automatically without refresh

---

### Test Case 3: Search & Filter
**Purpose:** Test violations list functionality

**Steps:**
1. Open Violations tab
2. Search for plate number
3. Filter by violation type
4. Filter by camera
5. Filter by date range

**Success criteria:** Filtering works, results update correctly

---

## 📦 Sample Test Dataset

I'll create a CSV with sample violations you can import:

```csv
violation_type,camera_id,timestamp,confidence,plate_number,vehicle_type,location_lat,location_lon
triple_riding,cam_01,2026-06-22T10:15:30,0.88,KA01AB1234,motorcycle,12.9716,77.5946
red_light_violation,cam_02,2026-06-22T10:20:45,0.92,KA05CD5678,car,12.9750,77.6000
wrong_side_driving,cam_01,2026-06-22T10:25:12,0.85,,motorcycle,12.9716,77.5946
stop_line_violation,cam_03,2026-06-22T10:30:00,0.90,KA02EF9012,auto,12.9800,77.6100
triple_riding,cam_01,2026-06-22T10:35:22,0.87,KA03GH3456,motorcycle,12.9716,77.5946
illegal_parking,cam_04,2026-06-22T10:40:15,0.83,KA12IJ7890,car,12.9650,77.5900
red_light_violation,cam_02,2026-06-22T10:45:50,0.91,KA08KL2345,bus,12.9750,77.6000
no_helmet,cam_01,2026-06-22T10:50:30,0.89,,motorcycle,12.9716,77.5946
phone_usage,cam_03,2026-06-22T10:55:10,0.86,KA15MN6789,car,12.9800,77.6100
triple_riding,cam_01,2026-06-22T11:00:45,0.90,KA07OP1234,motorcycle,12.9716,77.5946
```

Save as `sample_violations.csv` and import via API.

---

## 🚀 Complete Test Workflow

### Full System Test (End-to-End)

**Day 1: Setup & Basic Tests**
```bash
# 1. Test with your video
python main.py --source ..\14985167_960_540_25fps.mp4 --camera test1 --skip 3 --max-frames 300

# 2. Check evidence
dir output\evidence\

# 3. Configure ROI for red light
python tools\quick_roi_setup.py ..\14985167_960_540_25fps.mp4

# 4. Test with ROI
python main.py --source ..\14985167_960_540_25fps.mp4 --roi rois\14985167_960_540_25fps_roi.json --camera test2 --skip 3 --max-frames 300
```

**Day 2: Download & Test New Videos**
```bash
# 1. Download traffic video from Pexels/Pixabay
# 2. Place in project root
# 3. Test quality detection
python core\low_res_handler.py new_video.mp4

# 4. Run detection
python main.py --source new_video.mp4 --camera test3 --skip 3 --max-frames 500
```

**Day 3: Frontend Testing**
```bash
# 1. Generate sample data
python test_data_generator.py

# 2. Start backend
uvicorn api.app:app --reload --port 8000

# 3. Start frontend
cd ..\BengaluruTrafficAI-Frontend
npm start

# 4. Open http://localhost:3000
# 5. Test all features
```

---

## 📝 Test Checklist

- [ ] Basic object detection works
- [ ] Triple riding detected (if video has it)
- [ ] Red light violation detected (with ROI)
- [ ] License plates recognized (40-60%+)
- [ ] Low quality videos processed
- [ ] Evidence images created
- [ ] API receives violations
- [ ] Frontend dashboard displays data
- [ ] Real-time updates work
- [ ] Search/filter functions
- [ ] Performance acceptable (20-60ms/frame)
- [ ] System stable over long videos
- [ ] No crashes or errors

---

## 🆘 If You Need More Test Videos

**Free sources:**
1. **Pexels:** https://www.pexels.com/videos/
2. **Pixabay:** https://pixabay.com/videos/
3. **Videvo:** https://www.videvo.net/
4. **Mixkit:** https://mixkit.co/free-stock-video/

**Search terms:**
- "traffic intersection"
- "busy road India"
- "motorcycle traffic"
- "highway traffic"
- "city traffic"

**Download as MP4, place in project root, and test!**

---

**Ready to test? Start with your current video using the commands above!** 🎯
