# backend/services/indicator_service.py
from config import settings


class IndicatorService:
    """Technical indicators: EMA, AVWAP, Candlestick patterns"""

    def ema(self, prices: list[float], period: int) -> list[float]:
        if len(prices) < period:
            return [0.0] * len(prices)

        ema_values = [0.0] * len(prices)
        multiplier = 2 / (period + 1)
        ema_values[period - 1] = sum(prices[:period]) / period

        for i in range(period, len(prices)):
            ema_values[i] = (prices[i] - ema_values[i - 1]) * multiplier + ema_values[i - 1]

        return ema_values

    def calculate_emas(self, candles: list[dict]) -> dict:
        closes = [float(c.get("close", c.get("c", 0))) for c in candles]
        return {
            "ema_21": self.ema(closes, settings.indicators.ema_fast),
            "ema_50": self.ema(closes, settings.indicators.ema_medium),
            "ema_200": self.ema(closes, settings.indicators.ema_slow),
        }

    def anchored_vwap(self, candles: list[dict], anchor_index: int) -> list[float]:
        """Calculate AVWAP from anchor point (swing high)"""
        avwap = [0.0] * len(candles)
        cum_vol = 0.0
        cum_vol_price = 0.0

        for i in range(anchor_index, len(candles)):
            typical = (
                float(candles[i].get("high", candles[i].get("h", 0))) +
                float(candles[i].get("low", candles[i].get("l", 0))) +
                float(candles[i].get("close", candles[i].get("c", 0)))
            ) / 3
            vol = float(candles[i].get("volume", candles[i].get("v", 1)))
            cum_vol += vol
            cum_vol_price += typical * vol
            avwap[i] = cum_vol_price / cum_vol if cum_vol > 0 else 0

        return avwap

    def is_hammer(self, candle: dict) -> bool:
        """Detect Hammer candle (bullish reversal at bottom)"""
        o = float(candle.get("open", candle.get("o", 0)))
        h = float(candle.get("high", candle.get("h", 0)))
        l = float(candle.get("low", candle.get("l", 0)))
        c = float(candle.get("close", candle.get("c", 0)))

        body = abs(c - o)
        if body == 0:
            body = 0.0001

        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        total_range = h - l

        if total_range == 0:
            return False

        # Hammer: long lower wick, small upper wick, small body
        ratio = settings.indicators.hammer_wick_ratio
        return (
            lower_wick >= body * ratio and
            upper_wick <= body * 0.5 and
            body / total_range <= 0.4
        )

    def is_hanging_man(self, candle: dict) -> bool:
        """Detect Hanging Man (bearish reversal at top) - same shape, different context"""
        o = float(candle.get("open", candle.get("o", 0)))
        h = float(candle.get("high", candle.get("h", 0)))
        l = float(candle.get("low", candle.get("l", 0)))
        c = float(candle.get("close", candle.get("c", 0)))

        body = abs(c - o)
        if body == 0:
            body = 0.0001

        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        total_range = h - l

        if total_range == 0:
            return False

        ratio = settings.indicators.hammer_wick_ratio
        return (
            lower_wick >= body * ratio and
            upper_wick <= body * 0.5 and
            c < o  # Bearish close
        )

    def is_bullish_engulfing(self, prev: dict, current: dict) -> bool:
        """Detect Bullish Engulfing pattern"""
        p_o = float(prev.get("open", prev.get("o", 0)))
        p_c = float(prev.get("close", prev.get("c", 0)))
        c_o = float(current.get("open", current.get("o", 0)))
        c_c = float(current.get("close", current.get("c", 0)))

        return (
            p_c < p_o and          # Previous was bearish
            c_c > c_o and          # Current is bullish
            c_o <= p_c and         # Current open below prev close
            c_c >= p_o             # Current close above prev open
        )
