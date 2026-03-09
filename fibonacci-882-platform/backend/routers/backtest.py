# backend/routers/backtest.py
from fastapi import APIRouter
from models.schemas import BacktestConfig
from services.bitunix_client import bitunix_client
from services.backtest_engine import BacktestEngine

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run")
async def run_backtest(config: BacktestConfig):
    """Execute a backtest with given configuration"""
    candles = await bitunix_client.get_klines(
        symbol=config.symbol,
        timeframe=config.timeframe,
        limit=1000,
    )

    if not candles or len(candles) < 100:
        return {
            "status": "error",
            "msg": f"Insufficient data: {len(candles) if candles else 0} candles",
            "total_trades": 0,
        }

    engine = BacktestEngine()
    result = engine.run(candles, config)

    return result.dict()


@router.get("/presets")
async def get_presets():
    return {
        "conservative": BacktestConfig(
            fib_levels=["0.882", "0.941"],
            require_confluence=3,
        ).dict(),
        "balanced": BacktestConfig(
            fib_levels=["0.786", "0.882", "0.941"],
            require_confluence=2,
        ).dict(),
        "aggressive": BacktestConfig(
            fib_levels=["0.786", "0.882"],
            require_confluence=1,
        ).dict(),
    }
