# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from routers import trading, signals, backtest, websocket, settings, scanner
from services.bitunix_client import bitunix_client
from services.websocket_client import binance_ws_client
from services.binance_client import binance_client
from services.telegram_bot import telegram_bot
from services.background_scanner import background_scanner
from config import settings as app_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    logger.info("🎯 Fibonacci-882 Sniper Platform starting...")
    logger.info(f"   Mode: {app_settings.trading_mode.value}")
    logger.info(f"   Symbol: {app_settings.symbol}")
    logger.info(f"   Timeframe: {app_settings.timeframe.value}")
    
    # Start WebSocket connection
    logger.info("   Connecting to WebSocket...")
    ws_task = asyncio.create_task(binance_ws_client.start())
    
    # Wait a moment for initial connection
    await asyncio.sleep(3)
    
    # Subscribe to market data
    if binance_ws_client.is_connected:
        binance_ws_client.subscribe("ticker", app_settings.symbol)
        binance_ws_client.subscribe("kline", app_settings.symbol, interval=app_settings.timeframe.value)
        logger.info("   Subscribed to market data channels")
    
    # Test Telegram connection if enabled
    if app_settings.telegram.enabled and app_settings.telegram.bot_token:
        logger.info("   Testing Telegram connection...")
        tg_ok = await telegram_bot.test_connection()
        if tg_ok:
            logger.info("   ✓ Telegram connected")
        else:
            logger.warning("   ✗ Telegram connection failed")
    
    # Start Background Scanner
    logger.info("   Starting Background Scanner...")
    await background_scanner.start()
    logger.info(f"   ✓ Background Scanner running (interval: {background_scanner.scan_interval}s)")
    
    logger.info("   Platform started successfully!")
    logger.info("🚀 Ready for production (Coolify deployment)")
    
    yield
    
    # Shutdown
    logger.info("Platform shutting down...")
    
    # Stop Background Scanner
    await background_scanner.stop()
    
    # Close WebSocket
    await binance_ws_client.stop()
    ws_task.cancel()
    
    # Close HTTP sessions
    await bitunix_client.close()
    await binance_client.close()
    await telegram_bot.close()
    
    logger.info("Platform shutdown complete.")


app = FastAPI(
    title="Fibonacci-882 Sniper Platform",
    description="Deep-Value Fibonacci Retracement Trading System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trading.router)
app.include_router(signals.router)
app.include_router(backtest.router)
app.include_router(websocket.router)
app.include_router(settings.router)
app.include_router(scanner.router)
app.include_router(scanner.router)


@app.get("/health")
async def health():
    """Basic health check"""
    return {
        "status": "ok",
        "mode": app_settings.trading_mode.value,
        "symbol": app_settings.symbol,
    }


@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check with all service statuses"""
    return {
        "status": "ok",
        "websocket": {
            "connected": binance_ws_client.is_connected,
            "uri": binance_ws_client.current_uri
        },
        "binance_api": "ok",
        "telegram": {
            "enabled": app_settings.telegram.enabled,
            "configured": bool(app_settings.telegram.bot_token and app_settings.telegram.chat_id)
        },
        "mode": app_settings.trading_mode.value,
        "symbol": app_settings.symbol,
        "timeframe": app_settings.timeframe.value,
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Fibonacci-882 Sniper Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "settings": "/settings",
    }
