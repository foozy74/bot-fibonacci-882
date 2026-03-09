# backend/services/fibonacci_engine.py
from models.schemas import FibonacciLevels, SwingPoint
from config import settings


class FibonacciEngine:
    """Calculate Fibonacci retracement levels from swing points (wick-to-wick)"""

    LEVELS = {
        "0.000": 0.000,
        "0.236": 0.236,
        "0.382": 0.382,
        "0.500": 0.500,
        "0.618": 0.618,
        "0.786": 0.786,
        "0.882": 0.882,
        "0.941": 0.941,
        "1.000": 1.000,
    }

    def calculate_levels(self, swing_high: SwingPoint, swing_low: SwingPoint) -> FibonacciLevels:
        """
        Calculate Fibonacci levels from Swing Low to Swing High.
        Retracement: Level = High - (High - Low) * ratio
        """
        high = swing_high.price
        low = swing_low.price
        diff = high - low

        return FibonacciLevels(
            swing_high=high,
            swing_low=low,
            level_0=round(high, 2),
            level_236=round(high - diff * 0.236, 2),
            level_382=round(high - diff * 0.382, 2),
            level_500=round(high - diff * 0.500, 2),
            level_618=round(high - diff * 0.618, 2),
            level_786=round(high - diff * 0.786, 2),
            level_882=round(high - diff * 0.882, 2),
            level_941=round(high - diff * 0.941, 2),
            level_100=round(low, 2),
        )

    def get_nearest_level(self, price: float, levels: FibonacciLevels) -> tuple[str, float] | None:
        """Check if price is near a key entry level"""
        entry_levels = {
            "0.786": levels.level_786,
            "0.882": levels.level_882,
            "0.941": levels.level_941,
        }

        threshold = settings.fib_proximity_threshold

        for name, level_price in entry_levels.items():
            if level_price == 0:
                continue
            proximity = abs(price - level_price) / level_price
            if proximity <= threshold:
                return (name, level_price)

        return None

    def calculate_crv(self, entry: float, stop_loss: float, take_profit: float) -> float:
        """Calculate CRV (Chance-Risiko-Verhältnis)"""
        risk = abs(entry - stop_loss)
        if risk == 0:
            return 0
        reward = abs(take_profit - entry)
        return round(reward / risk, 2)


fibonacci_engine = FibonacciEngine()
