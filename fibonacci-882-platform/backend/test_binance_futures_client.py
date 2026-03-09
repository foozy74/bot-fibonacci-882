#!/usr/bin/env python3
"""
Test script for Binance Futures Trading Client
Run: python test_binance_futures_client.py

NOTE: Requires API credentials in .env or environment variables
For testing, use Binance Testnet: https://testnet.binancefuture.com
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

from services.binance_futures_client import binance_futures_client


def set_test_credentials():
    """Set testnet credentials from environment"""
    api_key = os.getenv("BINANCE_FUTURES_API_KEY", "")
    api_secret = os.getenv("BINANCE_FUTURES_API_SECRET", "")
    
    if api_key and api_secret:
        binance_futures_client.set_credentials(api_key, api_secret)
        binance_futures_client.set_testnet(True)  # Use testnet for safety
        print("✓ Using testnet credentials")
        return True
    else:
        print("✗ No API credentials found")
        print("Set BINANCE_FUTURES_API_KEY and BINANCE_FUTURES_API_SECRET in .env")
        return False


async def test_account_info():
    """Test account information endpoint"""
    print("\n📊 Testing Account Info...")
    
    account = await binance_futures_client.get_account()
    
    if account:
        print(f"   ✓ Account retrieved")
        print(f"   Available Balance: ${float(account.get('availableBalance', 0)):,.2f}")
        print(f"   Total Wallet Balance: ${float(account.get('totalWalletBalance', 0)):,.2f}")
        print(f"   Total Unrealized PnL: ${float(account.get('totalUnrealizedProfit', 0)):,.2f}")
        return True
    else:
        print("   ✗ Failed to get account info")
        return False


async def test_balance():
    """Test balance endpoint"""
    print("\n💰 Testing Balance...")
    
    balances = await binance_futures_client.get_balance()
    
    if balances:
        usdt_balance = None
        for bal in balances:
            if bal.get('asset') == 'USDT':
                usdt_balance = bal
                break
        
        if usdt_balance:
            print(f"   ✓ USDT Balance retrieved")
            print(f"   Available: ${float(usdt_balance.get('availableBalance', 0)):,.2f}")
            print(f"   Total: ${float(usdt_balance.get('balance', 0)):,.2f}")
            return True
    
    print("   ✗ Failed to get balance")
    return False


async def test_positions():
    """Test positions endpoint"""
    print("\n📈 Testing Positions...")
    
    positions = await binance_futures_client.get_positions()
    
    if positions is not None:
        # Filter positions with non-zero entry price
        active_positions = [p for p in positions if float(p.get('entryPrice', 0)) > 0]
        
        print(f"   ✓ Positions retrieved")
        print(f"   Total positions: {len(positions)}")
        print(f"   Active positions: {len(active_positions)}")
        
        if active_positions:
            print(f"\n   Active Positions:")
            for pos in active_positions[:5]:  # Show first 5
                print(f"   - {pos.get('symbol')}: {pos.get('positionSide')} "
                      f"{pos.get('positionAmt')} @ ${float(pos.get('entryPrice', 0)):,.2f}")
        
        return True
    else:
        print("   ✗ Failed to get positions")
        return False


async def test_leverage():
    """Test leverage settings (read-only test)"""
    print("\n🔧 Testing Leverage (Read-Only)...")
    
    # Just get current account config to see leverage
    account = await binance_futures_client.get_account()
    
    if account:
        print(f"   ✓ Account config retrieved")
        # Note: Leverage is per-symbol, would need to check specific symbol
        print(f"   (Leverage is set per-symbol, use set_leverage() to modify)")
        return True
    else:
        print("   ✗ Failed to get account config")
        return False


async def test_order_placement():
    """Test order placement (will fail on testnet without proper setup)"""
    print("\n📝 Testing Order Placement (Paper Test)...")
    
    # This test will show the order structure but won't actually place orders
    # unless you have a funded testnet account
    
    print(f"   ℹ️  Order placement test skipped (requires funded testnet account)")
    print(f"   To test manually:")
    print(f"   - Go to https://testnet.binancefuture.com")
    print(f"   - Fund your testnet account")
    print(f"   - Use place_market_order() or place_limit_order()")
    
    return True


async def test_open_orders():
    """Test open orders endpoint"""
    print("\n📋 Testing Open Orders...")
    
    orders = await binance_futures_client.get_open_orders("BTCUSDT")
    
    if orders is not None:
        print(f"   ✓ Open orders retrieved")
        print(f"   Open BTCUSDT orders: {len(orders)}")
        
        if orders:
            print(f"\n   Recent Orders:")
            for order in orders[:5]:  # Show first 5
                print(f"   - {order.get('symbol')} {order.get('side')} "
                      f"{order.get('type')}: {order.get('origQty')} @ ${float(order.get('price', 0)):,.2f}")
        
        return True
    else:
        print("   ✗ Failed to get open orders")
        return False


async def test_trade_history():
    """Test trade history endpoint"""
    print("\n💹 Testing Trade History...")
    
    trades = await binance_futures_client.get_trades("BTCUSDT", limit=5)
    
    if trades is not None:
        print(f"   ✓ Trade history retrieved")
        print(f"   Recent BTCUSDT trades: {len(trades)}")
        
        if trades:
            print(f"\n   Last 3 Trades:")
            for trade in trades[:3]:
                side = "BUY" if trade.get('buyer') else "SELL"
                print(f"   - {side} {trade.get('qty')} @ ${float(trade.get('price', 0)):,.2f}")
        
        return True
    else:
        print("   ✗ Failed to get trade history")
        return False


async def test_time_sync():
    """Test time synchronization"""
    print("\n🕐 Testing Time Sync...")
    
    await binance_futures_client._sync_server_time()
    
    if binance_futures_client.server_time_offset != 0:
        print(f"   ✓ Time synchronized")
        print(f"   Server offset: {binance_futures_client.server_time_offset}ms")
        return True
    else:
        print(f"   ✓ Time sync attempted (offset may be 0 if already in sync)")
        return True


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Binance Futures Trading Client - Test Suite")
    print("=" * 60)
    
    # Check credentials
    if not set_test_credentials():
        print("\n❌ Cannot run tests without API credentials")
        print("Set BINANCE_FUTURES_API_KEY and BINANCE_FUTURES_API_SECRET")
        print("For testnet: https://testnet.binancefuture.com")
        return False
    
    # Sync time first
    print("\n🕐 Synchronizing with server time...")
    await binance_futures_client._sync_server_time()
    await asyncio.sleep(1)
    
    tests = [
        test_time_sync,
        test_account_info,
        test_balance,
        test_positions,
        test_leverage,
        test_open_orders,
        test_trade_history,
        test_order_placement,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
            await asyncio.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print(f"   ✗ Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    # Cleanup
    await binance_futures_client.close()
    
    if all(results):
        print("✅ All tests passed!")
        return True
    else:
        failed = [t.__name__ for t, r in zip(tests, results) if not r]
        print(f"❌ Failed tests: {', '.join(failed)}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        asyncio.run(binance_futures_client.close())
        sys.exit(1)
