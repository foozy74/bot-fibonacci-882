# backend/services/binance_client.py
"""
Binance Futures Market Data API Client
Public endpoints - no authentication required
Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api
"""
import aiohttp
from typing import List, Optional, Dict, Any
import logging
import time
from datetime import datetime
import asyncio
import asyncio

logger = logging.getLogger(__name__)


BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_TESTNET_URL = "https://demo-fapi.binance.com"
BINANCE_TESTNET_URL = "https://demo-fapi.binance.com"


# Map Bitunix intervals to Binance intervals
INTERVAL_MAP = {
    "15m": "15m",
    "30m": "30m",
    "60m": "1h",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


class BinanceClient:
    """
    Client for Binance Futures public Market Data API
    - No authentication required for public endpoints
    - Supports Testnet for development
    - Includes caching for rate limit optimization
    """

    def __init__(self, testnet: bool = False):
        self.base_url = BINANCE_TESTNET_URL if testnet else BINANCE_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.testnet = testnet
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_reset = 0
        
        # Simple in-memory cache
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self._cache_ttl = 5  # 5 seconds cache TTL
        self.testnet = testnet
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_reset = 0
        
        # Simple in-memory cache
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self._cache_ttl = 5  # 5 seconds cache TTL

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None,
        use_cache: bool = False
    ) -> Optional[Any]:
        """
        Make HTTP request with rate limiting and caching
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/fapi/v1/klines")
            params: Query parameters
            use_cache: Whether to use response caching
            
        Returns:
            Response data or None on error
        """
        # Check cache first
        if use_cache:
            cache_key = f"{method}:{path}:{params}"
            if cache_key in self._cache:
                data, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return data
        
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        
        # Rate limiting: max 1200 requests per minute
        now = time.time()
        if now - self._last_request_time < 0.05:  # 20 requests per second max
            await asyncio.sleep(0.05)
        
        self._last_request_time = now
        self._request_count += 1
        
        try:
            async with session.request(method, url, params=params) as resp:
                # Handle rate limit
                if resp.status == 429:
                    retry_after = int(resp.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._request(method, path, params, use_cache)
                
                # Handle server overload
                if resp.status == 503:
                    logger.warning(f"Service unavailable, retrying...")
                    await asyncio.sleep(1)
                    return await self._request(method, path, params, use_cache)
                
                if resp.status != 200:
                    error_data = await resp.json()
                    logger.error(f"Binance API error {resp.status}: {error_data}")
                    return None
                
                data = await resp.json()
                
                # Cache successful response
                if use_cache:
                    self._cache[cache_key] = (data, time.time())
                    # Clean old cache entries
                    self._cleanup_cache()
                
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Binance request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def _cleanup_cache(self):
        """Remove expired cache entries"""
        now = time.time()
        expired = [k for k, (_, t) in self._cache.items() if now - t > self._cache_ttl]
        for k in expired:
            del self._cache[k]

    async def _get_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Helper method for simple GET requests"""
        return await self._request("GET", url, params)

    async def _request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None,
        use_cache: bool = False
    ) -> Optional[Any]:
        """
        Make HTTP request with rate limiting and caching
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/fapi/v1/klines")
            params: Query parameters
            use_cache: Whether to use response caching
            
        Returns:
            Response data or None on error
        """
        # Check cache first
        if use_cache:
            cache_key = f"{method}:{path}:{params}"
            if cache_key in self._cache:
                data, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return data
        
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        
        # Rate limiting: max 1200 requests per minute
        now = time.time()
        if now - self._last_request_time < 0.05:  # 20 requests per second max
            await asyncio.sleep(0.05)
        
        self._last_request_time = now
        self._request_count += 1
        
        try:
            async with session.request(method, url, params=params) as resp:
                # Handle rate limit
                if resp.status == 429:
                    retry_after = int(resp.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._request(method, path, params, use_cache)
                
                # Handle server overload
                if resp.status == 503:
                    logger.warning(f"Service unavailable, retrying...")
                    await asyncio.sleep(1)
                    return await self._request(method, path, params, use_cache)
                
                if resp.status != 200:
                    error_data = await resp.json()
                    logger.error(f"Binance API error {resp.status}: {error_data}")
                    return None
                
                data = await resp.json()
                
                # Cache successful response
                if use_cache:
                    self._cache[cache_key] = (data, time.time())
                    # Clean old cache entries
                    self._cleanup_cache()
                
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Binance request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def _cleanup_cache(self):
        """Remove expired cache entries"""
        now = time.time()
        expired = [k for k, (_, t) in self._cache.items() if now - t > self._cache_ttl]
        for k in expired:
            del self._cache[k]

    async def _get_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Helper method for simple GET requests"""
        return await self._request("GET", url, params)

    async def get_klines(
        self,
        symbol: str,
        interval: str = "15m",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[dict]:
        """
        Get historical kline/candlestick data from Binance
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval (e.g., "15m", "1h", "1d")
            start_time: Start timestamp in milliseconds (optional)
            end_time: End timestamp in milliseconds (optional)
            limit: Number of candles to return (max 1500, default 500)
        
        Returns:
            List of kline dicts with format:
            {
                "timestamp": 1234567890,
                "open": 50000.0,
                "high": 50500.0,
                "low": 49500.0,
                "close": 50200.0,
                "volume": 1234.56
            }
        """
        session = await self._get_session()
        
        # Map interval to Binance format
        binance_interval = INTERVAL_MAP.get(interval, "15m")
        
        params = {
            "symbol": symbol,
            "interval": binance_interval,
            "limit": min(limit, 1500)  # Binance max is 1500
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        url = f"{self.base_url}/fapi/v1/klines"
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Binance API error: {resp.status}")
                    return []
                
                data = await resp.json()
                
                # Convert Binance format to standard format
                klines = []
                for candle in data:
                    # Binance kline format:
                    # [0] Open time
                    # [1] Open
                    # [2] High
                    # [3] Low
                    # [4] Close
                    # [5] Volume
                    # [6] Close time
                    # [7] Quote asset volume
                    # [8] Number of trades
                    # [9] Taker buy base asset volume
                    # [10] Taker buy quote asset volume
                    
                    klines.append({
                        "timestamp": int(candle[0]),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "close_time": int(candle[6]),
                    })
                
                logger.info(f"Retrieved {len(klines)} candles from Binance for {symbol}")
                return klines
                
        except Exception as e:
            logger.error(f"Binance request error: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[dict]:
        """
        Get 24h ticker price change statistics
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
        
        Returns:
            Ticker dict or None
        """
        session = await self._get_session()
        
        params = {"symbol": symbol}
        url = f"{self.base_url}/fapi/v1/ticker/24hr"
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return None
                
                data = await resp.json()
                
                return {
                    "symbol": data.get("symbol"),
                    "last": float(data.get("lastPrice", 0)),
                    "price_change": float(data.get("priceChange", 0)),
                    "price_change_percent": float(data.get("priceChangePercent", 0)),
                    "high_24h": float(data.get("highPrice", 0)),
                    "low_24h": float(data.get("lowPrice", 0)),
                    "volume_24h": float(data.get("volume", 0)),
                }
        except Exception as e:
            logger.error(f"Binance ticker error: {e}")
            return None

    async def get_symbols(self) -> List[str]:
        """
        Get list of available trading symbols
        
        Returns:
            List of symbol strings
        """
        data = await self._request("GET", "/fapi/v1/exchangeInfo", use_cache=True)
        
        if not data:
            return []
        
        symbols = []
        for s in data.get("symbols", []):
            if s.get("status") == "TRADING":
                symbols.append(s.get("symbol"))
        
        return symbols

    async def get_server_time(self) -> int:
        """
        GET /fapi/v1/time - Get Binance server time
        
        Returns:
            Server time in milliseconds
        """
        data = await self._request("GET", "/fapi/v1/time")
        if data and "serverTime" in data:
            return int(data["serverTime"])
        return int(time.time() * 1000)

    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict:
        """
        GET /fapi/v1/exchangeInfo - Get trading rules and symbol info
        
        Args:
            symbol: Optional symbol to filter (e.g., "BTCUSDT")
            
        Returns:
            Exchange info dict with symbols, filters, rate limits
        """
        params = {"symbol": symbol} if symbol else {}
        data = await self._request("GET", "/fapi/v1/exchangeInfo", params, use_cache=True)
        return data or {}

    async def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get specific symbol information
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            
        Returns:
            Symbol info dict or None
        """
        info = await self.get_exchange_info(symbol)
        if info and "symbols" in info:
            for s in info["symbols"]:
                if s.get("symbol") == symbol:
                    return s
        return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """
        GET /fapi/v1/depth - Order Book Depth
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            limit: Depth levels (5, 10, 20, 50, 100, 500, 1000)
            
        Returns:
            Order book dict with bids and asks
        """
        params = {"symbol": symbol, "limit": limit}
        data = await self._request("GET", "/fapi/v1/depth", params)
        
        if data:
            return {
                "symbol": symbol,
                "bids": [[float(b[0]), float(b[1])] for b in data.get("bids", [])],
                "asks": [[float(a[0]), float(a[1])] for a in data.get("asks", [])],
                "timestamp": data.get("lastUpdateId"),
            }
        return {}

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """
        GET /fapi/v1/trades - Recent Trades List
        
        Args:
            symbol: Trading pair
            limit: Number of trades (max 1000)
            
        Returns:
            List of recent trades
        """
        params = {"symbol": symbol, "limit": min(limit, 1000)}
        data = await self._request("GET", "/fapi/v1/trades", params)
        
        if not data:
            return []
        
        return [
            {
                "id": t.get("id"),
                "price": float(t.get("price", 0)),
                "qty": float(t.get("qty", 0)),
                "quote_qty": float(t.get("quoteQty", 0)),
                "time": t.get("time"),
                "is_buyer_maker": t.get("isBuyerMaker"),
            }
            for t in data
        ]

    async def get_historical_trades(self, symbol: str, from_id: int = 0, limit: int = 100) -> List[Dict]:
        """
        GET /fapi/v1/historicalTrades - Old Trades Lookup
        
        Args:
            symbol: Trading pair
            from_id: Trade ID to start from (default: most recent)
            limit: Number of trades (max 1000)
            
        Returns:
            List of historical trades
        """
        params = {"symbol": symbol, "limit": min(limit, 1000)}
        if from_id > 0:
            params["fromId"] = from_id
        
        data = await self._request("GET", "/fapi/v1/historicalTrades", params)
        
        if not data:
            return []
        
        return [
            {
                "id": t.get("id"),
                "price": float(t.get("price", 0)),
                "qty": float(t.get("qty", 0)),
                "quote_qty": float(t.get("quoteQty", 0)),
                "time": t.get("time"),
                "is_buyer_maker": t.get("isBuyerMaker"),
            }
            for t in data
        ]

    async def get_agg_trades(
        self, 
        symbol: str, 
        from_id: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        GET /fapi/v1/aggTrades - Compressed/Aggregate Trades List
        
        Args:
            symbol: Trading pair
            from_id: ID to get aggregate trades from
            start_time: Timestamp in ms
            end_time: Timestamp in ms
            limit: Number of trades (max 1000)
            
        Returns:
            List of aggregate trades
        """
        params = {"symbol": symbol, "limit": min(limit, 1000)}
        
        if from_id:
            params["fromId"] = from_id
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        data = await self._request("GET", "/fapi/v1/aggTrades", params)
        
        if not data:
            return []
        
        return [
            {
                "agg_id": t.get("a"),
                "price": float(t.get("p", 0)),
                "qty": float(t.get("q", 0)),
                "first_id": t.get("f"),
                "last_id": t.get("l"),
                "timestamp": t.get("T"),
                "is_buyer_maker": t.get("m"),
            }
            for t in data
        ]

    async def get_mark_price(self, symbol: Optional[str] = None) -> Any:
        """
        GET /fapi/v1/premiumIndex - Mark Price and Funding Rate
        
        Args:
            symbol: Trading pair (optional, all symbols if not provided)
            
        Returns:
            Mark price dict or list of dicts
        """
        params = {"symbol": symbol} if symbol else {}
        data = await self._request("GET", "/fapi/v1/premiumIndex", params)
        
        if not data:
            return None
        
        if symbol:
            return {
                "symbol": symbol,
                "mark_price": float(data.get("markPrice", 0)),
                "index_price": float(data.get("indexPrice", 0)),
                "estimated_settle_price": float(data.get("estimatedSettlePrice", 0)),
                "last_funding_rate": float(data.get("lastFundingRate", 0)),
                "next_funding_time": data.get("nextFundingTime"),
                "interest_rate": float(data.get("interestRate", 0)),
            }
        
        return [
            {
                "symbol": d.get("symbol"),
                "mark_price": float(d.get("markPrice", 0)),
                "index_price": float(d.get("indexPrice", 0)),
                "last_funding_rate": float(d.get("lastFundingRate", 0)),
                "next_funding_time": d.get("nextFundingTime"),
            }
            for d in data
        ]

    async def get_funding_rate(self, symbol: str, start_time: int = 0, end_time: int = 0, limit: int = 100) -> List[Dict]:
        """
        GET /fapi/v1/fundingRate - Funding Rate History
        
        Args:
            symbol: Trading pair
            start_time: Timestamp in ms
            end_time: Timestamp in ms
            limit: Number of results (max 1000)
            
        Returns:
            List of funding rate records
        """
        params = {
            "symbol": symbol,
            "limit": min(limit, 1000)
        }
        
        if start_time > 0:
            params["startTime"] = start_time
        if end_time > 0:
            params["endTime"] = end_time
        
        data = await self._request("GET", "/fapi/v1/fundingRate", params)
        
        if not data:
            return []
        
        return [
            {
                "symbol": d.get("symbol"),
                "funding_rate": float(d.get("fundingRate", 0)),
                "funding_time": d.get("fundingTime"),
                "mark_price": float(d.get("markPrice", 0)),
            }
            for d in data
        ]

    async def get_open_interest(self, symbol: str) -> Dict:
        """
        GET /fapi/v1/openInterest - Current Open Interest
        
        Args:
            symbol: Trading pair
            
        Returns:
            Open interest dict
        """
        params = {"symbol": symbol}
        data = await self._request("GET", "/fapi/v1/openInterest", params)
        
        if data:
            return {
                "symbol": symbol,
                "open_interest": float(data.get("openInterest", 0)),
                "timestamp": data.get("updateTime"),
            }
        return {}

    async def get_open_interest_statistics(self, symbol: str, period: str = "5m", limit: int = 50) -> List[Dict]:
        """
        GET /futures/openInterestHist - Open Interest Statistics
        
        Args:
            symbol: Trading pair
            period: Period (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d)
            limit: Number of results (max 500)
            
        Returns:
            List of OI statistics
        """
        params = {
            "symbol": symbol,
            "period": period,
            "limit": min(limit, 500)
        }
        
        data = await self._request("GET", "/futures/openInterestHist", params)
        
        if not data:
            return []
        
        return [
            {
                "symbol": d.get("symbol"),
                "open_interest": float(d.get("openInterest", 0)),
                "timestamp": d.get("updateTime"),
            }
            for d in data
        ]

    async def get_top_long_short_ratio(self, symbol: str, period: str = "5m", limit: int = 50) -> Dict:
        """
        GET /futures/data/topLongShortPositionRatio - Top Trader Long/Short Ratio
        
        Args:
            symbol: Trading pair
            period: Period (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d)
            limit: Number of results (max 500)
            
        Returns:
            Latest long/short ratio
        """
        params = {
            "symbol": symbol,
            "period": period,
            "limit": min(limit, 500)
        }
        
        data = await self._request("GET", "/futures/data/topLongShortPositionRatio", params)
        
        if not data:
            return {}
        
        latest = data[0] if data else {}
        return {
            "symbol": symbol,
            "long_short_ratio": float(latest.get("longShortRatio", 0)),
            "long_account": float(latest.get("longAccount", 0)),
            "short_account": float(latest.get("shortAccount", 0)),
            "timestamp": latest.get("updateTime"),
        }

    async def get_taker_buy_sell_volume(self, symbol: str, period: str = "5m", limit: int = 50) -> Dict:
        """
        Get taker buy/sell volume ratio via fallback to long/short ratio
        
        Note: Direct taker volume endpoint not consistently available.
        This method uses top trader long/short ratio as a proxy.
        
        Args:
            symbol: Trading pair
            period: Period (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d)
            limit: Number of results (max 500)
            
        Returns:
            Latest ratio data (uses long/short ratio as proxy)
        """
        # Fallback: use long/short ratio as sentiment indicator
        ratio_data = await self.get_top_long_short_ratio(symbol, period, limit)
        
        if ratio_data:
            # Convert long/short ratio to buy/sell format
            long_account = ratio_data.get("long_account", 0.5)
            short_account = ratio_data.get("short_account", 0.5)
            
            return {
                "symbol": symbol,
                "buy_sell_ratio": ratio_data.get("long_short_ratio", 1.0),
                "buy_vol": long_account,
                "sell_vol": short_account,
                "timestamp": ratio_data.get("timestamp"),
            }
        
        return {}
        
        return {}

    async def get_continuous_contract_klines(
        self,
        pair: str,
        contract_type: str = "PERPETUAL",
        interval: str = "15m",
        limit: int = 500
    ) -> List[Dict]:
        """
        GET /fapi/v1/premiumIndexKlines - Continuous Contract Kline Data
        
        Args:
            pair: Trading pair (e.g., "BTCUSDT")
            contract_type: PERPETUAL, CURRENT_MONTH, NEXT_MONTH, CURRENT_QUARTER, etc.
            interval: Kline interval
            limit: Number of candles (max 1500)
            
        Returns:
            List of continuous contract klines
        """
        binance_interval = INTERVAL_MAP.get(interval, "15m")
        
        params = {
            "pair": pair,
            "contractType": contract_type,
            "interval": binance_interval,
            "limit": min(limit, 1500)
        }
        
        data = await self._request("GET", "/fapi/v1/premiumIndexKlines", params)
        
        if not data:
            return []
        
        return [
            {
                "timestamp": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            }
            for candle in data
        ]

    async def get_index_price_klines(
        self,
        pair: str,
        interval: str = "15m",
        limit: int = 500
    ) -> List[Dict]:
        """
        GET /fapi/v1/indexPriceKlines - Index Price Kline Data
        
        Args:
            pair: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval
            limit: Number of candles (max 1500)
            
        Returns:
            List of index price klines
        """
        binance_interval = INTERVAL_MAP.get(interval, "15m")
        
        params = {
            "pair": pair,
            "interval": binance_interval,
            "limit": min(limit, 1500)
        }
        
        data = await self._request("GET", "/fapi/v1/indexPriceKlines", params)
        
        if not data:
            return []
        
        return [
            {
                "timestamp": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
            }
            for candle in data
        ]

    async def get_mark_price_klines(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 500
    ) -> List[Dict]:
        """
        GET /fapi/v1/markPriceKlines - Mark Price Kline Data
        
        Args:
            symbol: Trading pair
            interval: Kline interval
            limit: Number of candles (max 1500)
            
        Returns:
            List of mark price klines
        """
        binance_interval = INTERVAL_MAP.get(interval, "15m")
        
        params = {
            "symbol": symbol,
            "interval": binance_interval,
            "limit": min(limit, 1500)
        }
        
        data = await self._request("GET", "/fapi/v1/markPriceKlines", params)
        
        if not data:
            return []
        
        return [
            {
                "timestamp": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
            }
            for candle in data
        ]

    async def get_oi_statistics_by_symbol(self, symbol: str, period: str = "5m", limit: int = 50) -> List[Dict]:
        """
        Alternative method for open interest statistics
        """
        return await self.get_open_interest_statistics(symbol, period, limit)

    def clear_cache(self):
        """Clear the response cache"""
        self._cache.clear()
        logger.info("Binance client cache cleared")

    async def close(self):
        """Close the session and clear cache"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.clear_cache()
        logger.info("Binance client closed")

    def set_testnet(self, testnet: bool):
        """Switch between testnet and mainnet"""
        self.testnet = testnet
        self.base_url = BINANCE_TESTNET_URL if testnet else BINANCE_BASE_URL
        logger.info(f"Binance client switched to {'testnet' if testnet else 'mainnet'}")


# Singleton instance
binance_client = BinanceClient(testnet=False)
