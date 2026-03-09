# backend/services/binance_futures_client.py
"""
Binance Futures Trading Client
Official API: https://developers.binance.com/docs/derivatives/usds-margined-futures

Supports:
- Account & Balance queries
- Order placement (MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET)
- Position management
- Order cancellation and modification
- Leverage and Margin Mode settings
- Trade history
- Auto-retry with exponential backoff
- Rate limit handling
"""
import hashlib
import hmac
import logging
import time
import asyncio
from typing import Optional, Dict, List, Any
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)

BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"
BINANCE_FUTURES_TESTNET_URL = "https://testnet.binancefuture.com"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"  # For hedge mode disabled


class TimeInForce(str, Enum):
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    GTX = "GTX"  # Good Till Crossing (Post Only)


class BinanceAPIError(Exception):
    """Base exception for Binance API errors"""
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(f"Binance API Error {code}: {msg}")


class RateLimitError(BinanceAPIError):
    """429 - Rate limit exceeded"""
    def __init__(self, msg: str = "Rate limit exceeded"):
        super().__init__(-1003, msg)


class TimestampError(BinanceAPIError):
    """-1021 - Timestamp ahead of server time"""
    def __init__(self, msg: str = "Timestamp ahead of server time"):
        super().__init__(-1021, msg)


class SignatureError(BinanceAPIError):
    """-1022 - Signature error"""
    def __init__(self, msg: str = "Signature error"):
        super().__init__(-1022, msg)


class OrderError(BinanceAPIError):
    """Order-related errors (-2010 to -2021)"""
    pass


def generate_signature(secret: str, params: str) -> str:
    """Generate HMAC SHA256 signature"""
    return hmac.new(
        secret.encode('utf-8'),
        params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def get_timestamp() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)


