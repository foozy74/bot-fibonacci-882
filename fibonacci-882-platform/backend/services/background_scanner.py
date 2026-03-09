# backend/services/background_scanner.py
"""
Background Scanner for automatic market monitoring
Runs independently of WebSocket connections
Production-ready for Coolify deployment
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from config import settings
from services.binance_client import binance_client
from services.signal_detector import signal_detector
from services.telegram_bot import telegram_bot

logger = logging.getLogger(__name__)

# Path for signal history
SIGNAL_HISTORY_FILE = Path(__file__).parent.parent / "data" / "signal_history.json"


class BackgroundScanner:
    """
    Background market scanner that runs continuously
    Scans for signals at configurable intervals
    """

    def __init__(self):
        self.is_running = False
        self.scan_interval = 60  # Default: 60 seconds
        self.last_scan = None
        self.total_scans = 0
        self.signals_found = 0
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """Start the background scanner"""
        if self.is_running:
            logger.warning("Background scanner already running")
            return

        self.is_running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._scan_loop())
        logger.info(f"🔍 Background scanner started (interval: {self.scan_interval}s)")

    async def stop(self):
        """Stop the background scanner"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("🔍 Background scanner stopped")

    async def _scan_loop(self):
        """Main scanning loop"""
        while not self._stop_event.is_set():
            try:
                await self._perform_scan()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scan error: {e}")
            
            # Wait for next scan or stop event
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.scan_interval)
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Continue to next scan

    async def _perform_scan(self):
        """Perform a single market scan"""
        self.total_scans += 1
        start_time = datetime.now(timezone.utc)
        
        logger.debug(f"🔍 Scan #{self.total_scans} started")
        
        try:
            # Get candle data from Binance
            candles = await binance_client.get_klines(
                symbol=settings.symbol,
                interval=settings.timeframe.value,
                limit=500
            )
            
            if not candles or len(candles) < 50:
                logger.warning(f"Insufficient candle data for scan: {len(candles) if candles else 0}")
                return
            
            # Run signal detection
            signals = signal_detector.detect(
                candles,
                settings.symbol,
                settings.timeframe.value
            )
            
            self.last_scan = start_time
            
            if signals:
                self.signals_found += len(signals)
                logger.info(f"🎯 Scan #{self.total_scans}: Found {len(signals)} signal(s)")
                
                # Send Telegram notifications for strong signals only
                if settings.telegram.enabled and settings.telegram.notify_signals:
                    for signal in signals:
                        if signal.strength in ["SNIPER", "STRONG"]:
                            await telegram_bot.send_signal(signal.dict())
                            logger.info(f"📱 Telegram notification sent for {signal.strength} signal")
                
                # Save to signal history
                self._save_signal_history(signals)
            else:
                logger.debug(f"✓ Scan #{self.total_scans}: No signals")
            
        except Exception as e:
            logger.error(f"Scan #{self.total_scans} failed: {e}", exc_info=True)
            raise

    def _save_signal_history(self, signals):
        """Save signals to history file"""
        try:
            # Load existing history
            history = self._load_signal_history()
            
            # Add new signals
            for signal in signals:
                history.append({
                    "id": signal.id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "symbol": signal.symbol,
                    "type": signal.type.value if signal.type else "LONG",
                    "strength": signal.strength.value if signal.strength else "WEAK",
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profits": signal.take_profits,
                    "crv": signal.crv,
                    "confluence_score": signal.confluence.total_score if signal.confluence else 0
                })
            
            # Keep only last 1000 signals
            if len(history) > 1000:
                history = history[-1000:]
            
            # Save to file
            SIGNAL_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SIGNAL_HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.debug(f"💾 Signal history saved ({len(history)} signals)")
            
        except Exception as e:
            logger.error(f"Failed to save signal history: {e}")

    def _load_signal_history(self) -> list:
        """Load signal history from file"""
        if not SIGNAL_HISTORY_FILE.exists():
            return []
        
        try:
            with open(SIGNAL_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load signal history: {e}")
            return []

    def get_stats(self) -> dict:
        """Get scanner statistics"""
        return {
            "is_running": self.is_running,
            "scan_interval": self.scan_interval,
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "total_scans": self.total_scans,
            "signals_found": self.signals_found,
            "history_count": len(self._load_signal_history())
        }

    def update_interval(self, interval: int):
        """Update scan interval (in seconds)"""
        if interval < 10:
            logger.warning(f"Scan interval too low ({interval}s), setting to 10s")
            interval = 10
        self.scan_interval = interval
        logger.info(f"🔄 Scan interval updated to {interval}s")


# Singleton instance
background_scanner = BackgroundScanner()
