# backend/services/trade_manager.py
import uuid
import asyncio
from datetime import datetime, timezone
from models.schemas import Trade, TradeStatus, PaperAccount, Signal
from config import settings
from services.telegram_bot import telegram_bot
from services.telegram_bot import telegram_bot


class TradeManager:
    """Manages paper and live trades"""

    def __init__(self):
        self.account = PaperAccount(
            balance=settings.paper_balance,
            equity=settings.paper_balance,
        )

    def get_account(self) -> PaperAccount:
        self._update_equity()
        return self.account

    def open_trade(self, signal: Signal, current_price: float) -> Trade | None:
        """Open a new trade from a signal"""
        # Calculate position size based on risk
        risk_per_unit = abs(signal.entry_price - signal.stop_loss)
        if risk_per_unit == 0:
            return None

        risk_amount = self.account.balance * settings.risk.max_risk_per_trade

        # Size multiplier based on fib level
        fib_name = signal.confluence.fib_level_name if signal.confluence else "0.882"
        size_mult = settings.risk.position_sizes.get(fib_name, 0.5)

        position_size = (risk_amount / risk_per_unit) * size_mult

        trade = Trade(
            id=str(uuid.uuid4())[:8],
            signal_id=signal.id,
            timestamp_open=datetime.now(timezone.utc),
            symbol=signal.symbol,
            side="LONG",
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profits=signal.take_profits,
            position_size=round(position_size, 6),
            status=TradeStatus.ACTIVE,
            fib_level=fib_name,
        )

        self.account.open_positions.append(trade)
        
        # Send Telegram notification
        if settings.telegram.enabled and settings.telegram.notify_trades:
            asyncio.create_task(telegram_bot.send_trade_open(trade.dict()))
        
        return trade

    def check_open_trades(self, current_price: float) -> list[Trade]:
        """Check all open trades against current price for SL/TP hits"""
        closed = []
        still_open = []

        for trade in self.account.open_positions:
            # Check Stop Loss
            if current_price <= trade.stop_loss:
                trade.exit_price = trade.stop_loss
                trade.status = TradeStatus.CLOSED_SL
                trade.timestamp_close = datetime.now(timezone.utc)
                trade.pnl = round(
                    (trade.exit_price - trade.entry_price) * trade.position_size, 2
                )
                trade.pnl_percent = round(
                    ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100, 2
                ) if trade.entry_price else 0

                self.account.balance += trade.pnl
                self.account.total_pnl += trade.pnl
                self.account.closed_trades.append(trade)
                closed.append(trade)
                
                # Send Telegram notification
                if settings.telegram.enabled and settings.telegram.notify_trades:
                    asyncio.create_task(telegram_bot.send_trade_close(trade.dict()))
                
                continue

            # Check Take Profits (first TP)
            if trade.take_profits and current_price >= trade.take_profits[0]:
                trade.exit_price = trade.take_profits[0]
                trade.status = TradeStatus.CLOSED_TP
                trade.timestamp_close = datetime.now(timezone.utc)
                trade.pnl = round(
                    (trade.exit_price - trade.entry_price) * trade.position_size, 2
                )
                trade.pnl_percent = round(
                    ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100, 2
                ) if trade.entry_price else 0

                self.account.balance += trade.pnl
                self.account.total_pnl += trade.pnl
                self.account.closed_trades.append(trade)
                closed.append(trade)
                
                # Send Telegram notification
                if settings.telegram.enabled and settings.telegram.notify_trades:
                    asyncio.create_task(telegram_bot.send_trade_close(trade.dict()))
                
                continue

            still_open.append(trade)

        self.account.open_positions = still_open
        self._update_equity()
        return closed

    def close_all(self, current_price: float) -> list[Trade]:
        """Force close all open positions"""
        closed = []
        for trade in self.account.open_positions:
            trade.exit_price = current_price
            trade.status = TradeStatus.CLOSED_MANUAL
            trade.timestamp_close = datetime.now(timezone.utc)
            trade.pnl = round(
                (trade.exit_price - trade.entry_price) * trade.position_size, 2
            )
            trade.pnl_percent = round(
                ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100, 2
            ) if trade.entry_price else 0

            self.account.balance += trade.pnl
            self.account.total_pnl += trade.pnl
            self.account.closed_trades.append(trade)
            closed.append(trade)
            
            # Send Telegram notification for manual close
            if settings.telegram.enabled and settings.telegram.notify_trades:
                asyncio.create_task(telegram_bot.send_trade_close(trade.dict()))

        self.account.open_positions = []
        self._update_equity()
        return closed

    def reset(self):
        """Reset account to initial state"""
        self.account = PaperAccount(
            balance=settings.paper_balance,
            equity=settings.paper_balance,
        )

    def _update_equity(self):
        """Recalculate equity from balance + unrealized PnL"""
        self.account.equity = self.account.balance


trade_manager = TradeManager()
