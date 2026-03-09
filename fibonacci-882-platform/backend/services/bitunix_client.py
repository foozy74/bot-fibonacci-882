# backend/services/bitunix_client.py
import hashlib
import time
import json
import uuid
import aiohttp
from config import settings


def get_nonce() -> str:
    """Generate a random string as nonce (32 characters)"""
    return str(uuid.uuid4()).replace('-', '')


def get_timestamp() -> str:
    """Get current timestamp in milliseconds"""
    return str(int(time.time() * 1000))


def generate_signature(
    api_key: str,
    secret_key: str,
    nonce: str,
    timestamp: str,
    query_params: str = "",
    body: str = ""
) -> str:
    """
    Generate signature according to Bitunix OpenAPI spec
    
    Args:
        api_key: API key
        secret_key: Secret key
        nonce: Random string
        timestamp: Timestamp in ms
        query_params: Sorted query string (no spaces)
        body: Raw JSON string (no spaces)
    
    Returns:
        str: SHA256 signature
    """
    digest_input = nonce + timestamp + api_key + query_params + body
    digest = hashlib.sha256(digest_input.encode('utf-8')).hexdigest()
    sign_input = digest + secret_key
    sign = hashlib.sha256(sign_input.encode('utf-8')).hexdigest()
    return sign


def get_auth_headers(
    api_key: str,
    secret_key: str,
    query_params: str = "",
    body: str = ""
) -> dict:
    """Get authentication headers"""
    nonce = get_nonce()
    timestamp = get_timestamp()
    
    sign = generate_signature(
        api_key=api_key,
        secret_key=secret_key,
        nonce=nonce,
        timestamp=timestamp,
        query_params=query_params,
        body=body
    )
    
    return {
        "api-key": api_key,
        "sign": sign,
        "nonce": nonce,
        "timestamp": timestamp,
        "Content-Type": "application/json",
        "language": "en-US",
    }


class BitunixClient:
    """Async HTTP client for Bitunix API (private endpoints only)"""

    BASE_URL = "https://fapi.bitunix.com"

    def __init__(self):
        self.api_key = settings.bitunix_api_key
        self.api_secret = settings.bitunix_api_secret
        self.session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _request(self, method: str, path: str, params: dict = None, body: dict = None) -> dict | None:
        session = await self._get_session()
        url = f"{self.BASE_URL}{path}"

        # Build query string for signature
        query_string = ""
        if params:
            query_string = ''.join(f"{k}{v}" for k, v in sorted(params.items()))
        
        # Build body string for signature
        body_str = json.dumps(body, separators=(',', ':')) if body else ""

        headers = get_auth_headers(
            api_key=self.api_key,
            secret_key=self.api_secret,
            query_params=query_string,
            body=body_str
        )

        try:
            if method == "GET":
                async with session.get(url, headers=headers, params=params) as resp:
                    data = await resp.json()
            else:
                async with session.post(url, headers=headers, json=body) as resp:
                    data = await resp.json()

            if data.get("code") == 0:
                return data.get("data")
            else:
                print(f"Bitunix API error: {data.get('msg', 'Unknown')} [{path}]")
                return None
        except Exception as e:
            print(f"Bitunix request error: {e}")
            return None

    async def get_account(self, margin_coin: str = "USDT") -> dict | None:
        """Get account information (private endpoint)"""
        params = {"marginCoin": margin_coin}
        return await self._request("GET", "/api/v1/futures/account", params=params)

    async def get_positions(self, symbol: str = None) -> dict | None:
        """Get current positions (private endpoint)"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._request("GET", "/api/v1/futures/position/get_positions", params=params)

    async def place_order(self, symbol: str, side: str, qty: float,
                          price: float = None, order_type: str = "LIMIT",
                          trade_side: str = "OPEN") -> dict | None:
        """Place a futures order (private endpoint)"""
        if settings.trading_mode.value == "paper":
            print("Paper mode: order not sent to exchange")
            return {"paper": True, "symbol": symbol, "side": side, "qty": qty}

        data = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type.upper(),
            "qty": str(qty),
            "tradeSide": trade_side,
            "effect": "GTC",
            "reduceOnly": False
        }
        
        if price and order_type.upper() == "LIMIT":
            data["price"] = str(price)

        return await self._request("POST", "/api/v1/futures/trade/place_order", body=data)

    async def cancel_order(self, symbol: str, order_id: str = None, client_id: str = None) -> dict | None:
        """Cancel an order (private endpoint)"""
        data = {
            "symbol": symbol,
        }
        if order_id:
            data["orderId"] = order_id
        if client_id:
            data["clientId"] = client_id
        
        return await self._request("POST", "/api/v1/futures/trade/cancel_order", body=data)

    async def get_history_orders(self, symbol: str = None) -> dict | None:
        """Get historical orders (private endpoint)"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._request("GET", "/api/v1/futures/trade/get_history_orders", params=params)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


bitunix_client = BitunixClient()
