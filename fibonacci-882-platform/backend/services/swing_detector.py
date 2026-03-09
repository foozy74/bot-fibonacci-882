# backend/services/swing_detector.py
from models.schemas import SwingPoint
from config import settings


class SwingDetector:
    """Detect swing highs and lows from candlestick data"""

    def find_swing_highs(self, candles: list[dict], lookback: int = None) -> list[SwingPoint]:
        lb = lookback or settings.fibonacci.swing_lookback
        swings = []

        for i in range(lb, len(candles) - lb):
            high = float(candles[i].get("high", candles[i].get("h", 0)))

            is_swing = True
            for j in range(i - lb, i + lb + 1):
                if j == i:
                    continue
                if j < 0 or j >= len(candles):
                    continue
                other_high = float(candles[j].get("high", candles[j].get("h", 0)))
                if other_high > high:
                    is_swing = False
                    break

            if is_swing:
                swings.append(SwingPoint(
                    price=high,
                    index=i,
                    timestamp=int(candles[i].get("timestamp", candles[i].get("ts", 0))),
                    type="high"
                ))

        return swings

    def find_swing_lows(self, candles: list[dict], lookback: int = None) -> list[SwingPoint]:
        lb = lookback or settings.fibonacci.swing_lookback
        swings = []

        for i in range(lb, len(candles) - lb):
            low = float(candles[i].get("low", candles[i].get("l", 0)))

            is_swing = True
            for j in range(i - lb, i + lb + 1):
                if j == i:
                    continue
                if j < 0 or j >= len(candles):
                    continue
                other_low = float(candles[j].get("low", candles[j].get("l", 0)))
                if other_low < low:
                    is_swing = False
                    break

            if is_swing:
                swings.append(SwingPoint(
                    price=low,
                    index=i,
                    timestamp=int(candles[i].get("timestamp", candles[i].get("ts", 0))),
                    type="low"
                ))

        return swings

    def get_latest_swing_pair(self, candles: list[dict]) -> tuple[SwingPoint | None, SwingPoint | None]:
        """Get most recent swing high and swing low pair for Fibonacci measurement"""
        highs = self.find_swing_highs(candles)
        lows = self.find_swing_lows(candles)

        if not highs or not lows:
            return None, None

        # Get the latest swing high
        latest_high = max(highs, key=lambda s: s.index)

        # Find swing low BEFORE the swing high (for wick-to-wick measurement)
        valid_lows = [l for l in lows if l.index < latest_high.index]

        if not valid_lows:
            # Try finding swing low after if no prior exists
            valid_lows = lows

        if not valid_lows:
            return None, None

        latest_low = min(valid_lows, key=lambda s: s.price)

        return latest_high, latest_low


swing_detector = SwingDetector()
