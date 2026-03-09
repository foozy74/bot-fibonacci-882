# backend/routers/settings.py
"""
Settings router for managing application configuration
"""
from fastapi import APIRouter
from config import settings, save_settings_to_file, load_settings_from_file, SETTINGS_FILE
from services.telegram_bot import telegram_bot
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings():
    """
    Get all settings (excluding secrets)
    """
    file_settings = load_settings_from_file()
    
    return {
        "status": "ok",
        "data": {
            "bitunix": {
                "api_key": file_settings.get("bitunix", {}).get("api_key", "")[:8] + "..." if file_settings.get("bitunix", {}).get("api_key") else "",
                "trading_mode": file_settings.get("bitunix", {}).get("trading_mode", settings.trading_mode.value)
            },
            "websocket": {
                "primary_uri": file_settings.get("websocket", {}).get("primary_uri", settings.websocket.primary_uri),
                "fallback_uri": file_settings.get("websocket", {}).get("fallback_uri", settings.websocket.fallback_uri)
            },
            "telegram": {
                "bot_token": file_settings.get("telegram", {}).get("bot_token", "")[:8] + "..." if file_settings.get("telegram", {}).get("bot_token") else "",
                "chat_id": file_settings.get("telegram", {}).get("chat_id", ""),
                "enabled": file_settings.get("telegram", {}).get("enabled", False),
                "notify_signals": file_settings.get("telegram", {}).get("notify_signals", True),
                "notify_trades": file_settings.get("telegram", {}).get("notify_trades", True),
                "notify_errors": file_settings.get("telegram", {}).get("notify_errors", True),
                "daily_summary": file_settings.get("telegram", {}).get("daily_summary", True)
            },
            "trading": {
                "symbol": file_settings.get("trading", {}).get("symbol", settings.symbol),
                "timeframe": file_settings.get("trading", {}).get("timeframe", settings.timeframe.value),
                "risk_pct": file_settings.get("trading", {}).get("risk_pct", 2.0)
            },
            "backtest": {
                "candles": file_settings.get("backtest", {}).get("candles", settings.backtest.candles)
            },
            "scanner": {
                "enabled": file_settings.get("scanner", {}).get("enabled", True),
                "interval": file_settings.get("scanner", {}).get("interval", 60)
            },
            "binance_futures": {
                "api_key": file_settings.get("binance_futures", {}).get("api_key", "")[:8] + "..." if file_settings.get("binance_futures", {}).get("api_key") else "",
            }
        }
    }


