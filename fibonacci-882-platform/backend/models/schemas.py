# backend/models/schemas.py
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class Timeframe(str, Enum):
    M15 = "15m"
    M30 = "30m"
    H1 = "60m"


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class SignalType(str, Enum):
    LONG = "long"
    SHORT = "short"


class SignalStrength(str, Enum):
    SNIPER = "sniper"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class TradeStatus(str, Enum):
    ACTIVE = "active"
    CLOSED_TP = "closed_tp"
    CLOSED_SL = "closed_sl"
    CLOSED_MANUAL = "closed_manual"


class SwingPoint(BaseModel):
    price: float
    index: int
    timestamp: int = 0
    type: str = "high"  # "high" or "low"


class FibonacciLevels(BaseModel):
    swing_high: float
    swing_low: float
    level_0: float
    level_236: float
    level_382: float
    level_500: float
    level_618: float
    level_786: float
    level_882: float
    level_941: float
    level_100: float


class ConfluenceCheck(BaseModel):
    fib_level_hit: bool = False
    fib_level_name: str = ""
    hammer_detected: bool = False
    hanging_man_detected: bool = False
    guss_valid: bool = False
    guss_invalidated: bool = False
    lsob_present: bool = False
    lsob_price: float = 0
    ema_confluence: bool = False
    avwap_confluence: bool = False
    total_score: int = 0
    max_score: int = 5


class Signal(BaseModel):
    id: str
    timestamp: datetime
    symbol: str
    timeframe: str
    type: SignalType
    strength: SignalStrength
    entry_price: float
    stop_loss: float
    take_profits: list[float] = []
    fib_levels: FibonacciLevels | None = None
    confluence: ConfluenceCheck | None = None
    crv: float = 0
    notes: str = ""


class Trade(BaseModel):
    id: str
    signal_id: str = ""
    timestamp_open: datetime | None = None
    timestamp_close: datetime | None = None
    symbol: str
    side: str = "LONG"
    entry_price: float
    exit_price: float = 0
    stop_loss: float
    take_profits: list[float] = []
    position_size: float = 0
    pnl: float = 0
    pnl_percent: float = 0
    status: TradeStatus = TradeStatus.ACTIVE
    fib_level: str = ""


class PaperAccount(BaseModel):
    balance: float = 10000
    equity: float = 10000
    total_pnl: float = 0
    open_positions: list[Trade] = []
    closed_trades: list[Trade] = []


class BacktestConfig(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    initial_capital: float = 10000
    fib_levels: list[str] = ["0.882", "0.941"]
    require_confluence: int = 2


class BacktestResult(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    total_pnl: float = 0
    final_balance: float = 0
    return_pct: float = 0
    avg_crv: float = 0
    best_trade: float = 0
    worst_trade: float = 0
    max_drawdown: float = 0
    profit_factor: float = 0
    trades: list[dict] = []
    equity_curve: list[float] = []
