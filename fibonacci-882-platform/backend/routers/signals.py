# backend/routers/signals.py
from fastapi import APIRouter
from config import settings
from services.binance_client import binance_client
from services.websocket_client import binance_ws_client
from services.signal_detector import signal_detector

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/scan")
async def scan_signals():
    """Run a full signal scan on current symbol/timeframe"""
    # Try to get candles from WebSocket cache first
    candles = binance_ws_client.get_klines(settings.symbol, settings.timeframe.value, limit=500)
    
    # Fallback to Binance if WebSocket cache is empty
    if not candles or len(candles) < 100:
        candles = await binance_client.get_klines(
            symbol=settings.symbol,
            interval=settings.timeframe.value,
            limit=settings.backtest.candles
        )
    
    if not candles:
        return {"status": "error", "msg": "No candle data", "signals": []}
    
    # Convert Binance format to standard format if needed
    standard_candles = []
    for c in candles:
        if "timestamp" in c:
            # Already in standard format
            standard_candles.append({
                "timestamp": c["timestamp"],
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c["volume"]
            })
        else:
            # Binance format
            standard_candles.append(c)
    
    signals = signal_detector.detect(standard_candles, settings.symbol, settings.timeframe.value)
    
    return {
        "status": "ok",
        "symbol": settings.symbol,
        "timeframe": settings.timeframe.value,
        "candle_count": len(standard_candles),
        "signals": [s.dict() for s in signals],
    }


@router.get("/active")
async def get_active_signals():
    signals = signal_detector.get_active_signals()
    return [s.dict() for s in signals]


@router.get("/fibonacci")
async def get_fibonacci_levels():
    """Get current Fibonacci levels for the active symbol"""
    # Try WebSocket cache first
    candles = binance_ws_client.get_klines(settings.symbol, settings.timeframe.value, limit=500)
    
    # Fallback to Binance
    if not candles or len(candles) < 100:
        candles = await binance_client.get_klines(
            symbol=settings.symbol,
            interval=settings.timeframe.value,
            limit=200
        )
    
    if not candles:
        return {"status": "error", "msg": "No candle data"}
    
    from services.swing_detector import swing_detector
    from services.fibonacci_engine import fibonacci_engine
    
    swing_high, swing_low = swing_detector.get_latest_swing_pair(candles)
    
    if not swing_high or not swing_low:
        return {"status": "error", "msg": "No swing points found"}
    
    levels = fibonacci_engine.calculate_levels(swing_high, swing_low)
    
    return {
        "status": "ok",
        "swing_high": {"price": swing_high.price, "index": swing_high.index},
        "swing_low": {"price": swing_low.price, "index": swing_low.index},
        "levels": levels.dict(),
    }


@router.get("/price")
async def get_current_price():
    # Try WebSocket ticker first
    ticker = binance_ws_client.get_latest_ticker(settings.symbol)
    
    if ticker:
        price = float(ticker.get("last", ticker.get("lastPrice", 0)))
        return {"status": "ok", "symbol": settings.symbol, "price": price}
    
    # Fallback to Binance
    ticker = await binance_client.get_ticker(settings.symbol)
    if not ticker:
        return {"status": "error", "price": 0}
    
    return {"status": "ok", "symbol": settings.symbol, "price": ticker.get("last", 0)}


@router.get("/candles")
async def get_candles(limit: int = 500):
    # Try WebSocket cache first
    candles = binance_ws_client.get_klines(settings.symbol, settings.timeframe.value, limit=limit)
    
    # Fallback to Binance
    if not candles or len(candles) < limit:
        candles = await binance_client.get_klines(
            symbol=settings.symbol,
            interval=settings.timeframe.value,
            limit=limit
        )
    
    return {"status": "ok", "count": len(candles), "candles": candles}
