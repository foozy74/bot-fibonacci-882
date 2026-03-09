# backend/services/backtest_engine.py
from models.schemas import (
    BacktestConfig, BacktestResult, FibonacciLevels
)
from services.swing_detector import SwingDetector
from services.fibonacci_engine import FibonacciEngine
from services.indicator_service import IndicatorService


class BacktestEngine:
    """Run historical backtests of the Fibonacci-882 strategy"""

    def __init__(self):
        self.swing = SwingDetector()
        self.fib = FibonacciEngine()
        self.indicators = IndicatorService()

    def run(self, candles: list[dict], config: BacktestConfig) -> BacktestResult:
        if len(candles) < 60:
            return BacktestResult()

        balance = config.initial_capital
        trades = []
        equity_curve = []
        peak_balance = balance

        entry_levels = [float(l) for l in config.fib_levels]

        window_size = 100
        i = window_size

        while i < len(candles):
            window = candles[i - window_size:i]
            current_candle = candles[i]

            current_price = float(current_candle.get("close", current_candle.get("c", 0)))
            current_low = float(current_candle.get("low", current_candle.get("l", 0)))
            current_high = float(current_candle.get("high", current_candle.get("h", 0)))

            swing_high, swing_low = self.swing.get_latest_swing_pair(window)
            if not swing_high or not swing_low:
                i += 1
                continue

            fib = self.fib.calculate_levels(swing_high, swing_low)

            level_map = {
                0.786: ("0.786", fib.level_786),
                0.882: ("0.882", fib.level_882),
                0.941: ("0.941", fib.level_941),
            }

            trade_taken = False

            for fib_ratio, (level_name, level_price) in level_map.items():
                if fib_ratio not in entry_levels:
                    continue
                if level_price == 0:
                    continue

                # Check if candle touches level
                if not (current_low <= level_price <= current_high):
                    continue

                # Confluence check
                confluence_score = self._check_confluence_simple(
                    window, current_candle, fib
                )

                if confluence_score < config.require_confluence:
                    continue

                # Trade parameters
                entry = level_price
                sl = fib.swing_low * (1 - 0.003)
                tp1 = fib.level_618
                risk = abs(entry - sl)

                if risk == 0 or tp1 <= entry:
                    continue

                # Position sizing
                risk_amount = balance * 0.02
                size_mult = {0.786: 0.25, 0.882: 0.5, 0.941: 0.75}.get(fib_ratio, 0.5)
                qty = (risk_amount / risk) * size_mult

                # Simulate forward
                pnl, exit_price, exit_type = self._simulate_trade(
                    candles, i, entry, sl, tp1
                )

                actual_pnl = pnl * qty
                balance += actual_pnl

                trades.append({
                    "fib_level": level_name,
                    "entry_price": round(entry, 2),
                    "exit_price": round(exit_price, 2),
                    "stop_loss": round(sl, 2),
                    "take_profit": round(tp1, 2),
                    "pnl": round(actual_pnl, 2),
                    "pnl_percent": round((pnl / entry) * 100, 2) if entry else 0,
                    "confluence": confluence_score,
                    "exit_type": exit_type,
                    "crv": round(self.fib.calculate_crv(entry, sl, tp1), 2),
                })

                equity_curve.append(round(balance, 2))
                peak_balance = max(peak_balance, balance)
                trade_taken = True

                # Skip forward after trade entry
                i += 10
                break

            if not trade_taken:
                i += 1

        return self._build_result(trades, equity_curve, config.initial_capital, balance)

    def _check_confluence_simple(self, candles: list[dict], current: dict,
                                 fib: FibonacciLevels) -> int:
        """Simplified confluence check for backtesting"""
        score = 1  # Fib level hit = 1

        # Hammer check
        if self.indicators.is_hammer(current):
            score += 1

        # EMA confluence
        closes = [float(c.get("close", c.get("c", 0))) for c in candles]
        ema200 = self.indicators.ema(closes, 200)

        if ema200 and ema200[-1] > 0:
            current_price = float(current.get("close", current.get("c", 0)))
            dist = abs(current_price - ema200[-1]) / ema200[-1]
            if dist < 0.02:
                score += 1

        # Bullish engulfing on previous
        if len(candles) >= 2:
            if self.indicators.is_bullish_engulfing(candles[-2], current):
                score += 1

        # Volume check: current volume > average
        volumes = [float(c.get("volume", c.get("v", 0))) for c in candles[-20:]]
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        current_vol = float(current.get("volume", current.get("v", 0)))
        if avg_vol > 0 and current_vol > avg_vol * 1.2:
            score += 1

        return score

    def _simulate_trade(self, candles: list[dict], entry_idx: int,
                        entry: float, sl: float, tp: float) -> tuple[float, float, str]:
        """Simulate trade forward from entry candle. Returns (pnl_per_unit, exit_price, type)"""
        max_hold = 50  # Max candles to hold

        for j in range(entry_idx + 1, min(entry_idx + max_hold, len(candles))):
            c = candles[j]
            low = float(c.get("low", c.get("l", 0)))
            high = float(c.get("high", c.get("h", 0)))

            # Check stop loss first (worst case)
            if low <= sl:
                pnl = sl - entry
                return (pnl, sl, "SL")

            # Check take profit
            if high >= tp:
                pnl = tp - entry
                return (pnl, tp, "TP")

        # Max hold reached - exit at last close
        if entry_idx + max_hold < len(candles):
            exit_price = float(candles[entry_idx + max_hold].get("close",
                              candles[entry_idx + max_hold].get("c", 0)))
        else:
            exit_price = float(candles[-1].get("close", candles[-1].get("c", 0)))

        pnl = exit_price - entry
        return (pnl, exit_price, "TIMEOUT")

    def _build_result(self, trades: list[dict], equity_curve: list[float],
                      initial: float, final: float) -> BacktestResult:
        if not trades:
            return BacktestResult(
                final_balance=initial,
                equity_curve=[initial],
            )

        pnls = [t["pnl"] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0.0001

        # Max drawdown
        peak = initial
        max_dd = 0
        running = initial
        for eq in equity_curve:
            running = eq
            peak = max(peak, running)
            dd = ((peak - running) / peak) * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        crvs = [t.get("crv", 0) for t in trades]

        return BacktestResult(
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=(len(wins) / len(trades)) * 100 if trades else 0,
            total_pnl=round(sum(pnls), 2),
            final_balance=round(final, 2),
            return_pct=round(((final - initial) / initial) * 100, 2),
            avg_crv=round(sum(crvs) / len(crvs), 2) if crvs else 0,
            best_trade=round(max(pnls), 2) if pnls else 0,
            worst_trade=round(min(pnls), 2) if pnls else 0,
            max_drawdown=round(max_dd, 2),
            profit_factor=round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0,
            trades=trades,
            equity_curve=equity_curve,
        )
