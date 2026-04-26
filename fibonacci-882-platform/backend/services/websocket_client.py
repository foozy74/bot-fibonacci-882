# backend/services/websocket_client.py
"""
Binance Futures WebSocket Client using aiohttp
Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams

Supports:
- Kline/Candlestick streams
- Mark Price streams
- Aggregate Trade streams
- 24hr Ticker streams
- Order Book streams
- Auto-reconnect with exponential backoff
- Subscription management
"""
import asyncio
import json
import time
import aiohttp
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Binance Futures WebSocket URLs
BINANCE_WS_URL = "wss://fstream.binance.com/ws"
BINANCE_TESTNET_WS_URL = "wss://fstream.binancefuture.com/ws"

# Stream types
STREAM_KLINE = "kline"
STREAM_MARK_PRICE = "markPrice"
STREAM_AGG_TRADE = "aggTrade"
STREAM_TICKER = "ticker"
STREAM_DEPTH = "depth"
STREAM_BOOK_TICKER = "bookTicker"


class BinanceWebSocketClient:
    """
    aiohttp-based WebSocket client for Binance Futures market data
    - Auto-reconnect with exponential backoff
    - Multiple stream subscriptions
    - Data caching for latest values
    - Callback support for real-time updates
    """

    def __init__(self, testnet: bool = False):
        self.testnet = testnet
        self.ws_url = BINANCE_TESTNET_WS_URL if testnet else BINANCE_WS_URL
        
        # Connection state
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.is_connected = False
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Reconnect settings
        self._reconnect_delay = 5
        self._max_reconnect_delay = 60
        self._current_reconnect_delay = 5
        
        # Subscriptions: list of stream names
        self._subscriptions: List[str] = []
        
        # Data caches
        self._kline_data: Dict[str, List[dict]] = defaultdict(list)  # symbol_interval -> klines
        self._mark_price_data: Dict[str, dict] = {}  # symbol -> mark price
        self._ticker_data: Dict[str, dict] = {}  # symbol -> 24hr ticker
        self._trade_data: Dict[str, List[dict]] = defaultdict(list)  # symbol -> trades
        self._depth_data: Dict[str, dict] = {}  # symbol -> order book
        
        # Callbacks for real-time updates
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Statistics
        self._message_count = 0
        self._last_message_time = 0
        self._reconnect_count = 0

    async def start(self):
        """Start WebSocket connection and message processing"""
        self._running = True
        await self._connect()

    async def _connect(self):
        """Establish WebSocket connection with retry logic"""
        while self._running:
            try:
                if not self.session or self.session.closed:
                    self.session = aiohttp.ClientSession()
                
                # Build combined stream URL
                stream_url = self._build_stream_url()
                
                logger.info(f"Connecting to {stream_url}")
                async with self.session.ws_connect(
                    stream_url,
                    heartbeat=180,  # Send ping every 180 seconds
                    receive_timeout=300,
                ) as ws:
                    self.ws = ws
                    self.is_connected = True
                    self._current_reconnect_delay = 5
                    self._reconnect_count = 0
                    
                    logger.info(f"✓ WebSocket connected to {self.ws_url}")
                    
                    # Resubscribe to streams
                    if self._subscriptions:
                        logger.info(f"Resubscribing to {len(self._subscriptions)} streams")
                    
                    # Start message processing
                    await self._process_messages()
                    
            except asyncio.CancelledError:
                logger.info("WebSocket connection cancelled")
                break
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.is_connected = False
                
            # Reconnect with exponential backoff
            if self._running:
                self._reconnect_count += 1
                logger.info(f"Reconnecting in {self._current_reconnect_delay}s (attempt {self._reconnect_count})")
                await asyncio.sleep(self._current_reconnect_delay)
                
                # Increase delay for next attempt
                self._current_reconnect_delay = min(
                    self._current_reconnect_delay * 2,
                    self._max_reconnect_delay
                )

    def _build_stream_url(self) -> str:
        """Build combined stream URL from subscriptions"""
        if not self._subscriptions:
            # No subscriptions, connect without streams
            return self.ws_url
        
        # Combined stream format: /stream?streams=stream1/stream2/stream3
        streams = "/".join(self._subscriptions)
        return f"{self.ws_url}/stream?streams={streams}"

    async def _process_messages(self):
        """Process incoming WebSocket messages"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("WebSocket connection closed")
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Message processing error: {e}")
        finally:
            self.is_connected = False

    async def _handle_message(self, data: str):
        """Parse and route incoming message"""
        try:
            msg = json.loads(data)
            self._message_count += 1
            self._last_message_time = int(time.time() * 1000)
            
            # Combined stream format: {"stream":"name","data":{...}}
            # Raw stream format: direct data object
            if "stream" in msg:
                stream_name = msg["stream"]
                payload = msg.get("data", {})
            else:
                # Raw stream - determine type from payload
                payload = msg
                stream_name = self._infer_stream_type(payload)
            
            # Route to appropriate handler
            if "@kline" in stream_name:
                await self._handle_kline(payload)
            elif "@markPrice" in stream_name:
                await self._handle_mark_price(payload)
            elif "@aggTrade" in stream_name:
                await self._handle_agg_trade(payload)
            elif "@ticker" in stream_name:
                await self._handle_ticker(payload)
            elif "@depth" in stream_name or "@bookTicker" in stream_name:
                await self._handle_depth(payload)
            else:
                logger.debug(f"Unknown stream: {stream_name}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")

    def _infer_stream_type(self, payload: dict) -> str:
        """Infer stream type from payload structure"""
        if "k" in payload:
            return "kline"
        elif "markPrice" in payload:
            return "markPrice"
        elif "a" in payload and "p" in payload:
            return "aggTrade"
        elif "c" in payload:
            return "ticker"
        elif "bids" in payload or "b" in payload:
            return "depth"
        return "unknown"

    async def _handle_kline(self, payload: dict):
        """Handle kline/candlestick update"""
        kline = payload.get("k", {})
        symbol = payload.get("s", "UNKNOWN")
        interval = kline.get("i", "15m")
        
        # Convert to standard format
        kline_data = {
            "symbol": symbol,
            "interval": interval,
            "timestamp": kline.get("t", 0),
            "open": float(kline.get("o", 0)),
            "high": float(kline.get("h", 0)),
            "low": float(kline.get("l", 0)),
            "close": float(kline.get("c", 0)),
            "volume": float(kline.get("v", 0)),
            "is_closed": kline.get("x", False),
        }
        
        # Cache kline
        key = f"{symbol}_{interval}"
        klines = self._kline_data[key]
        
        # Update or append
        if klines and klines[-1]["timestamp"] == kline_data["timestamp"]:
            klines[-1] = kline_data
        else:
            klines.append(kline_data)
            # Keep last 500 candles
            if len(klines) > 500:
                klines = klines[-500:]
                self._kline_data[key] = klines
        
        # Trigger callbacks
        await self._trigger_callbacks("kline", kline_data)
        
        logger.debug(f"Kline update: {symbol} {interval} @ {kline_data['close']}")

    async def _handle_mark_price(self, payload: dict):
        """Handle mark price update"""
        symbol = payload.get("s", "UNKNOWN")
        
        mark_price = {
            "symbol": symbol,
            "mark_price": float(payload.get("p", 0)),
            "index_price": float(payload.get("i", 0)),
            "estimated_settle_price": float(payload.get("P", 0)),
            "funding_rate": float(payload.get("r", 0)),
            "next_funding_time": payload.get("T", 0),
        }
        
        self._mark_price_data[symbol] = mark_price
        await self._trigger_callbacks("mark_price", mark_price)
        
        logger.debug(f"Mark price: {symbol} @ {mark_price['mark_price']}")

    async def _handle_agg_trade(self, payload: dict):
        """Handle aggregate trade update"""
        symbol = payload.get("s", "UNKNOWN")
        
        trade = {
            "event_type": payload.get("e"),
            "event_time": payload.get("E", 0),
            "symbol": symbol,
            "agg_trade_id": payload.get("a", 0),
            "price": float(payload.get("p", 0)),
            "quantity": float(payload.get("q", 0)),
            "first_trade_id": payload.get("f", 0),
            "last_trade_id": payload.get("l", 0),
            "timestamp": payload.get("T", 0),
            "is_buyer_maker": payload.get("m", False),
        }
        
        # Cache trade
        key = f"{symbol}_trades"
        trades = self._trade_data[key]
        trades.append(trade)
        if len(trades) > 100:
            trades = trades[-100:]
        self._trade_data[key] = trades
        
        await self._trigger_callbacks("agg_trade", trade)
        logger.debug(f"Trade: {symbol} {trade['quantity']} @ {trade['price']}")

    async def _handle_ticker(self, payload: dict):
        """Handle 24hr ticker update"""
        symbol = payload.get("s", "UNKNOWN")
        
        ticker = {
            "symbol": symbol,
            "price_change": float(payload.get("p", 0)),
            "price_change_percent": float(payload.get("P", 0)),
            "weighted_avg_price": float(payload.get("w", 0)),
            "last_price": float(payload.get("c", 0)),
            "last_qty": float(payload.get("Q", 0)),
            "open_price": float(payload.get("o", 0)),
            "high_price": float(payload.get("h", 0)),
            "low_price": float(payload.get("l", 0)),
            "volume": float(payload.get("v", 0)),
            "quote_volume": float(payload.get("q", 0)),
            "open_time": payload.get("O", 0),
            "close_time": payload.get("C", 0),
            "first_trade_id": payload.get("F", 0),
            "last_trade_id": payload.get("L", 0),
            "trade_count": payload.get("n", 0),
        }
        
        self._ticker_data[symbol] = ticker
        await self._trigger_callbacks("ticker", ticker)
        logger.debug(f"Ticker: {symbol} {ticker['last_price']} ({ticker['price_change_percent']}%)")

    async def _handle_depth(self, payload: dict):
        """Handle order book depth update"""
        symbol = payload.get("s", "UNKNOWN")
        
        # Handle both @depth and @bookTicker formats
        if "bids" in payload:
            depth = {
                "symbol": symbol,
                "bids": [[float(b[0]), float(b[1])] for b in payload.get("bids", [])],
                "asks": [[float(a[0]), float(a[1])] for a in payload.get("asks", [])],
                "timestamp": payload.get("lastUpdateId", 0),
            }
        else:
            # @bookTicker format
            depth = {
                "symbol": symbol,
                "bid_price": float(payload.get("b", 0)),
                "bid_qty": float(payload.get("B", 0)),
                "ask_price": float(payload.get("a", 0)),
                "ask_qty": float(payload.get("A", 0)),
            }
        
        self._depth_data[symbol] = depth
        await self._trigger_callbacks("depth", depth)
        logger.debug(f"Depth update: {symbol}")

    async def _trigger_callbacks(self, event_type: str, data: dict):
        """Trigger registered callbacks for event type"""
        for callback in self._callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event_type}: {e}")

    def subscribe(self, stream_type: str, symbol: str, **kwargs) -> str:
        """
        Subscribe to a stream
        
        Args:
            stream_type: Type of stream (kline, markPrice, aggTrade, ticker, depth)
            symbol: Trading pair (e.g., "BTCUSDT")
            **kwargs: Additional params (e.g., interval for kline)
            
        Returns:
            Stream name
        """
        # Binance requires lowercase symbols
        symbol_lower = symbol.lower()
        
        if stream_type == STREAM_KLINE:
            interval = kwargs.get("interval", "15m")
            stream = f"{symbol_lower}@kline_{interval}"
        elif stream_type == STREAM_MARK_PRICE:
            stream = f"{symbol_lower}@markPrice@1s"  # 1-second updates
        elif stream_type == STREAM_AGG_TRADE:
            stream = f"{symbol_lower}@aggTrade"
        elif stream_type == STREAM_TICKER:
            stream = f"{symbol_lower}@ticker"
        elif stream_type == STREAM_DEPTH:
            level = kwargs.get("level", 20)
            stream = f"{symbol_lower}@depth{level}@100ms"
        elif stream_type == STREAM_BOOK_TICKER:
            stream = f"{symbol_lower}@bookTicker"
        else:
            raise ValueError(f"Unknown stream type: {stream_type}")
        
        if stream not in self._subscriptions:
            self._subscriptions.append(stream)
            logger.info(f"Subscribed to {stream}")
            
            # Reconnect to apply subscription
            if self.is_connected:
                asyncio.create_task(self._reconnect_with_new_subscription())
        
        return stream

    async def _reconnect_with_new_subscription(self):
        """Reconnect to apply new subscription"""
        self._running = False
        if self.ws:
            await self.ws.close()
        await asyncio.sleep(1)
        self._running = True
        asyncio.create_task(self._connect())

    def unsubscribe(self, stream_type: str, symbol: str, **kwargs):
        """Unsubscribe from a stream"""
        symbol_lower = symbol.lower()
        
        if stream_type == STREAM_KLINE:
            interval = kwargs.get("interval", "15m")
            stream = f"{symbol_lower}@kline_{interval}"
        elif stream_type == STREAM_MARK_PRICE:
            stream = f"{symbol_lower}@markPrice@1s"
        elif stream_type == STREAM_AGG_TRADE:
            stream = f"{symbol_lower}@aggTrade"
        elif stream_type == STREAM_TICKER:
            stream = f"{symbol_lower}@ticker"
        elif stream_type == STREAM_DEPTH:
            level = kwargs.get("level", 20)
            stream = f"{symbol_lower}@depth{level}@100ms"
        else:
            return
        
        if stream in self._subscriptions:
            self._subscriptions.remove(stream)
            logger.info(f"Unsubscribed from {stream}")

    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for event type"""
        self._callbacks[event_type].append(callback)
        logger.debug(f"Registered callback for {event_type}")

    def unregister_callback(self, event_type: str, callback: Callable):
        """Unregister callback"""
        if callback in self._callbacks.get(event_type, []):
            self._callbacks[event_type].remove(callback)

    # Data access methods
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[dict]:
        """Get cached klines for symbol/interval"""
        key = f"{symbol.upper()}_{interval}"
        klines = self._kline_data.get(key, [])
        return klines[-limit:] if len(klines) > limit else klines

    def get_mark_price(self, symbol: str) -> Optional[dict]:
        """Get latest mark price for symbol"""
        return self._mark_price_data.get(symbol)

    def get_ticker(self, symbol: str) -> Optional[dict]:
        """Get latest 24hr ticker for symbol"""
        return self._ticker_data.get(symbol)

    def get_trades(self, symbol: str, limit: int = 50) -> List[dict]:
        """Get recent trades for symbol"""
        key = f"{symbol}_trades"
        trades = self._trade_data.get(key, [])
        return trades[-limit:] if len(trades) > limit else trades

    def get_depth(self, symbol: str) -> Optional[dict]:
        """Get latest order book depth for symbol"""
        return self._depth_data.get(symbol)

    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "connected": self.is_connected,
            "subscriptions": len(self._subscriptions),
            "message_count": self._message_count,
            "reconnect_count": self._reconnect_count,
            "last_message_time": self._last_message_time,
        }

    def get_latest_ticker(self, symbol: str) -> Optional[dict]:
        """Get latest ticker for symbol"""
        return self._ticker_data.get(symbol)

    def get_latest_kline(self, symbol: str, interval: str) -> Optional[dict]:
        """Get latest kline for symbol/interval"""
        key = f"{symbol}_{interval}"
        klines = self._kline_data.get(key, [])
        return klines[-1] if klines else None

    async def stop(self):
        """Stop WebSocket connection"""
        logger.info("Stopping WebSocket client...")
        self._running = False
        self.is_connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self.ws and not self.ws.closed:
            await self.ws.close()
        
        if self.session and not self.session.closed:
            await self.session.close()
        
        logger.info("WebSocket client stopped")

    def set_testnet(self, testnet: bool):
        """Switch between testnet and mainnet"""
        self.testnet = testnet
        self.ws_url = BINANCE_TESTNET_WS_URL if testnet else BINANCE_WS_URL
        logger.info(f"WebSocket switched to {'testnet' if testnet else 'mainnet'}")


# Singleton instance
binance_ws_client = BinanceWebSocketClient(testnet=False)
