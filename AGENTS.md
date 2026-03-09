# Fibonacci-882 Platform - Agent Guidelines

## Project Overview
Deep-value Fibonacci retracement trading system with React frontend and FastAPI backend. Supports paper trading and live trading via Binance Futures.

## Build & Run Commands

### Development Setup
```bash
# Start full stack with Docker
docker-compose up --build

# Backend only (from fibonacci-882-platform/backend/)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend only (from fibonacci-882-platform/frontend/)
npm install
npm run dev
```

### Docker Commands
```bash
# Rebuild containers
docker-compose build

# Stop and cleanup
docker-compose down
docker rm -f $(docker ps -aq)  # Force cleanup if needed
```

### Testing
No formal test suite exists. Manual testing via:
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:3000 (via nginx) or http://localhost:5173 (dev)
- Health check: `curl http://localhost:8000/health`

## Code Style Guidelines

### Python (Backend)

**Imports:**
- Standard library first, then third-party, then local modules
- Local imports use relative-style paths from project root: `from services.bitunix_client import ...`
- Group imports by source: routers, services, models, config

**Types:**
- Use Python 3.10+ union syntax: `dict | None` not `Optional[dict]`
- Pydantic v2 models for all schemas
- Type hints on all function parameters and returns

**Naming:**
- snake_case for functions/variables
- PascalCase for classes and Pydantic models
- Descriptive names: `signal_detector`, `bitunix_client`

**Error Handling:**
- Return `None` on API failures, log with `print()` for now
- Wrap async calls in try/except
- Use guards for early returns: `if not swing_high: return []`

**Async:**
- Use `asyncio.create_task()` for fire-and-forget background tasks
- Await all async calls properly
- Close sessions in shutdown handlers

### JavaScript/React (Frontend)

**Imports:**
- React hooks first: `import React, { useState, useEffect } from 'react'`
- Then components: `import Dashboard from './components/Dashboard'`
- Then utils: `import { api } from './utils/api'`

**Components:**
- Functional components only, no class components
- Default exports for page components
- Named exports for utilities

**State:**
- Use `useState` for local state
- Polling with `setInterval` for real-time updates
- Cleanup intervals in useEffect return

**Naming:**
- PascalCase for component files and exports
- camelCase for variables/functions
- Descriptive: `loadTradingMode`, `setSettingsOpen`

**CSS:**
- Separate `.css` files per component
- BEM-like naming: `.app-header`, `.header-badge`, `.badge-live`

### File Structure
```
fibonacci-882-platform/
├── backend/
│   ├── main.py              # FastAPI app, lifespan, routers
│   ├── config.py            # Pydantic settings, env loading
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic, external APIs
│   ├── models/              # Pydantic schemas
│   └── data/                # Persistent JSON files
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Root component
│   │   ├── components/      # React components
│   │   └── utils/           # API helpers
│   └── nginx.conf           # Production routing
└── docker-compose.yml
```

## Key Patterns

### Backend Services
- Singleton instances: `bitunix_client = BitunixClient()`
- Async HTTP with aiohttp sessions
- Signature-based auth for trading APIs
- Background scanner with APScheduler

### Frontend Components
- Polling every 5s for trading mode sync
- WebSocket for real-time price updates
- Settings modal with persistent JSON storage

### API Endpoints
- RESTful: GET for reads, POST for actions, PUT for updates
- Health checks: `/health` and `/health/detailed`
- Swagger docs at `/docs`

## Known Issues
1. **Bitunix API unreachable** - Use Binance Futures for live trading
2. **Duplicate router import** in `main.py:100-101` - scanner.router included twice
3. **Duplicate function definitions** in `api.js:18-30` and `api.js:40-49`
4. **Duplicate ScannerConfig class** in `config.py:79-91`
5. **Settings.py syntax error** - Extra `}` around line 58-59

## Environment Variables
```bash
TRADING_MODE=paper          # paper or live
BINANCE_FUTURES_API_KEY=
BINANCE_FUTURES_API_SECRET=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SCANNER_INTERVAL=60
```

## Deployment (Coolify/Docker)
- Backend: Python 3.11, uvicorn on port 8000
- Frontend: Node 20 build, nginx serving on port 80
- Volume: `./backend/data:/app/data` for persistence
- Health check: `curl -f http://localhost:8000/health`
