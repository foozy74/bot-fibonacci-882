#!/usr/bin/env python3
"""
Test script for Binance Market Data Client
Run: python test_binance_client.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.binance_client import binance_client


async def test_server_time():
    """Test server time endpoint"""
    print("\n🕐 Testing Server Time...")
    server_time = await binance_client.get_server_time()
    print(f"   Server Time: {server_time}")
    print(f"   ✓ Success" if server_time > 0 else "   ✗ Failed")
    return server_time > 0


async def test_exchange_info():
    """Test exchange info endpoint"""
    print("\n📊 Testing Exchange Info...")
    info = await binance_client.get_exchange_info()
    
    if info and "symbols" in info:
        trading_symbols = [s for s in info["symbols"] if s.get("status") == "TRADING"]
        print(f"   Total symbols: {len(info.get('symbols', []))}")
        print(f"   Trading symbols: {len(trading_symbols)}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_symbol_info():
    """Test symbol info for BTCUSDT"""
    print("\n₿ Testing Symbol Info (BTCUSDT)...")
    info = await binance_client.get_symbol_info("BTCUSDT")
    
    if info:
        print(f"   Symbol: {info.get('symbol')}")
        print(f"   Status: {info.get('status')}")
        print(f"   Min Notional: {info.get('filters', [{}])[0].get('minNotional', 'N/A')}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_klines():
    """Test kline/candlestick data"""
    print("\n🕯️ Testing Klines (BTCUSDT 15m)...")
    klines = await binance_client.get_klines("BTCUSDT", "15m", limit=5)
    
    if klines and len(klines) > 0:
        print(f"   Retrieved {len(klines)} candles")
        latest = klines[-1]
        print(f"   Latest: O={latest['open']}, H={latest['high']}, L={latest['low']}, C={latest['close']}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_ticker_24hr():
    """Test 24hr ticker"""
    print("\n📈 Testing 24hr Ticker (BTCUSDT)...")
    ticker = await binance_client.get_ticker("BTCUSDT")
    
    if ticker:
        print(f"   Last Price: ${ticker.get('last', 0):,.2f}")
        print(f"   24h Change: {ticker.get('price_change_percent', 0):+.2f}%")
        print(f"   24h High: ${ticker.get('high_24h', 0):,.2f}")
        print(f"   24h Low: ${ticker.get('low_24h', 0):,.2f}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_orderbook():
    """Test order book depth"""
    print("\n📚 Testing Order Book (BTCUSDT)...")
    orderbook = await binance_client.get_orderbook("BTCUSDT", limit=10)
    
    if orderbook and "bids" in orderbook:
        best_bid = orderbook["bids"][0] if orderbook["bids"] else [0, 0]
        best_ask = orderbook["asks"][0] if orderbook["asks"] else [0, 0]
        spread = best_ask[0] - best_bid[0]
        
        print(f"   Best Bid: ${best_bid[0]:,.2f} ({best_bid[1]} BTC)")
        print(f"   Best Ask: ${best_ask[0]:,.2f} ({best_ask[1]} BTC)")
        print(f"   Spread: ${spread:,.2f}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_mark_price():
    """Test mark price"""
    print("\n💰 Testing Mark Price (BTCUSDT)...")
    mark_price = await binance_client.get_mark_price("BTCUSDT")
    
    if mark_price:
        print(f"   Mark Price: ${mark_price.get('mark_price', 0):,.2f}")
        print(f"   Index Price: ${mark_price.get('index_price', 0):,.2f}")
        print(f"   Last Funding Rate: {mark_price.get('last_funding_rate', 0)*100:.4f}%")
        print(f"   Next Funding: {mark_price.get('next_funding_time', 0)}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_funding_rate():
    """Test funding rate history"""
    print("\n💸 Testing Funding Rate History (BTCUSDT)...")
    funding_rates = await binance_client.get_funding_rate("BTCUSDT", limit=5)
    
    if funding_rates and len(funding_rates) > 0:
        print(f"   Retrieved {len(funding_rates)} funding rates")
        latest = funding_rates[0]
        print(f"   Latest: {latest.get('funding_rate', 0)*100:.4f}% at {latest.get('funding_time')}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_open_interest():
    """Test open interest"""
    print("\n📊 Testing Open Interest (BTCUSDT)...")
    oi = await binance_client.get_open_interest("BTCUSDT")
    
    if oi:
        print(f"   Open Interest: {oi.get('open_interest', 0):,.2f} BTC")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_agg_trades():
    """Test aggregate trades"""
    print("\n💹 Testing Aggregate Trades (BTCUSDT)...")
    trades = await binance_client.get_agg_trades("BTCUSDT", limit=5)
    
    if trades and len(trades) > 0:
        print(f"   Retrieved {len(trades)} trades")
        latest = trades[0]
        print(f"   Latest: {latest.get('qty', 0)} BTC @ ${latest.get('price', 0):,.2f}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_top_long_short_ratio():
    """Test top trader long/short ratio"""
    print("\n📉 Testing Top Trader Long/Short Ratio (BTCUSDT)...")
    ratio = await binance_client.get_top_long_short_ratio("BTCUSDT", period="1h", limit=1)
    
    if ratio:
        print(f"   Long/Short Ratio: {ratio.get('long_short_ratio', 0):.4f}")
        print(f"   Long Accounts: {ratio.get('long_account', 0)*100:.2f}%")
        print(f"   Short Accounts: {ratio.get('short_account', 0)*100:.2f}%")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def test_taker_volume():
    """Test taker buy/sell volume (uses long/short ratio as proxy)"""
    print("\n📊 Testing Taker Buy/Sell Volume (BTCUSDT - via L/S ratio)...")
    volume = await binance_client.get_taker_buy_sell_volume("BTCUSDT", period="1h", limit=1)
    
    if volume and volume.get('buy_sell_ratio', 0) > 0:
        print(f"   Buy/Sell Ratio: {volume.get('buy_sell_ratio', 0):.4f}")
        print(f"   Buy Side: {volume.get('buy_vol', 0)*100:.2f}%")
        print(f"   Sell Side: {volume.get('sell_vol', 0)*100:.2f}%")
        print(f"   ✓ Success (using long/short ratio as proxy)")
        return True
    
    print("   ✗ Failed")
    return False


async def test_symbols():
    """Test symbols list"""
    print("\n🔤 Testing Symbols List...")
    symbols = await binance_client.get_symbols()
    
    if symbols and len(symbols) > 0:
        print(f"   Total symbols: {len(symbols)}")
        print(f"   First 10: {', '.join(symbols[:10])}")
        print(f"   ✓ Success")
        return True
    
    print("   ✗ Failed")
    return False


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Binance Market Data Client - Test Suite")
    print("=" * 60)
    
    tests = [
        test_server_time,
        test_exchange_info,
        test_symbol_info,
        test_klines,
        test_ticker_24hr,
        test_orderbook,
        test_mark_price,
        test_funding_rate,
        test_open_interest,
        test_agg_trades,
        test_top_long_short_ratio,
        test_taker_volume,
        test_symbols,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
            await asyncio.sleep(0.1)  # Small delay between tests
        except Exception as e:
            print(f"   ✗ Exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    if all(results):
        print("✅ All tests passed!")
    else:
        failed = [t.__name__ for t, r in zip(tests, results) if not r]
        print(f"❌ Failed tests: {', '.join(failed)}")
    
    await binance_client.close()
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
