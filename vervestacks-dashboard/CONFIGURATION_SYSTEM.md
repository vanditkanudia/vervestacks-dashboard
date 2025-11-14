# VerveStacks Dashboard - Environment Configuration

## 📁 **Environment Files**

```
vervestacks-dashboard/
└── env/
    ├── env.development    # Development settings
    └── env.production     # Production settings (vervestacks.cloud)
```

## 🚀 **How to Use**

### **Available Commands:**

- **`npm start`** - Default command, runs in development mode
- **`npm run start:dev`** - Explicitly runs in development mode  
- **`npm run start:prod`** - Runs in production mode
- **`npm run dev`** - Development mode with nodemon (auto-restart on file changes)

### **Usage:**

```bash
# Development
npm start        # Uses env/env.development
npm run start:dev   # Uses env/env.development
npm run dev         # Uses env/env.development (with auto-restart)

# Production
npm run start:prod  # Uses env/env.production
```

## ⚙️ **Configuration**

### **Edit Environment Files:**
- **Development:** Edit `env/env.development`
- **Production:** Edit `env/env.production`

### **All Services in One File (Unified Source):**
Edit ONLY the root env files:

```
vervestacks-dashboard/env/env.development
vervestacks-dashboard/env/env.production
```

These contain settings for:
- Backend (database, JWT, CORS, Python service)
- Frontend (derived API URL)
- Python service (port, CORS origins)
- Logging configuration

The backend loads these via `config/ConfigManager.js`.

The frontend gets these automatically at build/start via a sync step that writes `frontend/.env.local`:
- Script: `config/syncEnvToFrontend.js`
- Derived vars:
  - `REACT_APP_API_URL = {BACKEND_PROTOCOL}://{BACKEND_HOST}:{BACKEND_PORT}/api`
  - `REACT_APP_ENV = {NODE_ENV}`

No manual edits are needed in `frontend/.env*`.

## 🎯 **Key Points**

- ✅ **Centralized** - Single root env per environment
- ✅ **Environment-specific** - Different files for dev/prod
- ✅ **No fallbacks** - Everything must be set in environment files
- ✅ **Production ready** - Configured for vervestacks.cloud

## 🔧 **Commands & Sync Behavior**

- `frontend` scripts run the sync automatically:
  - `npm start`/`npm run build` in `frontend/` will first run `node ../config/syncEnvToFrontend.js`
  - This regenerates `frontend/.env.local` from the root env

## ✅ **Health Checks**

- Backend: `http://localhost:{BACKEND_PORT}/health`
- API Base: `http://localhost:{BACKEND_PORT}/api`
- Fuel Colors: `GET /api/capacity/fuel-colors` (requires Python service at `PYTHON_SERVICE_URL`)
- Overview Tab Charts: `GET /api/overview/energy-metrics/:iso_code` and `GET /api/overview/capacity-utilization/:iso_code` (now use PostgreSQL procedures directly)
