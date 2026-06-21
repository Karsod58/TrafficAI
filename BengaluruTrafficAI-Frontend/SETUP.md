# Dashboard Setup & Installation Guide

## Prerequisites

Before setting up the dashboard, ensure you have:

- ✅ **Node.js** (v16.0 or higher) - [Download](https://nodejs.org/)
- ✅ **npm** (comes with Node.js) or **yarn**
- ✅ **Python 3.8+** (for backend API)
- ✅ **Backend API running** on `http://localhost:8000`

## Installation Steps

### Step 1: Navigate to Dashboard Directory

```bash
cd bengaluru_traffic_ai/dashboard
```

### Step 2: Install Dependencies

```bash
npm install
```

This will install:
- React 18
- TypeScript
- Recharts (for charts)
- Axios (for API calls)
- Lucide React (for icons)
- Date-fns (for date formatting)

**Expected output:**
```
added 1364 packages in 30s
```

### Step 3: Verify Backend API is Running

Open a new terminal and start the backend:

```bash
cd bengaluru_traffic_ai
uvicorn api.app:app --reload --port 8000
```

Verify it's running by opening: `http://localhost:8000`

You should see:
```json
{
  "service": "BengaluruTrafficAI",
  "status": "running",
  "ws_clients": 0
}
```

### Step 4: Start the Dashboard

```bash
npm start
```

The dashboard will:
1. Compile TypeScript
2. Start development server
3. Automatically open `http://localhost:3000` in your browser

**Expected output:**
```
Compiled successfully!

You can now view bengaluru-traffic-ai-dashboard in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

### Step 5: Verify Connection

Once the dashboard opens, check:
- ✅ **Live** indicator in top-right (should be green)
- ✅ Stats cards show data (or zeros if no violations yet)
- ✅ No console errors (press F12 to check)

## Quick Start Script (Windows)

For convenience, use the provided batch script:

```bash
start-dashboard.bat
```

This automatically:
1. Starts API server in one terminal
2. Starts dashboard in another terminal
3. Opens both applications

## Troubleshooting

### Issue: "npm: command not found"

**Solution:** Install Node.js from [nodejs.org](https://nodejs.org/)

Verify installation:
```bash
node --version
npm --version
```

---

### Issue: Port 3000 Already in Use

**Solution:** Kill the process or use a different port:

```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Or set different port
set PORT=3001 && npm start
```

---

### Issue: API Connection Failed

**Symptoms:** Dashboard shows "Disconnected", no data loads

**Solution:**

1. Verify API is running:
   ```bash
   curl http://localhost:8000
   ```

2. Check CORS settings in `api/app.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. Check browser console for errors (F12)

---

### Issue: WebSocket Not Connecting

**Symptoms:** Live indicator stays red/disconnected

**Solution:**

1. Check WebSocket endpoint:
   ```javascript
   // In browser console:
   const ws = new WebSocket('ws://localhost:8000/ws');
   ws.onopen = () => console.log('Connected!');
   ```

2. Verify no firewall blocking WebSocket connections

3. Check browser console for WebSocket errors

---

### Issue: Images Not Loading

**Symptoms:** Violation cards show "No Image Available"

**Solution:**

1. Check evidence directory exists:
   ```bash
   ls output/evidence/
   ```

2. Verify API serves static files:
   ```python
   # In api/app.py
   app.mount("/evidence", StaticFiles(directory="output/evidence"), name="evidence")
   ```

3. Check image paths in database match actual files

---

### Issue: Dependencies Installation Failed

**Symptoms:** npm install errors

**Solution:**

1. Clear npm cache:
   ```bash
   npm cache clean --force
   ```

2. Delete node_modules and reinstall:
   ```bash
   rmdir /s /q node_modules
   npm install
   ```

3. Try with legacy peer deps:
   ```bash
   npm install --legacy-peer-deps
   ```

---

### Issue: TypeScript Errors

**Symptoms:** Compilation errors about types

**Solution:**

1. Ensure TypeScript is installed:
   ```bash
   npm install --save-dev typescript
   ```

2. Check tsconfig.json exists in dashboard directory

3. Restart development server:
   ```bash
   npm start
   ```

---

## Configuration

### Change API URL

Edit each component file and update `API_BASE`:

```typescript
// Current (development)
const API_BASE = 'http://localhost:8000';

// For production
const API_BASE = 'https://your-domain.com/api';
```

Or create a `.env` file:

```env
REACT_APP_API_URL=http://localhost:8000
```

Then use in components:

```typescript
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

### Change Port

```bash
# Windows CMD
set PORT=3001 && npm start

# Windows PowerShell
$env:PORT=3001; npm start

# Linux/Mac
PORT=3001 npm start
```

### Disable Auto-open Browser

```bash
# Windows CMD
set BROWSER=none && npm start

# Windows PowerShell
$env:BROWSER="none"; npm start

# Linux/Mac
BROWSER=none npm start
```

## Development Workflow

### 1. Daily Development

```bash
# Terminal 1: Backend
cd bengaluru_traffic_ai
uvicorn api.app:app --reload --port 8000

# Terminal 2: Frontend
cd bengaluru_traffic_ai/dashboard
npm start
```

### 2. Making Changes

- Edit files in `src/` directory
- Dashboard auto-reloads on save
- Check console for errors
- Test in browser

### 3. Adding New Components

```bash
cd src/components
# Create new files:
# - ComponentName.tsx
# - ComponentName.css
```

### 4. Adding Dependencies

```bash
npm install package-name
npm install --save-dev @types/package-name  # If TypeScript types needed
```

## Production Build

### Build for Production

```bash
npm run build
```

This creates optimized build in `build/` directory.

### Test Production Build

```bash
# Install serve globally
npm install -g serve

# Serve production build
serve -s build -l 3000
```

### Deploy

Upload `build/` directory to:
- **Static hosting**: Netlify, Vercel, GitHub Pages
- **Web server**: Apache, Nginx
- **Cloud**: AWS S3, Azure, Google Cloud

### Example: Nginx Configuration

```nginx
server {
    listen 80;
    server_name dashboard.yourdomain.com;
    root /path/to/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

## Environment Setup

### Development Environment

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_ENV=development
```

### Production Environment

```env
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_WS_URL=wss://api.yourdomain.com/ws
REACT_APP_ENV=production
```

## Testing

### Run Tests

```bash
npm test
```

### Run Tests with Coverage

```bash
npm test -- --coverage
```

### Run Tests in CI

```bash
CI=true npm test
```

## Debugging

### Enable Debug Mode

```javascript
// In browser console
localStorage.setItem('DEBUG', 'true');
```

### View Network Requests

1. Open DevTools (F12)
2. Go to Network tab
3. Filter by "XHR" or "WS"
4. Monitor API calls and WebSocket messages

### React DevTools

Install React Developer Tools browser extension for:
- Component inspection
- Props and state viewing
- Performance profiling

## Performance Optimization

### Analyze Bundle Size

```bash
npm run build
npx source-map-explorer build/static/js/*.js
```

### Reduce Bundle Size

1. Use code splitting
2. Lazy load components
3. Optimize images
4. Remove unused dependencies

### Enable Compression

In production, enable gzip/brotli compression on your web server.

## Security Checklist

Before deploying to production:

- [ ] Change API URLs to production endpoints
- [ ] Enable HTTPS (use Let's Encrypt)
- [ ] Add authentication to API
- [ ] Implement rate limiting
- [ ] Sanitize user inputs
- [ ] Enable CORS only for your domain
- [ ] Use environment variables for secrets
- [ ] Enable Content Security Policy headers
- [ ] Add CSRF protection
- [ ] Audit dependencies: `npm audit`

## Maintenance

### Update Dependencies

```bash
# Check for updates
npm outdated

# Update all dependencies
npm update

# Update specific package
npm install package-name@latest
```

### Check Security Vulnerabilities

```bash
npm audit
npm audit fix
```

### Clean Build

```bash
# Delete build artifacts
rm -rf build node_modules

# Reinstall and rebuild
npm install
npm run build
```

## Support & Resources

### Official Documentation
- React: https://react.dev/
- TypeScript: https://www.typescriptlang.org/
- Recharts: https://recharts.org/
- Axios: https://axios-http.com/

### Project Documentation
- `README.md` - Project overview
- `FEATURES.md` - Complete feature list
- `DASHBOARD_GUIDE.md` - User guide
- `SETUP.md` - This file

### Getting Help
1. Check browser console for errors
2. Review API logs
3. Check network tab for failed requests
4. Verify backend is running
5. Ensure WebSocket connection is active

---

## Quick Reference

### Common Commands

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Check for issues
npm audit

# Update dependencies
npm update
```

### File Structure

```
dashboard/
├── public/              # Static files
├── src/
│   ├── components/     # React components
│   ├── App.tsx        # Main app
│   ├── App.css       # Global styles
│   └── index.tsx     # Entry point
├── package.json       # Dependencies
├── tsconfig.json     # TypeScript config
└── README.md         # Documentation
```

### Key URLs

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

---

**Happy coding! 🚀**
