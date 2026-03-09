# backend/models/schemas.py
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalType(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class SignalStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    SNIPER = "sniper"


class TradeStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED_TP = "closed_tp"
    CLOSED_SL = "closed_sl"
    INVALIDATED = "invalidated"
    CANCELLED = "cancelled"


class Candle(BaseModel):
    timestamp: int
    open: float
    high: float
    close: float
    low: float
    volume: float


class SwingPoint(BaseModel):
    type: str  # "high" or "low"
    price: float
    timestamp: int
    index: int


class FibonacciLevels(BaseModel):
    swing_high: float
    swing_low: float
    swing_high_ts: int
    swing_low_ts: int
    level_0: float      # Swing High
    level_236: float
    level_382: float
    level_500: float
    level_618: float
    level_786: float
    level_882: float
    level_941: float
    level_100: float     # Swing Low


class ConfluenceCheck(BaseModel):
    fib_level_hit: bool = False
    fib_level_name: str = ""
    lsob_present: bool = False
    lsob_price: Optional[float] = None
    guss_valid: bool = False
    guss_invalidated: bool = False
    hammer_detected: bool = False
    ema_confluence: bool = False
    avwap_confluence: bool = False
    total_score: int = 0
    max_score: int = 5


class Signal(BaseModel):
    id: str = ""
    timestamp: datetime = datetime.now()
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    type: SignalType = SignalType.NONE
    strength: SignalStrength = SignalStrength.WEAK
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profits: list[float] = []
    fib_levels: Optional[FibonacciLevels] = None
    confluence: Optional[ConfluenceCheck] = None
    crv: float = 0.0
    notes: str = ""


class Trade(BaseModel):
    id: str = ""
    signal_id: str = ""
    timestamp_open: datetime = datetime.now()
    timestamp_close: Optional[datetime] = None
    symbol: str = "BTCUSDT"
    side: str = "LONG"
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    stop_loss: float = 0.0
    take_profits: list[float] = []
    position_size: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    status: TradeStatus = TradeStatus.PENDING
    fib_level: str = ""


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 10000.0
    fib_levels: list[str] = ["0.882", "0.941"]
    require_confluence: int = 3


class BacktestResult(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    max_drawdown: float = 0.0
    avg_crv: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    sharpe_ratio: float = 0.0
    trades: list[Trade] = []
    equity_curve: list[dict] = []


class PaperAccount(BaseModel):
    balance: float = 10000.0
    equity: float = 10000.0
    open_positions: list[Trade] = []
    closed_trades: list[Trade] = []
    total_pnl: float = 0.0


class SettingsUpdate(BaseModel):
    timeframe: Optional[str] = None
    trading_mode: Optional[str] = None
    symbol: Optional[str] = None
    swing_lookback: Optional[int] = None
    min_swing_amplitude: Optional[float] = None
    max_risk_per_trade: Optional[float] = None
    paper_balance: Optional[float] = None
