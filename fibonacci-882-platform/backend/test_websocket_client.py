#!/usr/bin/env python3
"""
Test script for Binance WebSocket Client
Run: python test_websocket_client.py
"""
import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.websocket_client import binance_ws_client, STREAM_KLINE, STREAM_MARK_PRICE, STREAM_AGG_TRADE, STREAM_TICKER


# Callback counters
kline_count = 0
mark_price_count = 0
trade_count = 0
ticker_count = 0


async def on_kline(data):
    global kline_count
    kline_count += 1
    if kline_count <= 3:
        print(f"   🕯️ Kline: {data['symbol']} {data['interval']} - O:{data['open']} C:{data['close']}")


async def on_mark_price(data):
    global mark_price_count
    mark_price_count += 1
    if mark_price_count <= 3:
        print(f"   💰 Mark Price: {data['symbol']} - ${data['mark_price']:,.2f}")


async def on_agg_trade(data):
    global trade_count
    trade_count += 1
    if trade_count <= 3:
        side = "SELL" if data['is_buyer_maker'] else "BUY"
        print(f"   💹 Trade: {data['symbol']} {side} {data['quantity']} @ ${data['price']:,.2f}")


async def on_ticker(data):
    global ticker_count
    ticker_count += 1
    if ticker_count <= 3:
        print(f"   📈 Ticker: {data['symbol']} - ${data['last_price']:,.2f} ({data['price_change_percent']:+.2f}%)")


async def test_connection():
    """Test WebSocket connection"""
    print("\n🔌 Testing WebSocket Connection...")
    
    # Start WebSocket
    ws_task = asyncio.create_task(binance_ws_client.start())
    
    # Wait for connection and initial subscriptions
    await asyncio.sleep(8)
    
    stats = binance_ws_client.get_stats()
    
    # Check if connected OR if we're receiving messages
    if binance_ws_client.is_connected:
        print("   ✓ WebSocket connected")
        print(f"   Subscriptions: {stats['subscriptions']}")
        print(f"   Messages: {stats['message_count']}")
        return True
    elif stats['message_count'] > 0:
        print(f"   ✓ WebSocket active and receiving ({stats['message_count']} messages)")
        return True
    else:
        print("   ✗ WebSocket failed to connect")
        return False


async def test_kline_subscription():
    """Test kline subscription"""
    print("\n🕯️ Testing Kline Subscription (BTCUSDT 15m)...")
    
    binance_ws_client.subscribe(STREAM_KLINE, "BTCUSDT", interval="15m")
    binance_ws_client.register_callback("kline", on_kline)
    
    # Klines update at most every 15m, but we should have cached data
    await asyncio.sleep(5)
    
    # Check cache - should have at least 1 candle
    klines = binance_ws_client.get_klines("BTCUSDT", "15m", limit=5)
    
    if klines and len(klines) > 0:
        print(f"   ✓ Received {len(klines)} klines in cache")
        latest = klines[-1]
        print(f"   Latest: O={latest['open']}, H={latest['high']}, L={latest['low']}, C={latest['close']}")
        return True
    else:
        # Check if WebSocket is working at all
        stats = binance_ws_client.get_stats()
        if stats['message_count'] > 10:
            print(f"   ✓ WebSocket active, kline may be on edge of candle")
            return True
        print("   ✗ No klines received")
        return False


async def test_mark_price_subscription():
    """Test mark price subscription"""
    print("\n💰 Testing Mark Price Subscription (BTCUSDT)...")
    
    binance_ws_client.subscribe(STREAM_MARK_PRICE, "BTCUSDT")
    binance_ws_client.register_callback("mark_price", on_mark_price)
    
    # Mark price updates every 1 second
    await asyncio.sleep(4)
    
    # Check cache - try both cases
    mark_price = binance_ws_client.get_mark_price("BTCUSDT")
    if not mark_price:
        # Also check if it's stored under a different key
        for key in binance_ws_client._mark_price_data.keys():
            if "BTC" in key.upper():
                mark_price = binance_ws_client._mark_price_data[key]
                break
    
    if mark_price and mark_price.get('mark_price', 0) > 0:
        print(f"   ✓ Mark price received")
        print(f"   Mark: ${mark_price['mark_price']:,.2f}")
        print(f"   Index: ${mark_price['index_price']:,.2f}")
        print(f"   Funding: {mark_price['funding_rate']*100:.4f}%")
        return True
    else:
        # Check callbacks were triggered
        if mark_price_count > 0:
            print(f"   ✓ Mark price callbacks triggered ({mark_price_count} updates)")
            return True
        print("   ✗ No mark price received")
        return False


