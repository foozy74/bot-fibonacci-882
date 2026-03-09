# backend/services/telegram_bot.py
"""
Telegram Bot service for sending notifications
"""
import aiohttp
import logging
from config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramBot:
    """
    Telegram bot for sending trading notifications
    """

    def __init__(self):
        self.base_url = TELEGRAM_API_URL
        self.session: aiohttp.ClientSession = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """
        Send message to Telegram chat
        
        Args:
            text: Message text (supports Markdown)
            parse_mode: Parse mode (Markdown or HTML)
        
        Returns:
            bool: True if sent successfully
        """
        if not settings.telegram.enabled:
            logger.debug("Telegram not enabled, skipping message")
            return False
        
        if not settings.telegram.bot_token or not settings.telegram.chat_id:
            logger.error("Telegram bot token or chat ID not configured")
            return False
        
        session = await self._get_session()
        url = f"{self.base_url}/bot{settings.telegram.bot_token}/sendMessage"
        
        payload = {
            "chat_id": settings.telegram.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                
                if data.get("ok"):
                    logger.info(f"Telegram message sent: {text[:50]}...")
                    return True
                else:
                    logger.error(f"Telegram API error: {data.get('description', 'Unknown')}")
                    return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def send_signal(self, signal: dict) -> bool:
        """
        Send signal notification
        
        Args:
            signal: Signal dict with entry, sl, tp, etc.
        """
        if not settings.telegram.notify_signals:
            return False
        
        strength_emoji = {
            "SNIPER": "🎯",
            "STRONG": "💪",
            "MODERATE": "⚠️",
            "WEAK": "📊"
        }
        
        emoji = strength_emoji.get(signal.get("strength", ""), "📈")
        
        text = f"""
{emoji} *SIGNAL DETECTED*

*Symbol:* {signal.get("symbol", "N/A")}
*Type:* {signal.get("type", "LONG").upper()}
*Strength:* {signal.get("strength", "N/A")}

*Entry:* ${signal.get("entry_price", 0):,.2f}
*Stop Loss:* ${signal.get("stop_loss", 0):,.2f}
*Take Profits:* {", ".join(f"${tp:,.2f}" for tp in signal.get("take_profits", []))}

*CRV:* {signal.get("crv", 0):.2f}
*Score:* {signal.get("confluence", {}).get("total_score", 0)}/5

*Notes:* {signal.get("notes", "")}
"""
        
        return await self._send_message(text)

    async def send_trade_open(self, trade: dict) -> bool:
        """
        Send trade opened notification
        """
        if not settings.telegram.notify_trades:
            return False
        
        text = f"""
✅ *TRADE OPENED*

*ID:* #{trade.get("id", "N/A")}
*Symbol:* {trade.get("symbol", "N/A")}
*Side:* {trade.get("side", "LONG").upper()}

*Entry:* ${trade.get("entry_price", 0):,.2f}
*Size:* {trade.get("position_size", 0):.6f}
*Stop Loss:* ${trade.get("stop_loss", 0):,.2f}

*Risk:* ${abs(trade.get("entry_price", 0) - trade.get("stop_loss", 0)) * trade.get("position_size", 0):,.2f}
"""
        
        return await self._send_message(text)

    async def send_trade_close(self, trade: dict) -> bool:
        """
        Send trade closed notification
        """
        if not settings.telegram.notify_trades:
            return False
        
        pnl = trade.get("pnl", 0)
        pnl_percent = trade.get("pnl_percent", 0)
        pnl_emoji = "💰" if pnl > 0 else "💸" if pnl < 0 else "😐"
        
        exit_reason = trade.get("status", "CLOSED")
        if exit_reason == "closed_tp":
            exit_reason = "✅ TP Hit"
        elif exit_reason == "closed_sl":
            exit_reason = "❌ SL Hit"
        elif exit_reason == "closed_manual":
            exit_reason = "🔧 Manual Close"
        
        text = f"""
{pnl_emoji} *TRADE CLOSED*

*ID:* #{trade.get("id", "N/A")}
*Symbol:* {trade.get("symbol", "N/A")}

*Entry:* ${trade.get("entry_price", 0):,.2f}
*Exit:* ${trade.get("exit_price", 0):,.2f}
*PnL:* ${pnl:,.2f} ({pnl_percent:+.2f}%)

*Reason:* {exit_reason}
"""
        
        return await self._send_message(text)

    async def send_error(self, message: str) -> bool:
        """
        Send error notification
        """
        if not settings.telegram.notify_errors:
            return False
        
        text = f"""
🚨 *ERROR ALERT*

{message}
"""
        
        return await self._send_message(text)

    async def send_daily_summary(self, stats: dict) -> bool:
        """
        Send daily trading summary
        """
        if not settings.telegram.daily_summary:
            return False
        
        total_trades = stats.get("total_trades", 0)
        winning = stats.get("winning_trades", 0)
        losing = stats.get("losing_trades", 0)
        total_pnl = stats.get("total_pnl", 0)
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        
        pnl_emoji = "📈" if total_pnl > 0 else "📉" if total_pnl < 0 else "➡️"
        
        text = f"""
{pnl_emoji} *DAILY SUMMARY*

*Total Trades:* {total_trades}
*Winning:* {winning}
*Losing:* {losing}
*Win Rate:* {win_rate:.1f}%

*Total PnL:* ${total_pnl:,.2f}

*Best Trade:* ${stats.get("best_trade", 0):,.2f}
*Worst Trade:* ${stats.get("worst_trade", 0):,.2f}
"""
        
        return await self._send_message(text)

    async def test_connection(self) -> bool:
        """
        Test Telegram connection
        """
        text = """
✅ *Test Message*

This is a test notification from Fibonacci-882 Sniper Platform.

If you receive this, Telegram notifications are working correctly!
"""
        
        return await self._send_message(text)

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Singleton instance
telegram_bot = TelegramBot()
