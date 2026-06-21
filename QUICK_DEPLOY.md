# ⚡ Quick Deploy Guide - Bengaluru Traffic AI

## 🎯 3-Step Deployment

### Step 1: Backend (5 minutes)

```bash
cd BengaluruTrafficAI-Backend

# Setup environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install
pip install -r requirements.txt

# Configure database (create .env file)
echo DATABASE_URL=postgresql://user:pass@localhost:5432/bengaluru_traffic > .env

# Start API
uvicorn api.app:app --reload --port 8000
```

**Verify**: Open http://localhost:8000 (should show `{"service": "BengaluruTrafficAI", "status": "running"}`)

### Step 2: Frontend (3 minutes)

```bash
cd BengaluruTrafficAI-Frontend

# Install
npm install

# Start
npm start
```

**Verify**: Open http://localhost:3000 (dashboard loads, shows "Live" connection indicator)

### Step 3: Test Upload Feature (2 minutes)

1. Go to **Upload** tab in dashboard
2. Either:
   - **Drag & drop** a video file (MP4, AVI, MOV)
   - OR paste a **YouTube URL**
3. Configure settings (camera ID, skip frames)
4. Click **Upload & Process** or **Submit URL & Process**
5. Watch job status update in real-time

**Done!** 🎉

---

## 🚀 Production Deployment

### Docker (Recommended)

```bash
# Build images
cd BengaluruTrafficAI-Backend
docker build -t traffic-backend .

cd ../BengaluruTrafficAI-Frontend
docker build -t traffic-frontend .

# Run with docker-compose
cd ..
docker-compose up -d
```

### Cloud Platforms

#### Backend → Railway
1. Create Railway account
2. New Project → Deploy from GitHub
3. Add PostgreSQL database
4. Set root directory: `BengaluruTrafficAI-Backend`
5. Deploy

#### Frontend → Vercel
1. Create Vercel account
2. Import GitHub repo
3. Set root directory: `BengaluruTrafficAI-Frontend`
4. Add env: `REACT_APP_API_URL=https://your-backend.railway.app`
5. Deploy

---

## 📋 Pre-Deployment Checklist

### Backend ✅
- [x] All routers integrated (violations, cameras, analytics, health, upload)
- [x] Database configured
- [x] Evidence folder created (`output/evidence/`)
- [x] Upload folder created (`uploads/`)
- [x] Environment variables set
- [x] Requirements installed

### Frontend ✅
- [x] All 5 views working (Dashboard, Violations, Cameras, Analytics, Upload)
- [x] WebSocket connection configured
- [x] API URL set correctly
- [x] Dependencies installed
- [x] Build tested (`npm run build`)

---

## 🧪 Quick Tests

### Backend Test
```bash
# Health check
curl http://localhost:8000/

# Upload endpoint
curl http://localhost:8000/upload/jobs

# WebSocket
# Should connect: ws://localhost:8000/ws
```

### Frontend Test
1. Dashboard loads
2. Connection indicator shows "Live"
3. Upload tab appears in navigation
4. All charts render
5. No console errors

---

## 🔥 Features Ready

✅ **7 Violation Types** (helmet, seatbelt, triple riding, wrong lane, signal, overspeeding, phone)  
✅ **Real-time Dashboard** with WebSocket  
✅ **Video Upload** (file + URL)  
✅ **Traffic Health Score**  
✅ **Multi-camera Monitoring**  
✅ **Analytics & Charts**  
✅ **Approve/Reject Workflow**

---

## 📞 Common Issues

**Backend won't start**
- Check Python version (3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check database connection

**Frontend won't connect**
- Ensure backend running on port 8000
- Check proxy settings in `package.json`
- Clear browser cache

**Upload not working**
- Verify `uploads/` folder exists and has write permissions
- Check file size < 500MB
- Ensure `python main.py` works standalone

---

## 🎯 Next Steps

1. Configure production database (Railway PostgreSQL)
2. Set up domain names
3. Enable HTTPS
4. Add authentication
5. Configure monitoring

---

**Time to Deploy**: ~10 minutes  
**Status**: 🟢 Ready for Production
