# 🔄 Project Reorganization Guide

## Overview

Your CreditIQ AI project has been successfully reorganized from a flat structure into a clean, scalable folder hierarchy with separate `frontend/` and `backend/` directories.
so add new file.
my project is
---

## What Changed

### Before (Flat Structure)
```
CreditIQ_AI/
├── src/                          # React files
├── public/                       # Frontend assets
├── routers/, services/, utils/   # Backend Python
├── package.json, vite.config.ts  # Frontend config
├── main.py, requirements.txt     # Backend config
└── ... (mixed frontend/backend files)
```

### After (Organized Structure)
```
CreditIQ_AI/
├── frontend/                     # All React/Vite files
│   ├── src/, public/
│   ├── package.json, vite.config.ts
│   └── node_modules/
├── backend/                      # All Python/FastAPI files
│   ├── routers/, services/, utils/
│   ├── main.py, requirements.txt
│   ├── venv/
│   └── run_backend.py
├── start_backend.py              # ✨ NEW: Quick start script
├── start_frontend.ps1            # ✨ NEW: Windows frontend starter
├── start_frontend.sh             # ✨ NEW: Unix frontend starter
├── .env                          # Environment variables
└── README.md                     # Updated with new structure
```

---

## Files Moved to `backend/`

**Core Application Files:**
- `main.py` → Backend entry point for FastAPI
- `config.py` → Configuration settings
- `database.py` → Database connection setup
- `requirements.txt` → Python dependencies
- `run_backend.py` → Backend server launcher

**Business Logic:**
- `routers/*` → API endpoint definitions
- `services/*` → Core business logic & AI services
- `utils/*` → Helper functions and utilities

**Data & Storage:**
- `models/*` → Saved ML models
- `data/*` → Datasets and sample data
- `chroma_db/*` → Vector database storage
- `uploads/*` → Temporary file storage
- `creditiq.db` → SQLite database file
- `graphs/*` → Output graphs and visualizations
- `docs/*` → Project documentation

**Testing & Diagnostics:**
- `test_*.py` → Unit tests
- `check_*.py`, `api_*.py` → Testing scripts
- `diagnose.py` → Diagnostic tools

---

## Files Moved to `frontend/`

**React & Vite:**
- `src/` → React components and pages
- `public/` → Static assets (images, icons, fonts)
- `package.json` → Frontend dependencies
- `package-lock.json` → Locked versions of dependencies
- `vite.config.ts` → Vite build configuration
- `index.html` → Page entry point

**Configuration:**
- `eslint.config.js` → Linting rules
- `tsconfig.json` → TypeScript configuration
- `tsconfig.app.json` → App-specific TypeScript config
- `tsconfig.node.json` → Node-specific TypeScript config

**Dependencies:**
- `node_modules/` → JavaScript packages

---

## Files at Root Level (Unchanged)

- `.env` - Environment variables and API keys
- `.gitignore` - Git ignore rules
- `.git/` - Git repository
- `README.md` - Updated with new structure and startup instructions

---

## Import Paths: No Changes Needed! ✅

Since all Python files now reside in the `backend/` directory (or its subdirectories), the relative imports continue to work seamlessly:

**Examples that still work:**
```python
from config import config              # ✅ Both in backend/
from database import engine            # ✅ Both in backend/
from routers import upload             # ✅ Both in backend/routers/
from services import fraud_service     # ✅ Both in backend/services/
from utils.demo_data import load_demo_data  # ✅ Both in backend/utils/
```

---

## How to Run the Project

### Quick Start ⚡

**Windows (PowerShell):**
```powershell
# Terminal 1 - Backend
python start_backend.py

# Terminal 2 - Frontend
.\start_frontend.ps1
```

**macOS/Linux:**
```bash
# Terminal 1 - Backend
python start_backend.py

# Terminal 2 - Frontend
bash start_frontend.sh
```

### Manual Start 🔧

**Backend:**
```bash
cd backend
python run_backend.py
# OR
python -m uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

---

## Key URLs After Startup

| Component | URL | Purpose |
|-----------|-----|---------|
| Frontend (Dev) | http://localhost:5173 | React UI |
| Backend API | http://localhost:8000 | FastAPI server |
| API Documentation | http://localhost:8000/docs | Swagger UI |
| API Schema | http://localhost:8000/openapi.json | OpenAPI spec |

---

## System Requirements

### Backend
- Python 3.9+ (currently using 3.14)
- Virtual environment created: `backend/venv/`
- Dependencies installed: `pip install -r backend/requirements.txt`

### Frontend
- Node.js 16+ with npm 7+
- Dependencies installed: `cd frontend && npm install`
- Vite dev server on port 5173

### Port Requirements
- `localhost:5173` - Frontend dev server
- `localhost:8000` - Backend API server

---

## Migration Checklist ✓

- [x] Created `frontend/` directory
- [x] Created `backend/` directory
- [x] Moved all React files to `frontend/`
- [x] Moved all Python files to `backend/`
- [x] Moved database files to `backend/`
- [x] Updated `run_backend.py` to work from `backend/`
- [x] Created root-level startup scripts
- [x] No code changes - imports still work
- [x] All relative paths preserved
- [x] API connections maintained
- [x] Environment variables at root level
- [x] Updated README.md

---

## Troubleshooting

### Backend won't start?
1. Ensure you're in the correct directory: `cd backend`
2. Activate the virtual environment: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. Check dependencies: `pip install -r requirements.txt`
4. Run: `python run_backend.py`

### Frontend won't start?
1. Navigate to: `cd frontend`
2. Install dependencies: `npm install`
3. Start dev server: `npm run dev`
4. Check that port 5173 is available

### Module import errors?
- All Python imports are relative and work from `backend/` directory
- If you get import errors, ensure you're running from within `backend/` directory
- Check that `backend/venv/` virtual environment is activated

---

## Benefits of New Structure

✨ **Clean Organization**
- Frontend and backend are completely separated
- Easy to find files in a larger project
- Clear responsibility boundaries

🚀 **Easier Deployment**
- Can deploy frontend and backend independently
- Use different hosting platforms if needed
- Simpler CI/CD pipelines

📦 **Scalability**
- Easier to add new features to either side
- Team members can work on separate directories without conflicts
- Prepared for monorepo or microservices architecture

🔍 **Better Navigation**
- IDE's can focus on one directory at a time
- Cleaner file tree in editors
- Easier to enforce coding standards per side

---

## Next Steps

1. **Test the application:**
   - Run `python start_backend.py`
   - Run `.\start_frontend.ps1` (or `bash start_frontend.sh`)
   - Visit http://localhost:5173

2. **Update any documentation:**
   - Deployment docs should reference new paths
   - Contribution guidelines might need updates
   - CI/CD pipelines may require adjustments

3. **Consider further optimizations:**
   - Docker setup for each service
   - Environment-specific config files
   - API versioning scheme

---

**Project reorganization completed successfully! 🎉**

Your CreditIQ AI application is now cleanly organized and ready for scaling.
