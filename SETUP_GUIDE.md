# Lead Generator Project - Complete Setup Guide

## ✅ What Has Been Set Up

### Backend (Django + Docker)
- **Django REST API** running on `http://localhost:8000`
- **PostgreSQL Database** on port 5433
- **Redis Cache** on port 6379
- **Celery Workers** for background tasks
- **Celery Beat** for scheduled tasks
- **Health Check Endpoint** at `/api/health/`

### Frontend (React + Vite)
- **React Application** with Firebase authentication
- **Tailwind CSS** for styling
- **Axios** for API requests
- **Connection Status Indicator** showing backend connectivity
- **Auto-reconnection** checking every 10 seconds

### API Endpoints Available
- `GET /api/` - Welcome endpoint
- `GET /api/health/` - Backend health check (used by frontend)
- `GET /api/leads/` - List all leads
- `POST /api/generate/` - Generate leads from platforms
- `POST /api/leads/bulk-verify/` - Bulk verify emails
- `GET /api/leads/export/` - Export leads as CSV
- And more...

---

## 🚀 Running the Application

### Option 1: Docker (Backend + Database)
```bash
cd c:\Users\SYED ZUBAIR HUSAIN\Desktop\lead-gen-project

# Start all containers
docker-compose up

# In another terminal, verify containers are running
docker ps
```

All containers will be running:
- ✅ Django Backend: http://localhost:8000
- ✅ PostgreSQL: localhost:5433
- ✅ Redis: localhost:6379
- ✅ Celery Worker: Running
- ✅ Celery Beat: Running

### Option 2: Frontend (React Development Server)
```bash
cd c:\Users\SYED ZUBAIR HUSAIN\Desktop\lead-gen-project\leadgen-frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## 🔌 Frontend-Backend Integration

### How It Works:
1. **Frontend .env** is configured with:
   ```
   VITE_API_URL=http://localhost:8000/api
   ```

2. **API Service** (`src/services/api.js`):
   - Uses Axios to communicate with backend
   - Includes health check function: `checkBackendHealth()`

3. **Connection Status Component** (`src/components/ConnectionStatus.jsx`):
   - Shows a **green indicator** when backend is connected ✅
   - Shows a **red indicator** when backend is disconnected ❌
   - Auto-checks every 10 seconds
   - Located in top-right corner of the screen

4. **App Integration**:
   - Connection status is displayed on every page
   - Checks backend health on mount and periodically

---

## 📋 Backend API Health Response

When frontend calls `GET /api/health/`, you'll get:

```json
{
  "status": "healthy",
  "db_connected": true,
  "serpapi_ready": true,
  "google_cse_ready": true,
  "apify_ready": true,
  "gemini_ready": true,
  "timestamp": "2026-04-01T10:00:00Z"
}
```

---

## 🔧 Configuration Files

### Backend Configuration
- **Location**: `backend/.env`
- **Key Settings**:
  - `DEBUG=True` (development)
  - `ALLOWED_HOSTS=localhost,127.0.0.1,backend,0.0.0.0`
  - `POSTGRES_DB=leadgen`
  - `CELERY_BROKER_URL=redis://redis:6379/0`

### Frontend Configuration
- **Location**: `leadgen-frontend/.env`
- **Key Settings**:
  - `VITE_API_URL=http://localhost:8000/api`
  - Firebase configuration for authentication

### Docker Configuration
- **Location**: `docker-compose.yml`
- **Services**:
  - Django Backend
  - PostgreSQL Database
  - Redis Cache
  - Celery Worker
  - Celery Beat

---

## ✨ Features Implemented

### 1. **Backend Health Monitoring**
- Frontend automatically checks backend connectivity
- Visual indicator shows connection status
- Auto-reconnects every 10 seconds

### 2. **CORS Configuration**
- Backend allows requests from Vite dev server (`localhost:5173`)
- No CORS errors should occur

### 3. **API Integration**
- Axios instance pre-configured with base URL
- Ready to make API calls from any component
- Example usage:
  ```javascript
  import api from '../services/api';
  
  // Make API calls
  const response = await api.get('/leads/');
  ```

### 4. **Database & Celery**
- PostgreSQL for persistent data
- Redis for caching and Celery broker
- Celery Workers for background jobs
- Celery Beat for scheduled tasks

---

## 🔍 Testing the Connection

### Method 1: Check with Browser
1. Open Frontend: `http://localhost:5173`
2. Look at top-right corner
3. You should see **"✓ Backend Connected"** in green

### Method 2: Check with curl
```bash
# Test backend is running
curl http://localhost:8000/api/health/

# Should return:
# {"status":"healthy","db_connected":true,...}
```

### Method 3: Check Docker Containers
```bash
docker ps

# All containers should show "healthy" or "Up"
```

---

## 🚨 Troubleshooting

### Backend shows "Disconnected"
1. Check if Docker containers are running: `docker ps`
2. Check backend logs: `docker logs lead-gen-project-backend-1`
3. Verify backend .env is correct
4. Restart: `docker-compose restart`

### Frontend won't load
1. Check if dependencies are installed: `npm install`
2. Check frontend .env has correct API URL
3. Check if React dev server is running on correct port
4. Check browser console for errors (F12)

### API calls failing
1. Check CORS configuration in `backend/leadgen/settings.py`
2. Ensure `http://localhost:5173` is in `CORS_ALLOWED_ORIGINS`
3. Check backend health: `curl http://localhost:8000/api/health/`

---

## 📝 Next Steps

1. **Run Backend**:
   ```bash
   docker-compose up
   ```

2. **Run Frontend**:
   ```bash
   cd leadgen-frontend && npm install && npm run dev
   ```

3. **Verify Connection**:
   - Open `http://localhost:5173`
   - Look for green "Backend Connected" indicator
   - You're ready to start fetching leads! 🎉

---

## 📊 Project Structure

```
lead-gen-project/
├── backend/                    # Django Backend
│   ├── leadgen/                # Main project settings
│   │   ├── settings.py        # Django configuration
│   │   └── urls.py            # URL routing
│   ├── leads/                  # Lead generation app
│   │   ├── models.py          # Database models
│   │   ├── views.py           # API endpoints
│   │   ├── serializers.py     # Serializers
│   │   └── services.py        # Business logic
│   ├── manage.py              # Django CLI
│   └── requirements.txt        # Python dependencies
├── leadgen-frontend/          # React Frontend
│   ├── src/
│   │   ├── components/        # Reusable components
│   │   │   └── ConnectionStatus.jsx  # Backend status indicator
│   │   ├── services/          # API services
│   │   │   └── api.js        # Axios instance with health check
│   │   ├── pages/            # Page components
│   │   ├── App.jsx           # Main app with status indicator
│   │   └── main.jsx          # Entry point
│   ├── .env                  # Frontend configuration
│   └── package.json          # Dependencies
├── docker-compose.yml         # Docker configuration
└── SETUP_GUIDE.md            # This file
```

---

## ✅ Everything is Ready!

Your full-stack application is now set up with:
- ✅ Backend API running in Docker
- ✅ Database and caching configured
- ✅ Frontend connected to backend
- ✅ Health monitoring in place
- ✅ Ready to fetch leads!

Start the services and begin building your lead generation platform! 🚀