class BinanceFuturesClient:
    """
    Binance Futures Trading Client
    
    Features:
    - SIGNED endpoints (TRADE, USER_DATA)
    - Auto-retry with exponential backoff
    - Rate limit handling
    - Time synchronization
    - Testnet support
    """

    def __init__(self, testnet: bool = False):
        self.testnet = testnet
        self.base_url = BINANCE_FUTURES_TESTNET_URL if testnet else BINANCE_FUTURES_BASE_URL
        self.api_key = ""
        self.api_secret = ""
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Time sync
        self.server_time_offset = 0
        self.last_time_sync = 0
        self.time_sync_interval = 3600000  # 1 hour
        
        # Rate limiting
        self.request_count = 0
        self.last_request_time = 0
        
        # Order ID counter for client order IDs
        self._order_id_counter = 0

    def set_credentials(self, api_key: str, api_secret: str):
        """Set API credentials"""
        self.api_key = api_key
        self.api_secret = api_secret
        logger.info("Binance Futures credentials set")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    def _get_timestamp(self) -> int:
        """Get synchronized timestamp"""
        now = get_timestamp()
        
        # Sync time if needed
        if now - self.last_time_sync > self.time_sync_interval:
            asyncio.create_task(self._sync_server_time())
        
        return now + self.server_time_offset

    async def _sync_server_time(self):
        """Synchronize with Binance server time"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/fapi/v1/time"
            
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    server_time = data.get("serverTime", get_timestamp())
                    local_time = get_timestamp()
                    self.server_time_offset = server_time - local_time
                    self.last_time_sync = local_time
                    logger.info(f"Time synced: offset={self.server_time_offset}ms")
        except Exception as e:
            logger.error(f"Time sync error: {e}")

    async def _request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None,
        signed: bool = False,
        retry_count: int = 3
    ) -> Optional[Dict]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, DELETE, PUT)
            path: API path (e.g., "/fapi/v1/order")
            params: Request parameters
            signed: Whether to sign the request
            retry_count: Number of retries for recoverable errors
            
        Returns:
            Response data or None on error
        """
        if not params:
            params = {}
            
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        
        # Prepare headers
        headers = {}
        if signed:
            if not self.api_key or not self.api_secret:
                logger.error("API credentials not set")
                return None
                
            # Add timestamp
            params['timestamp'] = self._get_timestamp()
            
            # Build query string for signature
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            
            # Generate signature
            signature = generate_signature(self.api_secret, query_string)
            params['signature'] = signature
            
            # Add API key header
            headers['X-MBX-APIKEY'] = self.api_key
        
        # Rate limiting
        await self._rate_limit()
        
        last_exception = None
        
        for attempt in range(retry_count + 1):
            try:
                async with session.request(method, url, params=params, headers=headers) as resp:
                    # Handle rate limit
                    if resp.status == 429:
                        retry_after = int(resp.headers.get('Retry-After', 5))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # Handle server overload
                    if resp.status == 503:
                        wait_time = (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Service unavailable (503), retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    data = await resp.json()
                    
                    # Check for Binance error codes
                    if 'code' in data:
                        code = data['code']
                        msg = data.get('msg', 'Unknown error')
                        
                        if code == 0 or code == 200:
                            return data
                        elif code == -1021:  # Timestamp error
                            logger.error(f"Timestamp error, re-syncing time")
                            await self._sync_server_time()
                            raise TimestampError(msg)
                        elif code == -1022:  # Signature error
                            raise SignatureError(msg)
                        elif code == -1003 or code == -1015:  # Rate limit
                            raise RateLimitError(msg)
                        elif -2010 <= code <= -2021:  # Order errors
                            raise OrderError(code, msg)
                        else:
                            logger.error(f"Binance API error {code}: {msg}")
                            return None
                    
                    return data
                    
            except asyncio.CancelledError:
                raise
            except (BinanceAPIError, aiohttp.ClientError) as e:
                last_exception = e
                if attempt < retry_count:
                    wait_time = (2 ** attempt)
                    logger.warning(f"Request error: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {retry_count} retries: {e}")
                    return None
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None
        
        return None

    async def _rate_limit(self):
        """Simple rate limiting - max 20 requests per second"""
        now = time.time()
        if now - self.last_request_time < 0.05:
            await asyncio.sleep(0.05 - (now - self.last_request_time))
        self.last_request_time = time.time()
        self.request_count += 1

    # ============= Account Endpoints =============
    
    async def get_account(self) -> Optional[Dict]:
        """
        GET /fapi/v3/account - Account Information v3 (USER_DATA)
        Latest API version with improved response format
        
        Returns:
            Account info with balances, positions, margins
        """
        return await self._request("GET", "/fapi/v3/account", signed=True)

    async def get_balance(self) -> Optional[List[Dict]]:
        """
        GET /fapi/v2/balance - Account Balance V2 (USER_DATA)
        
        Returns:
            List of asset balances with unrealized PnL
        """
        return await self._request("GET", "/fapi/v2/balance", signed=True)

    async def get_account_config(self) -> Optional[Dict]:
        """
        GET /fapi/v1/accountConfig - Account Configuration (USER_DATA)
        
        Returns:
            Account configuration including leverage, margin mode
        """
        return await self._request("GET", "/fapi/v1/accountConfig", signed=True)

    # ============= Position Endpoints =============
    
    async def get_positions(self, symbol: Optional[str] = None) -> Optional[List[Dict]]:
        """
        GET /fapi/v3/positionRisk - Current Position Risk V3 (USER_DATA)
        Latest API version with enhanced position data
        
        Args:
            symbol: Optional symbol to filter (e.g., "BTCUSDT")
            
        Returns:
            List of positions with unrealized PnL, entry price, leverage
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._request("GET", "/fapi/v3/positionRisk", params, signed=True)

    async def set_leverage(self, symbol: str, leverage: int) -> Optional[Dict]:
        """
        POST /fapi/v1/leverage - Change Initial Leverage (TRADE)
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            leverage: Leverage value (1-125)
            
        Returns:
            Updated leverage info
        """
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        return await self._request("POST", "/fapi/v1/leverage", params, signed=True)

    async def set_margin_mode(self, symbol: str, margin_mode: str) -> Optional[Dict]:
        """
        POST /fapi/v1/marginType - Change Margin Mode (TRADE)
        
        Args:
            symbol: Trading pair
            margin_mode: "ISOLATED" or "CROSSED"
            
        Returns:
            Success status
        """
        params = {
            'symbol': symbol,
            'marginType': margin_mode.upper()
        }
        return await self._request("POST", "/fapi/v1/marginType", params, signed=True)

    async def set_position_mode(self, dual_side: bool) -> Optional[Dict]:
        """
        POST /fapi/v1/positionSide - Change Position Mode (TRADE)
        
        Args:
            dual_side: True for hedge mode, False for one-way mode
            
        Returns:
            Success status
        """
        params = {
            'dualSidePosition': 'true' if dual_side else 'false'
        }
        return await self._request("POST", "/fapi/v1/positionSide", params, signed=True)

    # ============= Order Endpoints =============
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        position_side: str = "BOTH",
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        close_position: bool = False,
        working_type: str = "CONTRACT_PRICE",
        price_protect: bool = False
    ) -> Optional[Dict]:
        """
        POST /fapi/v1/order - Place Order (TRADE)
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP_MARKET, etc.
            quantity: Order quantity
            price: Limit price (for LIMIT orders)
            position_side: LONG, SHORT, or BOTH
            time_in_force: GTC, IOC, FOK, GTX
            reduce_only: Reduce position only
            stop_price: Stop price for stop orders
            client_order_id: Custom order ID
            
        Returns:
            Order response with order ID, status, etc.
        """
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
        }
        
        if quantity:
            params['quantity'] = str(quantity)
        
        if price and order_type.upper() == OrderType.LIMIT:
            params['price'] = str(price)
            params['timeInForce'] = time_in_force.upper()
        
        if position_side:
            params['positionSide'] = position_side.upper()
        
        if reduce_only:
            params['reduceOnly'] = 'true'
        
        if stop_price:
            params['stopPrice'] = str(stop_price)
        
        if client_order_id:
            params['newClientOrderId'] = client_order_id
        else:
            # Generate unique client order ID
            self._order_id_counter += 1
            params['newClientOrderId'] = f"fib882_{get_timestamp()}_{self._order_id_counter}"
        
        # Additional parameters for advanced orders
        if close_position:
            params['closePosition'] = 'true'
        if working_type:
            params['workingType'] = working_type
        if price_protect and stop_price:
            params['priceProtect'] = 'true'
        
        return await self._request("POST", "/fapi/v1/order", params, signed=True)

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        position_side: str = "BOTH",
        reduce_only: bool = False
    ) -> Optional[Dict]:
        """Place a MARKET order"""
        return await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            position_side=position_side,
            reduce_only=reduce_only
        )

    async def place_batch_orders(self, orders: List[Dict]) -> Optional[List[Dict]]:
        """
        POST /fapi/v1/batchOrders - Place Multiple Orders (TRADE)
        Place up to 5 orders simultaneously
        
        Args:
            orders: List of order dicts, each containing:
                - symbol: str
                - side: str (BUY/SELL)
                - type: str (MARKET/LIMIT/STOP_MARKET/etc)
                - quantity: float
                - price: float (optional, for LIMIT)
                - positionSide: str (optional)
                - timeInForce: str (optional, for LIMIT)
                - reduceOnly: bool (optional)
                - stopPrice: float (optional, for STOP orders)
                
        Returns:
            List of order results or error details
            
        Example:
            orders = [
                {
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "type": "LIMIT",
                    "quantity": "0.001",
                    "price": "50000",
                    "timeInForce": "GTC"
                },
                {
                    "symbol": "BTCUSDT",
                    "side": "SELL",
                    "type": "LIMIT",
                    "quantity": "0.001",
                    "price": "52000",
                    "timeInForce": "GTC"
                }
            ]
        """
        if not orders or len(orders) > 5:
            logger.error("Batch orders must be between 1 and 5 orders")
            return None
        
        # Build batch order parameters
        batch_list = []
        for i, order in enumerate(orders):
            order_params = {
                "symbol": order.get("symbol"),
                "side": order.get("side", "BUY").upper(),
                "type": order.get("type", "MARKET").upper(),
                "quantity": str(order.get("quantity", 0)),
            }
            
            # Add optional parameters
            if order.get("price"):
                order_params["price"] = str(order["price"])
            if order.get("timeInForce"):
                order_params["timeInForce"] = order["timeInForce"].upper()
            if order.get("positionSide"):
                order_params["positionSide"] = order["positionSide"].upper()
            if order.get("reduceOnly"):
                order_params["reduceOnly"] = "true"
            if order.get("stopPrice"):
                order_params["stopPrice"] = str(order["stopPrice"])
            
            # Generate client order ID
            order_params["newClientOrderId"] = order.get(
                "newClientOrderId", 
                f"batch_{get_timestamp()}_{i}"
            )
            
            batch_list.append(order_params)
        
        # Send as JSON list in request body
        params = {
            "batchOrders": batch_list
        }
        
        return await self._request("POST", "/fapi/v1/batchOrders", params, signed=True)

    async def place_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        stop_limit_price: Optional[float] = None,
        stop_limit_time_in_force: str = "GTC",
        position_side: str = "BOTH"
    ) -> Optional[Dict]:
        """
        Place OCO (One-Cancels-Other) order - LIMIT + STOP_MARKET combination
        When one order executes, the other is automatically cancelled
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Limit order price
            stop_price: Stop order trigger price
            stop_limit_price: Stop limit price (optional, defaults to stop_price)
            stop_limit_time_in_force: Time in force for stop limit
            position_side: LONG, SHORT, or BOTH
            
        Returns:
            OCO order response
        """
        # Place limit order
        limit_order = await self.place_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            position_side=position_side
        )
        
        if not limit_order:
            return None
        
        # Place stop order linked to same position
        stop_order = await self.place_stop_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            position_side=position_side,
            reduce_only=True
        )
        
        return {
            "limit_order": limit_order,
            "stop_order": stop_order,
            "oco_type": "MANUAL_LINKED"
        }

    async def place_batch_orders(self, orders: List[Dict]) -> Optional[List[Dict]]:
        """
        POST /fapi/v1/batchOrders - Place Multiple Orders (TRADE)
        Place up to 5 orders simultaneously
        
        Args:
            orders: List of order dicts, each containing:
                - symbol: str
                - side: str (BUY/SELL)
                - type: str (MARKET/LIMIT/STOP_MARKET/etc)
                - quantity: float
                - price: float (optional, for LIMIT)
                - positionSide: str (optional)
                - timeInForce: str (optional, for LIMIT)
                - reduceOnly: bool (optional)
                - stopPrice: float (optional, for STOP orders)
                
        Returns:
            List of order results or error details
            
        Example:
            orders = [
                {
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "type": "LIMIT",
                    "quantity": "0.001",
                    "price": "50000",
                    "timeInForce": "GTC"
                },
                {
                    "symbol": "BTCUSDT",
                    "side": "SELL",
                    "type": "LIMIT",
                    "quantity": "0.001",
                    "price": "52000",
                    "timeInForce": "GTC"
                }
            ]
        """
        if not orders or len(orders) > 5:
            logger.error("Batch orders must be between 1 and 5 orders")
            return None
        
        # Build batch order parameters
        batch_list = []
        for i, order in enumerate(orders):
            order_params = {
                "symbol": order.get("symbol"),
                "side": order.get("side", "BUY").upper(),
                "type": order.get("type", "MARKET").upper(),
                "quantity": str(order.get("quantity", 0)),
            }
            
            # Add optional parameters
            if order.get("price"):
                order_params["price"] = str(order["price"])
            if order.get("timeInForce"):
                order_params["timeInForce"] = order["timeInForce"].upper()
            if order.get("positionSide"):
                order_params["positionSide"] = order["positionSide"].upper()
            if order.get("reduceOnly"):
                order_params["reduceOnly"] = "true"
            if order.get("stopPrice"):
                order_params["stopPrice"] = str(order["stopPrice"])
            
            # Generate client order ID
            order_params["newClientOrderId"] = order.get(
                "newClientOrderId", 
                f"batch_{get_timestamp()}_{i}"
            )
            
            batch_list.append(order_params)
        
        # Send as JSON list in request body
        params = {
            "batchOrders": batch_list
        }
        
        return await self._request("POST", "/fapi/v1/batchOrders", params, signed=True)

    async def place_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        stop_limit_price: Optional[float] = None,
        stop_limit_time_in_force: str = "GTC",
        position_side: str = "BOTH"
    ) -> Optional[Dict]:
        """
        Place OCO (One-Cancels-Other) order - LIMIT + STOP_MARKET combination
        When one order executes, the other is automatically cancelled
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Limit order price
            stop_price: Stop order trigger price
            stop_limit_price: Stop limit price (optional, defaults to stop_price)
            stop_limit_time_in_force: Time in force for stop limit
            position_side: LONG, SHORT, or BOTH
            
        Returns:
            OCO order response
        """
        # Place limit order
        limit_order = await self.place_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            position_side=position_side
        )
        
        if not limit_order:
            return None
        
        # Place stop order linked to same position
        stop_order = await self.place_stop_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            position_side=position_side,
            reduce_only=True
        )
        
        return {
            "limit_order": limit_order,
            "stop_order": stop_order,
            "oco_type": "MANUAL_LINKED"
        }

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        position_side: str = "BOTH",
        time_in_force: str = "GTC",
        reduce_only: bool = False
    ) -> Optional[Dict]:
        """Place a LIMIT order"""
        return await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            position_side=position_side,
            time_in_force=time_in_force,
            reduce_only=reduce_only
        )

    async def place_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        position_side: str = "BOTH",
        reduce_only: bool = False
    ) -> Optional[Dict]:
        """Place a STOP_MARKET order"""
        return await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP_MARKET,
            quantity=quantity,
            stop_price=stop_price,
            position_side=position_side,
            reduce_only=reduce_only
        )

    async def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        position_side: str = "BOTH",
        reduce_only: bool = False
    ) -> Optional[Dict]:
        """Place a TAKE_PROFIT_MARKET order"""
        return await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.TAKE_PROFIT_MARKET,
            quantity=quantity,
            stop_price=stop_price,
            position_side=position_side,
            reduce_only=reduce_only
        )

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        DELETE /fapi/v1/order - Cancel Order (TRADE)
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
            client_order_id: Client order ID to cancel
            
        Returns:
            Cancelled order info
        """
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['origClientOrderId'] = client_order_id
        else:
            logger.error("Either order_id or client_order_id must be provided")
            return None
        
        return await self._request("DELETE", "/fapi/v1/order", params, signed=True)

    async def cancel_all_orders(self, symbol: str) -> Optional[Dict]:
        """
        DELETE /fapi/v1/allOpenOrders - Cancel All Open Orders (TRADE)
        
        Args:
            symbol: Trading pair
            
        Returns:
            Cancellation status
        """
        params = {'symbol': symbol}
        return await self._request("DELETE", "/fapi/v1/allOpenOrders", params, signed=True)

    async def modify_order(
        self,
        symbol: str,
        order_id: int,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        PUT /fapi/v1/order - Modify Order (TRADE)
        
        Args:
            symbol: Trading pair
            order_id: Order ID to modify
            quantity: New quantity
            price: New price
            client_order_id: New client order ID
            
        Returns:
            Modified order info
        """
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        if quantity:
            params['quantity'] = str(quantity)
        if price:
            params['price'] = str(price)
        if client_order_id:
            params['newClientOrderId'] = client_order_id
        
        return await self._request("PUT", "/fapi/v1/order", params, signed=True)

    async def get_open_orders(
        self,
        symbol: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/openOrders - Current Open Orders (USER_DATA)
        
        Args:
            symbol: Optional symbol to filter
            
        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._request("GET", "/fapi/v1/openOrders", params, signed=True)

    async def get_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        GET /fapi/v1/order - Query Order (USER_DATA)
        
        Args:
            symbol: Trading pair
            order_id: Order ID
            client_order_id: Client order ID
            
        Returns:
            Order details
        """
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['origClientOrderId'] = client_order_id
        else:
            logger.error("Either order_id or client_order_id must be provided")
            return None
        
        return await self._request("GET", "/fapi/v1/order", params, signed=True)

    async def get_order_history(
        self,
        symbol: str,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/allOrders - All Orders (USER_DATA)
        
        Args:
            symbol: Trading pair
            limit: Number of orders (max 1000)
            
        Returns:
            List of historical orders
        """
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000)
        }
        return await self._request("GET", "/fapi/v1/allOrders", params, signed=True)

    async def get_trades(
        self,
        symbol: str,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/userTrades - Account Trade List (USER_DATA)
        
        Args:
            symbol: Trading pair
            limit: Number of trades (max 1000)
            
        Returns:
            List of executed trades
        """
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000)
        }
        return await self._request("GET", "/fapi/v1/userTrades", params, signed=True)

    async def get_income_history(
        self,
        symbol: Optional[str] = None,
        income_type: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/income - Get Income History (USER_DATA)
        
        Args:
            symbol: Optional trading pair filter
            income_type: Type of income:
                - TRANSFER: Fund Transfer
                - WELCOME_BONUS: Welcome Bonus
                - REALIZED_PNL: Realized PnL
                - FUNDING_FEE: Funding Fee
                - COMMISSION: Trading Commission
                - INSURANCE_CLEAR: Insurance Clear
            start_time: Start timestamp in ms
            end_time: End timestamp in ms
            limit: Number of records (max 1000)
            
        Returns:
            List of income records
        """
        params = {
            'limit': min(limit, 1000)
        }
        
        if symbol:
            params['symbol'] = symbol
        if income_type:
            params['incomeType'] = income_type.upper()
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        income_data = await self._request("GET", "/fapi/v1/income", params, signed=True)
        
        if not income_data:
            return []
        
        return [
            {
                "symbol": item.get("symbol"),
                "income_type": item.get("incomeType"),
                "income": float(item.get("income", 0)),
                "asset": item.get("asset"),
                "info": item.get("info"),
                "time": item.get("time"),
                "trade_id": item.get("tradeId"),
            }
            for item in income_data
        ]

    async def get_force_orders(
        self,
        symbol: Optional[str] = None,
        auto_cancel_type: Optional[str] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/forceOrders - Get Force Orders (USER_DATA)
        Liquidation orders for the account
        
        Args:
            symbol: Optional trading pair filter
            auto_cancel_type: Auto cancel type (LEGACY_MARGIN_SHORT/LEGACY_MARGIN_LONG)
            limit: Number of records (max 100)
            
        Returns:
            List of force/liquidation orders
        """
        params = {
            'limit': min(limit, 100)
        }
        
        if symbol:
            params['symbol'] = symbol
        if auto_cancel_type:
            params['autoCancelType'] = auto_cancel_type
        
        return await self._request("GET", "/fapi/v1/forceOrders", params, signed=True)

    async def get_adl_quantile(self) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/adlQuantile - Get ADL Quantile (USER_DATA)
        Auto-Deleveraging quantile for positions
        
        Returns:
            List of ADL quantiles per symbol
        """
        return await self._request("GET", "/fapi/v1/adlQuantile", signed=True)

    async def get_commission_rate(self, symbol: str) -> Optional[Dict]:
        """
        GET /fapi/v1/commissionRate - Get User Commission Rate (USER_DATA)
        
        Args:
            symbol: Trading pair
            
        Returns:
            Commission rate info
        """
        params = {'symbol': symbol}
        return await self._request("GET", "/fapi/v1/commissionRate", params, signed=True)

    async def get_income_history(
        self,
        symbol: Optional[str] = None,
        income_type: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/income - Get Income History (USER_DATA)
        
        Args:
            symbol: Optional trading pair filter
            income_type: Type of income:
                - TRANSFER: Fund Transfer
                - WELCOME_BONUS: Welcome Bonus
                - REALIZED_PNL: Realized PnL
                - FUNDING_FEE: Funding Fee
                - COMMISSION: Trading Commission
                - INSURANCE_CLEAR: Insurance Clear
            start_time: Start timestamp in ms
            end_time: End timestamp in ms
            limit: Number of records (max 1000)
            
        Returns:
            List of income records
        """
        params = {
            'limit': min(limit, 1000)
        }
        
        if symbol:
            params['symbol'] = symbol
        if income_type:
            params['incomeType'] = income_type.upper()
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        income_data = await self._request("GET", "/fapi/v1/income", params, signed=True)
        
        if not income_data:
            return []
        
        return [
            {
                "symbol": item.get("symbol"),
                "income_type": item.get("incomeType"),
                "income": float(item.get("income", 0)),
                "asset": item.get("asset"),
                "info": item.get("info"),
                "time": item.get("time"),
                "trade_id": item.get("tradeId"),
            }
            for item in income_data
        ]

    async def get_force_orders(
        self,
        symbol: Optional[str] = None,
        auto_cancel_type: Optional[str] = None,
        limit: int = 100
    ) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/forceOrders - Get Force Orders (USER_DATA)
        Liquidation orders for the account
        
        Args:
            symbol: Optional trading pair filter
            auto_cancel_type: Auto cancel type (LEGACY_MARGIN_SHORT/LEGACY_MARGIN_LONG)
            limit: Number of records (max 100)
            
        Returns:
            List of force/liquidation orders
        """
        params = {
            'limit': min(limit, 100)
        }
        
        if symbol:
            params['symbol'] = symbol
        if auto_cancel_type:
            params['autoCancelType'] = auto_cancel_type
        
        return await self._request("GET", "/fapi/v1/forceOrders", params, signed=True)

    async def get_adl_quantile(self) -> Optional[List[Dict]]:
        """
        GET /fapi/v1/adlQuantile - Get ADL Quantile (USER_DATA)
        Auto-Deleveraging quantile for positions
        
        Returns:
            List of ADL quantiles per symbol
        """
        return await self._request("GET", "/fapi/v1/adlQuantile", signed=True)

    async def get_commission_rate(self, symbol: str) -> Optional[Dict]:
        """
        GET /fapi/v1/commissionRate - Get User Commission Rate (USER_DATA)
        
        Args:
            symbol: Trading pair
            
        Returns:
            Commission rate info
        """
        params = {'symbol': symbol}
        return await self._request("GET", "/fapi/v1/commissionRate", params, signed=True)

    # ============= Helper Methods =============
    
    async def get_account_balance_usdt(self) -> float:
        """Get USDT balance"""
        balances = await self.get_balance()
        if balances:
            for bal in balances:
                if bal.get('asset') == 'USDT':
                    return float(bal.get('availableBalance', 0))
        return 0.0

    async def get_unrealized_pnl(self) -> float:
        """Get total unrealized PnL from all positions"""
        positions = await self.get_positions()
        if positions:
            return sum(float(p.get('unRealizedProfit', 0)) for p in positions)
        return 0.0

    def set_testnet(self, testnet: bool):
        """Switch between testnet and mainnet"""
        self.testnet = testnet
        self.base_url = BINANCE_FUTURES_TESTNET_URL if testnet else BINANCE_FUTURES_BASE_URL
        logger.info(f"Binance Futures switched to {'testnet' if testnet else 'mainnet'}")

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("Binance Futures client closed")


# Singleton instance
binance_futures_client = BinanceFuturesClient(testnet=False)
