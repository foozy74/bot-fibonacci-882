# backend/config.py
import os
import json
from pathlib import Path
from pydantic import BaseModel
from enum import Enum


# Path to settings file
SETTINGS_FILE = Path(__file__).parent / "data" / "settings.json"


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class TradingPlatform(str, Enum):
    BITUNIX = "bitunix"
    BINANCE_FUTURES = "binance_futures"


class TimeFrame(str, Enum):
    M15 = "15m"
    M30 = "30m"
    H1 = "60m"


class FibonacciConfig(BaseModel):
    level_786: float = 0.786
    level_882: float = 0.882
    level_941: float = 0.941
    swing_lookback: int = 50
    min_swing_amplitude: float = 0.005  # 0.5% minimum swing


class IndicatorConfig(BaseModel):
    ema_fast: int = 21
    ema_medium: int = 50
    ema_slow: int = 200
    hammer_wick_ratio: float = 2.0
    guss_max_counter_candles: int = 0


class RiskConfig(BaseModel):
    max_risk_per_trade: float = 0.02  # 2% of capital
    stop_loss_buffer: float = 0.001   # 0.1% below swing low
    tp_levels: list[float] = [0.618, 0.5, 0.382, 0.0]
    position_sizes: dict = {
        "0.786": 0.25,   # Quarter size
        "0.882": 0.50,   # Half size
        "0.941": 1.00,   # Full size
    }


class WebSocketConfig(BaseModel):
    primary_uri: str = "wss://openapi.bitunix.com/ws"
    fallback_uri: str = "wss://fapi.bitunix.com/ws"
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10


class TelegramConfig(BaseModel):
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = False
    notify_signals: bool = True
    notify_trades: bool = True
    notify_errors: bool = True
    daily_summary: bool = True


class BacktestConfig(BaseModel):
    candles: int = 500
    min_candles: int = 100
    max_candles: int = 1000


class ScannerConfig(BaseModel):
    enabled: bool = True
    interval: int = 60  # seconds
    min_interval: int = 10
    max_interval: int = 300


class ScannerConfig(BaseModel):
    enabled: bool = True
    interval: int = 60  # seconds
    min_interval: int = 10
    max_interval: int = 300


class Settings(BaseModel):
    bitunix_api_key: str = os.getenv("BITUNIX_API_KEY", "")
    bitunix_api_secret: str = os.getenv("BITUNIX_API_SECRET", "")
    bitunix_base_url: str = "https://fapi.bitunix.com"
    trading_mode: TradingMode = TradingMode(os.getenv("TRADING_MODE", "paper"))
    symbol: str = "BTCUSDT"
    timeframe: TimeFrame = TimeFrame.M15
    fibonacci: FibonacciConfig = FibonacciConfig()
    indicators: IndicatorConfig = IndicatorConfig()
    risk: RiskConfig = RiskConfig()
    paper_balance: float = 10000.0
    
    # New settings
    websocket: WebSocketConfig = WebSocketConfig()
    telegram: TelegramConfig = TelegramConfig()
    backtest: BacktestConfig = BacktestConfig()
    scanner: ScannerConfig = ScannerConfig()
    
    # Binance for historical data
    binance_base_url: str = "https://fapi.binance.com"
    
    # Binance Futures for live trading
    binance_futures_api_key: str = os.getenv("BINANCE_FUTURES_API_KEY", "")
    binance_futures_api_secret: str = os.getenv("BINANCE_FUTURES_API_SECRET", "")
    binance_testnet: bool = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    # Platform selection
    trading_platform: TradingPlatform = TradingPlatform.BINANCE_FUTURES
    
    # Leverage & Margin
    default_leverage: int = 20
    margin_mode: str = "ISOLATED"  # ISOLATED or CROSSED
    
    # Fib proximity threshold
    fib_proximity_threshold: float = 0.005  # 0.5%


def load_settings_from_file() -> dict:
    """Load settings from JSON file"""
    if not SETTINGS_FILE.exists():
        return {}
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}


def save_settings_to_file(data: dict):
    """Save settings to JSON file"""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


# Load file settings at startup
_file_settings = load_settings_from_file()

# Create settings instance
settings = Settings()

# Apply file settings if available
if _file_settings:
    # Apply trading settings
    if "trading" in _file_settings:
        trading = _file_settings["trading"]
        if "symbol" in trading:
            settings.symbol = trading["symbol"]
        if "timeframe" in trading:
            try:
                settings.timeframe = TimeFrame(trading["timeframe"])
            except ValueError:
                pass
        if "risk_pct" in trading:
            settings.risk.max_risk_per_trade = trading["risk_pct"] / 100
    
    # Apply websocket settings
    if "websocket" in _file_settings:
        ws = _file_settings["websocket"]
        if "primary_uri" in ws:
            settings.websocket.primary_uri = ws["primary_uri"]
        if "fallback_uri" in ws:
            settings.websocket.fallback_uri = ws["fallback_uri"]
    
    # Apply telegram settings
    if "telegram" in _file_settings:
        tg = _file_settings["telegram"]
        settings.telegram.bot_token = tg.get("bot_token", "")
        settings.telegram.chat_id = tg.get("chat_id", "")
        settings.telegram.enabled = tg.get("enabled", False)
        settings.telegram.notify_signals = tg.get("notify_signals", True)
        settings.telegram.notify_trades = tg.get("notify_trades", True)
        settings.telegram.notify_errors = tg.get("notify_errors", True)
        settings.telegram.daily_summary = tg.get("daily_summary", True)
    
    # Apply backtest settings
    if "backtest" in _file_settings:
        bt = _file_settings["backtest"]
        if "candles" in bt:
            settings.backtest.candles = bt["candles"]
    
    # Apply bitunix settings
    if "bitunix" in _file_settings:
        bitunix = _file_settings["bitunix"]
        if "trading_mode" in bitunix:
            try:
                settings.trading_mode = TradingMode(bitunix["trading_mode"])
            except ValueError:
                pass
