# 📦 Model Weights Download Guide

The YOLO model weight files are **not included in the repository** due to their large size (GitHub file size limits). You need to download them before running the system.

## 🎯 Required Models

### 1. YOLOv8s (Recommended for CPU)
- **File**: `yolov8s.pt`
- **Size**: ~22 MB
- **Download**: Automatically downloads on first run
- **Manual Download**: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt

### 2. YOLO11s (Latest, Better Accuracy)
- **File**: `yolo11s.pt`
- **Size**: ~20 MB
- **Download**: Automatically downloads on first run
- **Manual Download**: https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt

## 🚀 Quick Setup

### Option 1: Automatic Download (Recommended)

The models will automatically download when you first run the detection pipeline:

```bash
python main.py --source YOUR_VIDEO --camera cam_01
```

The Ultralytics library will download the model on first use.

### Option 2: Manual Download

If you want to download manually:

```bash
# Download YOLOv8s
curl -L -o yolov8s.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt

# Download YOLO11s
curl -L -o yolo11s.pt https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt
```

Or using Python:

```python
from ultralytics import YOLO

# This will auto-download if not present
model = YOLO('yolov8s.pt')
# or
model = YOLO('yolo11s.pt')
```

### Option 3: Using wget (Linux/Mac)

```bash
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt
```

## 📁 Model Placement

Place the downloaded `.pt` files in the backend root directory:

```
BengaluruTrafficAI-Backend/
├── yolov8s.pt    ← Place here
├── yolo11s.pt    ← Place here
├── main.py
├── requirements.txt
└── ...
```

## 🔍 Verify Installation

Check if models are present:

```bash
# Windows
dir *.pt

# Linux/Mac
ls -lh *.pt
```

Expected output:
```
yolov8s.pt    (20-25 MB)
yolo11s.pt    (18-22 MB)
```

## 🎛️ Model Selection

The system uses YOLOv8s by default. To use YOLO11s (better accuracy):

Edit `core/detector.py`:
```python
# Change this line:
self.model = YOLO("yolov8s.pt")

# To:
self.model = YOLO("yolo11s.pt")
```

## 📊 Model Comparison

| Model | Size | Speed (CPU) | Speed (GPU) | Accuracy |
|-------|------|-------------|-------------|----------|
| YOLOv8s | 22 MB | 15-20 FPS | 60+ FPS | Good |
| YOLO11s | 20 MB | 18-25 FPS | 70+ FPS | Better |
| YOLOv8m | 50 MB | 10-15 FPS | 50+ FPS | Better |
| YOLO11m | 48 MB | 12-18 FPS | 60+ FPS | Best |

For prototype/demo: **YOLOv8s** or **YOLO11s** (small models)  
For production with GPU: **YOLO11m** (medium model)

## 🐛 Troubleshooting

### Model download fails

```bash
# Set proxy if needed
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port

# Then run again
python main.py --source VIDEO
```

### Model not found error

```
FileNotFoundError: yolov8s.pt not found
```

**Solution**: Download manually using one of the options above.

### Slow detection

**Problem**: Model is slow on CPU  
**Solution**: 
1. Use smaller model (yolov8n.pt - nano)
2. Increase frame skip: `--skip 5`
3. Use GPU if available

## 🌐 Alternative Model Sources

If GitHub releases are slow, you can also find models at:

1. **Ultralytics Hub**: https://hub.ultralytics.com/
2. **Roboflow Universe**: https://universe.roboflow.com/
3. **Direct from Ultralytics**: https://docs.ultralytics.com/models/

## 📝 Custom Models

To use your own trained YOLO model:

```python
# Place your custom model in the backend folder
model = YOLO('your_custom_model.pt')
```

Ensure it's trained on similar classes (car, person, motorcycle, etc.).

## ✅ Verification Script

Create a test script to verify models work:

```python
# test_models.py
from ultralytics import YOLO

print("Testing YOLOv8s...")
model_v8 = YOLO('yolov8s.pt')
print("✓ YOLOv8s loaded successfully")

print("Testing YOLO11s...")
model_v11 = YOLO('yolo11s.pt')
print("✓ YOLO11s loaded successfully")

print("\nAll models ready!")
```

Run: `python test_models.py`

---

**Note**: Model files are NOT included in the git repository due to GitHub's 100MB file size limit. They must be downloaded separately.