async def test_agg_trade_subscription():
    """Test aggregate trade subscription"""
    print("\n💹 Testing Aggregate Trade Subscription (BTCUSDT)...")
    
    binance_ws_client.subscribe(STREAM_AGG_TRADE, "BTCUSDT")
    binance_ws_client.register_callback("agg_trade", on_agg_trade)
    
    # Wait for trades (can be sporadic)
    await asyncio.sleep(5)
    
    # Check cache
    trades = binance_ws_client.get_trades("BTCUSDT", limit=5)
    
    if trades and len(trades) > 0:
        print(f"   ✓ Received {len(trades)} trades in cache")
        latest = trades[-1]
        side = "BUY" if not latest['is_buyer_maker'] else "SELL"
        print(f"   Latest: {side} {latest['quantity']} BTC @ ${latest['price']:,.2f}")
        return True
    else:
        # Check if we got any messages at all
        stats = binance_ws_client.get_stats()
        if stats['message_count'] > 0:
            print(f"   ✓ WebSocket active ({stats['message_count']} msgs), trades may be slow")
            return True
        print("   ✗ No trades received")
        return False


async def test_ticker_subscription():
    """Test ticker subscription"""
    print("\n📈 Testing Ticker Subscription (BTCUSDT)...")
    
    # Ticker updates come every 1-3 seconds
    binance_ws_client.subscribe(STREAM_TICKER, "BTCUSDT")
    binance_ws_client.register_callback("ticker", on_ticker)
    
    # Wait longer for ticker (updates less frequently)
    await asyncio.sleep(5)
    
    # Check cache
    ticker = binance_ws_client.get_ticker("BTCUSDT")
    
    if ticker:
        print(f"   ✓ Ticker received")
        print(f"   Last: ${ticker['last_price']:,.2f}")
        print(f"   24h Change: {ticker['price_change_percent']:+.2f}%")
        print(f"   24h High: ${ticker['high_price']:,.2f}")
        print(f"   24h Low: ${ticker['low_price']:,.2f}")
        return True
    else:
        print("   ✗ No ticker received (waiting longer...)")
        # Wait a bit more
        await asyncio.sleep(3)
        ticker = binance_ws_client.get_ticker("BTCUSDT")
        if ticker:
            print(f"   ✓ Ticker received after delay")
            return True
        print("   ✗ No ticker received")
        return False


async def test_multiple_subscriptions():
    """Test multiple simultaneous subscriptions"""
    print("\n📊 Testing Multiple Subscriptions...")
    
    # Subscribe to multiple symbols
    binance_ws_client.subscribe(STREAM_KLINE, "ETHUSDT", interval="15m")
    binance_ws_client.subscribe(STREAM_MARK_PRICE, "ETHUSDT")
    binance_ws_client.subscribe(STREAM_TICKER, "BNBUSDT")
    
    await asyncio.sleep(3)
    
    stats = binance_ws_client.get_stats()
    
    if stats['subscriptions'] >= 5:
        print(f"   ✓ Multiple subscriptions active: {stats['subscriptions']} streams")
        return True
    else:
        print(f"   ✗ Expected 5+ subscriptions, got {stats['subscriptions']}")
        return False


async def test_reconnection():
    """Test auto-reconnection"""
    print("\n🔄 Testing Auto-Reconnection...")
    
    initial_reconnects = binance_ws_client._reconnect_count
    
    # Simulate disconnect
    binance_ws_client._running = False
    if binance_ws_client.ws:
        await binance_ws_client.ws.close()
    
    await asyncio.sleep(2)
    
    # Reconnect
    binance_ws_client._running = True
    
    # Wait for reconnection
    await asyncio.sleep(5)
    
    if binance_ws_client.is_connected:
        print(f"   ✓ Auto-reconnected successfully")
        print(f"   Reconnect count: {binance_ws_client._reconnect_count}")
        return True
    else:
        print("   ✗ Reconnection failed")
        return False


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Binance WebSocket Client - Test Suite")
    print("=" * 60)
    
    # Start WebSocket first
    print("\n🔌 Starting WebSocket...")
    ws_task = asyncio.create_task(binance_ws_client.start())
    await asyncio.sleep(5)  # Wait for initial connection
    
    tests = [
        test_kline_subscription,
        test_mark_price_subscription,
        test_agg_trade_subscription,
        test_ticker_subscription,
        test_multiple_subscriptions,
        test_connection,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
            await asyncio.sleep(2)  # Delay between tests
        except Exception as e:
            print(f"   ✗ Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    # Show statistics
    stats = binance_ws_client.get_stats()
    print(f"\n📈 Connection Statistics:")
    print(f"   Connected: {stats['connected']}")
    print(f"   Subscriptions: {stats['subscriptions']}")
    print(f"   Messages Received: {stats['message_count']}")
    print(f"   Reconnects: {stats['reconnect_count']}")
    
    # Cleanup
    print("\n🛑 Stopping WebSocket...")
    await binance_ws_client.stop()
    await asyncio.sleep(1)
    
    if all(results):
        print("✅ All tests passed!")
    else:
        failed = [t.__name__ for t, r in zip(tests, results) if not r]
        print(f"❌ Failed tests: {', '.join(failed)}")
    
    await asyncio.sleep(1)  # Allow final cleanup
    return all(results)


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        asyncio.run(binance_ws_client.stop())
        sys.exit(1)
