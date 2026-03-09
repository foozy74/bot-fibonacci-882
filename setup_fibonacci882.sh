#!/bin/bash

# Setup script for fibonacci-882-platform

set -e

echo "Creating project structure for fibonacci-882-platform..."

# Root
mkdir -p fibonacci-882-platform

# Frontend directories
mkdir -p fibonacci-882-platform/frontend/src/components
mkdir -p fibonacci-882-platform/frontend/src/utils

# Backend directories
mkdir -p fibonacci-882-platform/backend/routers
mkdir -p fibonacci-882-platform/backend/services
mkdir -p fibonacci-882-platform/backend/models

# Data directory
mkdir -p fibonacci-882-platform/data

# Root files
touch fibonacci-882-platform/docker-compose.yml

# Frontend files
touch fibonacci-882-platform/frontend/Dockerfile
touch fibonacci-882-platform/frontend/nginx.conf
touch fibonacci-882-platform/frontend/package.json
touch fibonacci-882-platform/frontend/vite.config.js
touch fibonacci-882-platform/frontend/index.html

# Frontend src files
touch fibonacci-882-platform/frontend/src/main.jsx
touch fibonacci-882-platform/frontend/src/App.jsx
touch fibonacci-882-platform/frontend/src/App.css

# Frontend components
touch fibonacci-882-platform/frontend/src/components/Dashboard.jsx
touch fibonacci-882-platform/frontend/src/components/Dashboard.css
touch fibonacci-882-platform/frontend/src/components/ChartPanel.jsx
touch fibonacci-882-platform/frontend/src/components/ChartPanel.css
touch fibonacci-882-platform/frontend/src/components/SignalPanel.jsx
touch fibonacci-882-platform/frontend/src/components/SignalPanel.css
touch fibonacci-882-platform/frontend/src/components/ControlPanel.jsx
touch fibonacci-882-platform/frontend/src/components/ControlPanel.css
touch fibonacci-882-platform/frontend/src/components/BacktestPanel.jsx
touch fibonacci-882-platform/frontend/src/components/BacktestPanel.css
touch fibonacci-882-platform/frontend/src/components/TradeLog.jsx
touch fibonacci-882-platform/frontend/src/components/TradeLog.css

# Frontend utils
touch fibonacci-882-platform/frontend/src/utils/api.js

# Backend files
touch fibonacci-882-platform/backend/Dockerfile
touch fibonacci-882-platform/backend/requirements.txt
touch fibonacci-882-platform/backend/main.py
touch fibonacci-882-platform/backend/config.py

# Backend routers
touch fibonacci-882-platform/backend/routers/__init__.py
touch fibonacci-882-platform/backend/routers/trading.py
touch fibonacci-882-platform/backend/routers/signals.py
touch fibonacci-882-platform/backend/routers/backtest.py
touch fibonacci-882-platform/backend/routers/websocket.py

# Backend services
touch fibonacci-882-platform/backend/services/__init__.py
touch fibonacci-882-platform/backend/services/bitunix_client.py
touch fibonacci-882-platform/backend/services/fibonacci_engine.py
touch fibonacci-882-platform/backend/services/signal_detector.py
touch fibonacci-882-platform/backend/services/swing_detector.py
touch fibonacci-882-platform/backend/services/indicator_service.py
touch fibonacci-882-platform/backend/services/backtest_engine.py
touch fibonacci-882-platform/backend/services/trade_manager.py

# Backend models
touch fibonacci-882-platform/backend/models/__init__.py
touch fibonacci-882-platform/backend/models/schemas.py

# Data placeholder
touch fibonacci-882-platform/data/.gitkeep

echo ""
echo "Project structure created successfully!"
echo ""
echo "Run 'find fibonacci-882-platform -print' to verify the structure."
