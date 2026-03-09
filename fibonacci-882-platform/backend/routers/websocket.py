# backend/routers/websocket.py
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import settings
from services.binance_client import binance_client
from services.websocket_client import binance_ws_client
from services.signal_detector import signal_detector
from services.trade_manager import trade_manager

router = APIRouter()

connected_clients: list[WebSocket] = []


@router.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)

    try:
        # Initial load of historical data from Binance
        candles = await binance_client.get_klines(
            symbol=settings.symbol,
            interval=settings.timeframe.value,
            limit=500
        )
        
        while True:
            # Get current price from WebSocket ticker
            ticker = binance_ws_client.get_latest_ticker(settings.symbol)
            current_price = 0.0
            
            if ticker:
                current_price = float(ticker.get("last", ticker.get("lastPrice", 0)))
            elif candles and len(candles) > 0:
                # Fallback to last candle close price
                current_price = candles[-1].get("close", 0)
            
            # Use latest WebSocket kline data if available
            ws_klines = binance_ws_client.get_klines(settings.symbol, settings.timeframe.value, limit=200)
            scan_candles = ws_klines if ws_klines and len(ws_klines) > 50 else candles
            
            # Check open trades against price
            closed_trades = trade_manager.check_open_trades(current_price)
            
            active_signals = []
            fib_data = None
            
            if scan_candles and len(scan_candles) > 50:
                signals = signal_detector.detect(
                    scan_candles, settings.symbol, settings.timeframe.value
                )
                active_signals = [s.dict() for s in signals]
                
                # Get Fibonacci levels
                from services.swing_detector import swing_detector
                from services.fibonacci_engine import fibonacci_engine
                
                swing_high, swing_low = swing_detector.get_latest_swing_pair(scan_candles)
                if swing_high and swing_low:
                    levels = fibonacci_engine.calculate_levels(swing_high, swing_low)
                    fib_data = levels.dict()
            
            # Build payload
            account = trade_manager.get_account()
            payload = {
                "type": "tick",
                "price": current_price,
                "symbol": settings.symbol,
                "timeframe": settings.timeframe.value,
                "mode": settings.trading_mode.value,
                "account": {
                    "balance": account.balance,
                    "equity": account.equity,
                    "total_pnl": account.total_pnl,
                    "open_count": len(account.open_positions),
                    "closed_count": len(account.closed_trades),
                },
                "signals": active_signals,
                "fibonacci": fib_data,
                "closed_trades": [t.dict() for t in closed_trades] if closed_trades else [],
            }
            
            await ws.send_text(json.dumps(payload, default=str))
            await asyncio.sleep(5)
    
    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if ws in connected_clients:
            connected_clients.remove(ws)
