# Dashboard Deployment Guide

## Production Build

The dashboard has been successfully built and is ready for deployment!

### Build Statistics
- **Main JS Bundle**: 197.02 kB (gzipped)
- **CSS Bundle**: 3.47 kB (gzipped)
- **Total Size**: ~200 kB (gzipped)
- **Build Status**: ✅ Success

## Deployment Options

### Option 1: Static File Server

#### Using Node.js `serve`
```bash
npm install -g serve
serve -s build -l 3000
```

#### Using Python
```bash
cd build
python -m http.server 3000
```

#### Using PHP
```bash
cd build
php -S localhost:3000
```

### Option 2: Netlify (Recommended for Quick Deploy)

1. Install Netlify CLI:
```bash
npm install -g netlify-cli
```

2. Deploy:
```bash
cd dashboard
netlify deploy --prod --dir=build
```

3. Follow prompts to create new site or update existing

### Option 3: Vercel

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Deploy:
```bash
cd dashboard
vercel --prod
```

### Option 4: GitHub Pages

1. Install gh-pages:
```bash
npm install --save-dev gh-pages
```

2. Add to package.json:
```json
{
  "homepage": "https://yourusername.github.io/bengaluru-traffic-ai",
  "scripts": {
    "predeploy": "npm run build",
    "deploy": "gh-pages -d build"
  }
}
```

3. Deploy:
```bash
npm run deploy
```

### Option 5: AWS S3 + CloudFront

1. Build project:
```bash
npm run build
```

2. Upload to S3:
```bash
aws s3 sync build/ s3://your-bucket-name --delete
```

3. Invalidate CloudFront cache:
```bash
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

### Option 6: Docker

Create `Dockerfile`:
```dockerfile
# Build stage
FROM node:16-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Create `nginx.conf`:
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    location /ws {
        proxy_pass http://backend:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

Build and run:
```bash
docker build -t bengaluru-traffic-dashboard .
docker run -p 80:80 bengaluru-traffic-dashboard
```

## Production Configuration

### Environment Variables

Create `.env.production`:
```env
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_WS_URL=wss://api.yourdomain.com/ws
REACT_APP_ENV=production
```

### Update API URLs

If not using environment variables, update in each component:
```typescript
const API_BASE = 'https://api.yourdomain.com';
```

### CORS Configuration

Update backend API CORS settings:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## SSL/HTTPS Setup

### Using Let's Encrypt (Free)

#### For Nginx:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

#### For Apache:
```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d yourdomain.com
```

### Update WebSocket to WSS

Change WebSocket URL from `ws://` to `wss://`:
```typescript
const ws = new WebSocket('wss://api.yourdomain.com/ws');
```

## Nginx Full Configuration

Complete production Nginx config:
```nginx
# HTTP - Redirect to HTTPS
server {
    listen 80;
    server_name dashboard.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name dashboard.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/dashboard.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;

    # Root
    root /var/www/dashboard/build;
    index index.html;

    # React Router
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API Proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket Proxy
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

## Performance Optimization

### Enable Compression

Ensure gzip is enabled on your server:
- Nginx: `gzip on;` (see config above)
- Apache: Enable `mod_deflate`

### Set Cache Headers

Cache static assets for better performance:
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Use CDN (Optional)

Upload static assets to CDN:
1. CloudFlare (Free)
2. AWS CloudFront
3. Azure CDN
4. Google Cloud CDN

## Monitoring & Analytics

### Add Google Analytics

Update `public/index.html`:
```html
<head>
  <!-- Google Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'GA_MEASUREMENT_ID');
  </script>
</head>
```

### Error Tracking

Add Sentry for error tracking:
```bash
npm install @sentry/react
```

In `src/index.tsx`:
```typescript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "YOUR_SENTRY_DSN",
  environment: "production",
});
```

## Security Checklist

Before deploying to production:

- [ ] Update API URLs to production endpoints
- [ ] Enable HTTPS/SSL
- [ ] Change WebSocket to WSS
- [ ] Restrict CORS to your domain only
- [ ] Add authentication to API
- [ ] Implement rate limiting
- [ ] Add security headers (CSP, HSTS, etc.)
- [ ] Sanitize all user inputs
- [ ] Enable firewall rules
- [ ] Set up monitoring and alerts
- [ ] Run security audit: `npm audit`
- [ ] Update all dependencies
- [ ] Remove console.log statements
- [ ] Disable source maps (optional)

## Post-Deployment Testing

### Smoke Tests

1. **Load Test**: Open dashboard, verify it loads
2. **Connection Test**: Check "Live" indicator is green
3. **Data Test**: Verify stats cards show data
4. **Navigation Test**: Test all 4 tabs
5. **WebSocket Test**: Wait for real-time update
6. **API Test**: Test filters and search
7. **Review Test**: Approve/reject violation
8. **Mobile Test**: Test on mobile device

### Performance Tests

```bash
# Lighthouse audit
npm install -g lighthouse
lighthouse https://yourdomain.com --view

# Load testing
npm install -g loadtest
loadtest -c 10 -n 100 https://yourdomain.com
```

## Rollback Plan

If deployment fails:

1. **Quick Rollback**:
   ```bash
   # Restore previous version
   git checkout previous-tag
   npm run build
   # Re-deploy
   ```

2. **DNS Rollback**: Point domain back to old server

3. **CDN Rollback**: Invalidate CDN cache

## Maintenance

### Regular Updates

```bash
# Check for updates weekly
npm outdated

# Update dependencies
npm update

# Rebuild
npm run build

# Re-deploy
```

### Backup

Backup build folder regularly:
```bash
# Create backup
tar -czf dashboard-backup-$(date +%Y%m%d).tar.gz build/

# Upload to S3
aws s3 cp dashboard-backup-*.tar.gz s3://your-backups/
```

## Troubleshooting Deployment

### Build Fails
- Clear cache: `npm cache clean --force`
- Delete node_modules: `rm -rf node_modules`
- Reinstall: `npm install`
- Rebuild: `npm run build`

### Assets Not Loading
- Check file paths in build/index.html
- Verify `homepage` in package.json
- Check server root directory

### API Connection Fails
- Verify API URL is correct
- Check CORS settings
- Ensure API is accessible
- Test with curl: `curl https://api.yourdomain.com`

### WebSocket Won't Connect
- Verify WSS URL (not WS)
- Check firewall allows WebSocket
- Verify proxy configuration
- Test WebSocket endpoint

## Cost Estimates

### Free Options
- **Netlify**: 100GB bandwidth/month
- **Vercel**: 100GB bandwidth/month
- **GitHub Pages**: Unlimited static hosting

### Paid Options
- **AWS S3 + CloudFront**: ~$5-20/month
- **Digital Ocean**: $5/month (Droplet)
- **Heroku**: $7/month (Hobby plan)
- **Azure**: ~$10/month

## Support

### Deployment Issues
1. Check build logs
2. Verify all files uploaded
3. Check server error logs
4. Test locally first
5. Check firewall settings

### Performance Issues
1. Enable compression
2. Use CDN
3. Optimize images
4. Enable caching
5. Check bundle size

---

## Quick Deploy Checklist

- [ ] Build production version: `npm run build`
- [ ] Update API URLs to production
- [ ] Configure CORS on backend
- [ ] Set up SSL/HTTPS
- [ ] Upload files to server
- [ ] Configure web server (Nginx/Apache)
- [ ] Test all features
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Document deployment

**Your dashboard is ready to deploy! Choose an option above and go live! 🚀**