@router.put("")
async def save_settings(data: dict):
    """
    Save settings to file
    
    Body:
    {
        "bitunix": {"api_key": "...", "api_secret": "...", "trading_mode": "paper"},
        "websocket": {"primary_uri": "...", "fallback_uri": "..."},
        "telegram": {"bot_token": "...", "chat_id": "...", "enabled": true, ...},
        "trading": {"symbol": "BTCUSDT", "timeframe": "15m", "risk_pct": 2.0},
        "backtest": {"candles": 500}
    }
    """
    # Load existing settings from file
    file_settings = load_settings_from_file()
    
    # Build complete settings with defaults
    current = {
        "bitunix": {
            "api_key": "",
            "api_secret": "",
            "trading_mode": "paper"
        },
        "binance_futures": {
            "api_key": "",
            "api_secret": "",
            "testnet": True
        },
        "websocket": {
            "primary_uri": "wss://openapi.bitunix.com/ws",
            "fallback_uri": "wss://fapi.bitunix.com/ws"
        },
        "telegram": {
            "bot_token": "",
            "chat_id": "",
            "enabled": False,
            "notify_signals": True,
            "notify_trades": True,
            "notify_errors": True,
            "daily_summary": True
        },
        "trading": {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "risk_pct": 2.0,
            "platform": "binance_futures",
            "leverage": 20,
            "margin_mode": "ISOLATED"
        },
        "backtest": {
            "candles": 500
        },
        "scanner": {
            "enabled": True,
            "interval": 60
        }
    }
    
    # Merge file settings first (existing persisted data)
    for section, values in file_settings.items():
        if section in current and isinstance(values, dict) and isinstance(current[section], dict):
            current[section].update(values)
        else:
            current[section] = values
    
    # Then merge new data (user's updates)
    for section, values in data.items():
        if section in current and isinstance(values, dict) and isinstance(current[section], dict):
            current[section].update(values)
        else:
            current[section] = values
    
    # Save to file
    if save_settings_to_file(current):
        logger.info("Settings saved successfully")
        
        # Update runtime settings
        from config import settings as runtime_settings
        if "trading" in current:
            trading = current["trading"]
            runtime_settings.symbol = trading.get("symbol", runtime_settings.symbol)
            try:
                runtime_settings.timeframe = type(runtime_settings.timeframe)(trading.get("timeframe", runtime_settings.timeframe.value))
            except ValueError:
                pass
            if "risk_pct" in trading:
                runtime_settings.risk.max_risk_per_trade = trading["risk_pct"] / 100
        
        if "telegram" in current:
            tg = current["telegram"]
            runtime_settings.telegram.bot_token = tg.get("bot_token", "")
            runtime_settings.telegram.chat_id = tg.get("chat_id", "")
            runtime_settings.telegram.enabled = tg.get("enabled", False)
        
        if "backtest" in current:
            runtime_settings.backtest.candles = current["backtest"].get("candles", 500)
        
        if "bitunix" in current:
            bitunix = current["bitunix"]
            runtime_settings.bitunix_api_key = bitunix.get("api_key", "")
            runtime_settings.bitunix_api_secret = bitunix.get("api_secret", "")
        
        if "binance_futures" in current:
            binance = current["binance_futures"]
            runtime_settings.binance_futures_api_key = binance.get("api_key", "")
            runtime_settings.binance_futures_api_secret = binance.get("api_secret", "")
        
        if "trading" in current:
            trading = current["trading"]
            runtime_settings.trading_platform = trading.get("platform", "binance_futures")
        
        return {"status": "ok", "msg": "Settings saved successfully"}
    else:
        return {"status": "error", "msg": "Failed to save settings"}


@router.post("/test-telegram")
async def test_telegram():
    """
    Send test notification to Telegram
    """
    if not settings.telegram.enabled:
        return {"status": "error", "msg": "Telegram is not enabled"}
    
    if not settings.telegram.bot_token or not settings.telegram.chat_id:
        return {"status": "error", "msg": "Telegram bot token or chat ID not configured"}
    
    success = await telegram_bot.test_connection()
    
    if success:
        return {"status": "ok", "msg": "Test message sent successfully"}
    else:
        return {"status": "error", "msg": "Failed to send test message"}


@router.get("/status")
async def get_status():
    """
    Get connection status for all services
    """
    from services.websocket_client import binance_ws_client
    from services.binance_client import binance_client
    
    # Check WebSocket
    ws_status = {
        "connected": binance_ws_client.is_connected,
        "subscriptions": len(binance_ws_client._subscriptions)
    }
    
    # Check Binance API (quick ping)
    binance_ok = False
    try:
        ticker = await binance_client.get_ticker("BTCUSDT")
        binance_ok = ticker is not None
    except Exception:
        binance_ok = False
    
    # Check Telegram
    telegram_ok = False
    if settings.telegram.enabled and settings.telegram.bot_token:
        try:
            # Simple check - just verify token format
            telegram_ok = len(settings.telegram.bot_token) > 10
        except Exception:
            telegram_ok = False
    
    return {
        "status": "ok",
        "services": {
            "websocket": ws_status,
            "binance_api": {"ok": binance_ok},
            "bitunix_api": {"ok": True},  # Assume OK, actual check requires auth
            "telegram": {"ok": telegram_ok, "enabled": settings.telegram.enabled}
        }
    }


@router.get("/symbols")
async def get_symbols():
    """
    Get list of available trading symbols
    """
    from services.binance_client import binance_client
    
    symbols = await binance_client.get_symbols()
    
    # Filter to common USDT pairs
    usdt_symbols = [s for s in symbols if s.endswith("USDT")]
    
    # Sort by length (shorter first) and alphabetically
    usdt_symbols.sort()
    
    return {
        "status": "ok",
        "count": len(usdt_symbols),
        "symbols": usdt_symbols[:100]  # Return top 100
    }
