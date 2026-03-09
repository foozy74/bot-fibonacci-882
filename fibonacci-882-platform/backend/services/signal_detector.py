# backend/services/signal_detector.py
import uuid
import asyncio
from datetime import datetime, timezone
from models.schemas import (
    Signal, SignalType, SignalStrength,
    ConfluenceCheck, FibonacciLevels,
)
from services.swing_detector import swing_detector
from services.fibonacci_engine import fibonacci_engine
from services.indicator_service import IndicatorService
from services.telegram_bot import telegram_bot
from config import settings


class SignalDetector:
    """Detects Fibonacci-882 Sniper entry signals with confluence scoring"""

    def __init__(self):
        self.indicators = IndicatorService()
        self.active_signals: list[Signal] = []
        self._max_signals = 20

    def detect(self, candles: list[dict], symbol: str, timeframe: str) -> list[Signal]:
        """Main detection pipeline"""
        if len(candles) < 60:
            return []

        # 1. Find swing points
        swing_high, swing_low = swing_detector.get_latest_swing_pair(candles)
        if not swing_high or not swing_low:
            return []

        # 2. Calculate Fibonacci levels
        fib = fibonacci_engine.calculate_levels(swing_high, swing_low)

        # 3. Get current candle and previous
        current = candles[-1]
        current_price = float(current.get("close", current.get("c", 0)))
        current_low = float(current.get("low", current.get("l", 0)))
        current_high = float(current.get("high", current.get("h", 0)))

        # 4. Calculate indicators
        emas = self.indicators.calculate_emas(candles)

        # 5. Check each Fibonacci entry level
        signals = []
        entry_levels = {
            "0.786": fib.level_786,
            "0.882": fib.level_882,
            "0.941": fib.level_941,
        }

        for level_name, level_price in entry_levels.items():
            if level_price == 0:
                continue

            # Check proximity
            proximity = abs(current_price - level_price) / level_price if level_price else 1
            if proximity > settings.fib_proximity_threshold:
                # Also check if candle wick touched
                if not (current_low <= level_price <= current_high):
                    continue

            # 6. Run confluence checks
            confluence = self._check_confluence(
                candles, current, fib, level_name, level_price, emas
            )

            # Minimum 2 confluence factors
            if confluence.total_score < 2:
                continue

            # 7. Calculate trade parameters
            sl = fib.swing_low * (1 - settings.risk.stop_loss_buffer)
            tp_prices = self._calculate_tp_levels(fib, level_price)

            crv = fibonacci_engine.calculate_crv(
                level_price, sl,
                tp_prices[0] if tp_prices else fib.level_618
            )

            # 8. Determine strength
            strength = self._score_to_strength(confluence.total_score)

            # 9. Build signal
            signal = Signal(
                id=str(uuid.uuid4())[:8],
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                timeframe=timeframe,
                type=SignalType.LONG,
                strength=strength,
                entry_price=round(level_price, 2),
                stop_loss=round(sl, 2),
                take_profits=[round(tp, 2) for tp in tp_prices],
                fib_levels=fib,
                confluence=confluence,
                crv=crv,
                notes=f"Fib {level_name} | Score {confluence.total_score}/5 | CRV {crv}",
            )

            signals.append(signal)

        # Send Telegram notifications for new signals
        if signals and settings.telegram.enabled and settings.telegram.notify_signals:
            try:
                # Send notification for the strongest signal
                strongest = max(signals, key=lambda s: s.strength.value)
                asyncio.create_task(telegram_bot.send_signal(strongest.dict()))
            except Exception as e:
                print(f"Telegram signal notification error: {e}")

        # Update active signals
        self.active_signals = signals[-self._max_signals:]
        return signals

    def _check_confluence(self, candles: list[dict], current: dict,
                          fib: FibonacciLevels, level_name: str,
                          level_price: float, emas: dict) -> ConfluenceCheck:
        """Run all confluence checks and score"""
        check = ConfluenceCheck()

        # 1. Fib level hit
        check.fib_level_hit = True
        check.fib_level_name = level_name
        check.total_score += 1

        # 2. Hammer detection
        if self.indicators.is_hammer(current):
            check.hammer_detected = True
            check.total_score += 1

        # 3. Hanging man on previous candles (bearish exhaustion before reversal)
        if len(candles) >= 3:
            if self.indicators.is_hanging_man(candles[-2]):
                check.hanging_man_detected = True

        # 4. Guss indicator check (price approaching 50 EMA without counter candle)
        guss_result = self._check_guss(candles, emas)
        if guss_result == "valid":
            check.guss_valid = True
            check.total_score += 1
        elif guss_result == "invalidated":
            check.guss_invalidated = True

        # 5. LSOB detection
        lsob = self._find_lsob(candles, fib)
        if lsob:
            check.lsob_present = True
            check.lsob_price = lsob
            check.total_score += 1

        # 6. EMA confluence (price near EMA 200 = support)
        if emas["ema_200"] and len(emas["ema_200"]) > 0:
            ema200_val = emas["ema_200"][-1]
            if ema200_val > 0:
                ema_dist = abs(level_price - ema200_val) / ema200_val
                if ema_dist < 0.02:  # Within 2% of EMA 200
                    check.ema_confluence = True
                    check.total_score += 1

        return check

    def _check_guss(self, candles: list[dict], emas: dict) -> str:
        """
        Guss indicator v7.4: Price approaches 50 EMA without counter candle.
        Returns 'valid', 'invalidated', or 'none'
        """
        if not emas["ema_50"] or len(candles) < 5:
            return "none"

        ema50 = emas["ema_50"]

        # Check last 5 candles approaching 50 EMA
        for i in range(-5, -1):
            idx = len(candles) + i
            if idx < 0 or idx >= len(ema50):
                continue

            c = candles[idx]
            close = float(c.get("close", c.get("c", 0)))
            open_p = float(c.get("open", c.get("o", 0)))
            ema_val = ema50[idx]

            if ema_val == 0:
                continue

            # Check if approaching EMA from below (for long)
            dist = abs(close - ema_val) / ema_val
            if dist < 0.005:  # Within 0.5%
                # Check no counter candle (gray/red for longs)
                has_counter = False
                for j in range(idx + 1, len(candles)):
                    cj = candles[j]
                    cj_close = float(cj.get("close", cj.get("c", 0)))
                    cj_open = float(cj.get("open", cj.get("o", 0)))
                    if cj_close < cj_open:  # Red candle = counter
                        has_counter = True
                        break

                if has_counter:
                    return "invalidated"
                return "valid"

        return "none"

    def _find_lsob(self, candles: list[dict], fib: FibonacciLevels) -> float | None:
        """
        Find Last Step Order Block: last candle before significant impulse move.
        Returns the LSOB price level or None.
        """
        if len(candles) < 10:
            return None

        # Look for large impulse candles (>1.5x average body)
        bodies = []
        for c in candles[-30:]:
            o = float(c.get("open", c.get("o", 0)))
            cl = float(c.get("close", c.get("c", 0)))
            bodies.append(abs(cl - o))

        avg_body = sum(bodies) / len(bodies) if bodies else 0
        if avg_body == 0:
            return None

        # Find impulse candle near fib zone
        for i in range(len(candles) - 2, max(len(candles) - 20, 0), -1):
            c = candles[i]
            o = float(c.get("open", c.get("o", 0)))
            cl = float(c.get("close", c.get("c", 0)))
            body = abs(cl - o)

            if body > avg_body * 1.5 and cl > o:  # Bullish impulse
                # Previous candle is the LSOB
                if i > 0:
                    prev = candles[i - 1]
                    lsob_price = float(prev.get("close", prev.get("c", 0)))
                    return lsob_price

        return None

    def _calculate_tp_levels(self, fib: FibonacciLevels, entry: float) -> list[float]:
        """Calculate take-profit levels at Fibonacci retracements going up"""
        tps = []
        potential = [fib.level_618, fib.level_500, fib.level_382, fib.level_236, fib.level_0]

        for tp in potential:
            if tp > entry:
                tps.append(tp)

        return tps[:3]  # Max 3 TP levels

    def _score_to_strength(self, score: int) -> SignalStrength:
        if score >= 4:
            return SignalStrength.SNIPER
        elif score >= 3:
            return SignalStrength.STRONG
        elif score >= 2:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def get_active_signals(self) -> list[Signal]:
        return self.active_signals


signal_detector = SignalDetector()
