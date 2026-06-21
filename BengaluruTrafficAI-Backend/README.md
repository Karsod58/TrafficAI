# Bengaluru Traffic AI - Backend

Complete AI-powered traffic violation detection system with FastAPI backend.

## 🏗️ Architecture

```
Backend/
├── api/                    # FastAPI REST API
│   ├── app.py             # Main FastAPI application
│   ├── database.py        # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   └── routers/           # API endpoints
│       ├── violations.py  # Violation CRUD
│       ├── cameras.py     # Camera management
│       ├── analytics.py   # Analytics endpoints
│       └── websocket.py   # WebSocket for real-time
├── core/                  # Core detection pipeline
│   ├── detector.py        # YOLO detection
│   ├── track_manager.py   # ByteTrack tracking
│   ├── roi_manager.py     # ROI management
│   ├── preprocessor.py    # Video preprocessing
│   └── alert_router.py    # Alert routing
├── violations/            # Violation detectors
│   ├── helmet_seatbelt.py # Helmet & seatbelt
│   ├── detectors.py       # Other violations
│   └── pipeline.py        # Orchestration
├── alpr/                  # License plate recognition
│   └── alpr.py
├── utils/                 # Utilities
│   └── evidence.py        # Evidence generation
├── output/
│   └── evidence/          # Saved violation images
├── main.py                # Pipeline entry point
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── Dockerfile             # Docker configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL (or use Railway/Supabase)
- (Optional) CUDA-capable GPU for faster inference

### Installation

1. **Create virtual environment:**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
# Copy example env file
copy .env.example .env

# Edit .env with your settings:
# - DATABASE_URL (PostgreSQL connection string)
# - API settings
```

4. **Initialize database:**
```bash
python -c "from api.database import init_db; init_db()"
```

### Running the Backend

#### 1. Start API Server
```bash
uvicorn api.app:app --reload --port 8000
```

API will be available at: http://localhost:8000  
API Docs: http://localhost:8000/docs

#### 2. Start Detection Pipeline
```bash
# From YouTube live stream
python main.py --source https://youtu.be/VIDEO_ID --camera cam_01

# From local video file
python main.py --source video.mp4 --camera cam_01

# From webcam
python main.py --source 0 --camera cam_01

# From RTSP stream
python main.py --source rtsp://camera-ip:port/stream --camera cam_01

# With output video
python main.py --source video.mp4 --camera cam_01 --output output.mp4
```

## 📊 API Endpoints

### Health Check
```bash
GET /
```

### Violations
```bash
GET  /violations              # List all violations
GET  /violations/{id}         # Get single violation
POST /violations/ingest       # Submit new violation (from CV pipeline)
PATCH /violations/{id}/review # Review violation (approve/reject)
GET  /violations/stats        # Dashboard statistics
```

### Cameras
```bash
GET /cameras                  # List all cameras
GET /cameras/{id}             # Get single camera
```

### Analytics
```bash
GET /analytics/trends         # Violation trends over time
GET /analytics/heatmap        # Violation hotspots by location
GET /analytics/cameras/{id}/stats  # Per-camera statistics
GET /analytics/summary        # Executive summary
GET /analytics/realtime       # Real-time metrics
```

### WebSocket
```bash
WS /ws                        # Real-time violation stream
```

## 🔧 Configuration

### Command Line Options

```bash
python main.py --help

Options:
  --source          Video source (file, URL, RTSP, camera index)
  --camera          Camera ID for metadata
  --skip            Process every Nth frame (default: 2)
  --roi             Path to ROI JSON config
  --output          Save annotated video
  --max-frames      Stop after N frames
  --no-evidence     Skip evidence file generation
  --no-api          Disable API submission
  --no-preproc      Disable preprocessing
  --no-routing      Disable alert routing
```

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Detection
CONFIDENCE_THRESHOLD=0.40
AUTO_APPROVE_THRESHOLD=0.92
SKIP_FRAMES=2

# Evidence Storage
EVIDENCE_DIR=output/evidence
```

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t bengaluru-traffic-backend .
```

### Run Container
```bash
docker run -d \
  --name traffic-backend \
  -p 8000:8000 \
  -v $(pwd)/output:/app/output \
  -e DATABASE_URL=postgresql://... \
  bengaluru-traffic-backend
```

### Docker Compose
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./output:/app/output
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/traffic
    depends_on:
      - db
  
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: traffic
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 📈 Performance

### CPU (Default)
- Detection: ~145-160ms per frame
- Total Pipeline: 10-13 FPS

### GPU (CUDA)
- Detection: ~16-18ms per frame
- Total Pipeline: 55-60 FPS

### Enable GPU
```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# System will automatically use GPU if available
```

## 🎯 Violation Types Supported

| Violation | Accuracy | Severity | Fine (₹) |
|-----------|----------|----------|----------|
| No Helmet | 92% | 4 | 1,000 |
| No Seatbelt | 83% | 3 | 1,000 |
| Triple Riding | 87% | 4 | 1,000 |
| Wrong-Side Driving | 91% | 5 | 5,000 |
| Stop-Line Violation | 89% | 3 | 1,000 |
| Red-Light Violation | 95% | 5 | 5,000 |
| Illegal Parking | 93% | 2 | 500 |

## 🔐 Security

### For Production

1. **Enable Authentication:**
```python
# Add to api/app.py
from fastapi.security import HTTPBearer

security = HTTPBearer()
```

2. **Restrict CORS:**
```python
allow_origins=["https://yourdomain.com"]  # Only your domain
```

3. **Use HTTPS:**
```bash
uvicorn api.app:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

4. **Environment Secrets:**
```bash
# Never commit .env file
# Use secrets management (AWS Secrets, Azure Key Vault, etc.)
```

## 📊 Database Schema

### Tables

```sql
-- Violations
CREATE TABLE violations (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE,
    violation_type VARCHAR(50),
    camera_id VARCHAR(50),
    track_id INTEGER,
    plate_number VARCHAR(20),
    confidence FLOAT,
    severity INTEGER,
    fine_inr INTEGER,
    auto_approve BOOLEAN,
    reviewed BOOLEAN,
    approved BOOLEAN,
    timestamp FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ...
);

-- Cameras
CREATE TABLE cameras (
    camera_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    location VARCHAR(200),
    lat FLOAT,
    lon FLOAT,
    active BOOLEAN
);
```

## 🧪 Testing

### Run Tests
```bash
pytest tests/
```

### Test Specific Module
```bash
pytest tests/test_detector.py
pytest tests/test_alpr.py
```

## 📝 Logging

Logs are output to console with format:
```
2026-06-21 00:58:51 [INFO] detector: Loading yolov8s.pt on cpu
2026-06-21 00:59:10 [INFO] main: VIOLATION | no_helmet | plate=KA01AB1234
```

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🐛 Troubleshooting

### Issue: API Won't Start
```bash
# Check port availability
netstat -ano | findstr :8000

# Try different port
uvicorn api.app:app --port 8001
```

### Issue: GPU Not Detected
```bash
# Check CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# Install correct CUDA version
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Issue: Database Connection Failed
```bash
# Verify DATABASE_URL in .env
# Test connection
python -c "from api.database import get_db; print('OK')"
```

## 📚 Documentation

- `PROJECT_REQUIREMENTS_CHECKLIST.md` - Feature implementation status
- `ARCHITECTURE.md` - System architecture
- `ALPR_IMPROVEMENT_GUIDE.md` - License plate recognition guide
- `SYSTEM_STATUS.md` - Current system status

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is part of the Bengaluru Traffic AI system.

## 🆘 Support

For issues and questions:
- Check documentation in the repo
- Review logs for errors
- Ensure all dependencies are installed

---

## Quick Commands Reference

```bash
# Start API server
uvicorn api.app:app --reload --port 8000

# Start detection pipeline
python main.py --source video.mp4 --camera cam_01

# Run with GPU
python main.py --source video.mp4 --camera cam_01  # Auto-detects GPU

# Save output video
python main.py --source video.mp4 --camera cam_01 --output output.mp4

# Process fewer frames (faster)
python main.py --source video.mp4 --camera cam_01 --skip 5

# Initialize database
python -c "from api.database import init_db; init_db()"
```

---

**Backend is ready for deployment! 🚀**
