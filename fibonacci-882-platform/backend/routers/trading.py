# backend/routers/trading.py
from fastapi import APIRouter, HTTPException
from config import settings, TradingPlatform, TradingMode
from models.schemas import PaperAccount, Signal, SignalType, SignalStrength, TradeStatus
from services.trade_manager import trade_manager
from services.signal_detector import signal_detector
from services.binance_futures_client import binance_futures_client, OrderType, OrderSide, PositionSide
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])


@router.get("/status")
async def get_status():
    """Get trading status including account info, positions, and open orders"""
    
    # Set credentials for Binance Futures client
    if settings.binance_futures_api_key and settings.binance_futures_api_secret:
        binance_futures_client.set_credentials(
            settings.binance_futures_api_key,
            settings.binance_futures_api_secret
        )
        binance_futures_client.set_testnet(settings.binance_testnet)
    
    account = trade_manager.get_account()
    balance_source = "paper"
    balance_warning = None
    live_positions = []
    live_orders = []
    
    if settings.trading_mode.value == "live":
        if settings.trading_platform == TradingPlatform.BINANCE_FUTURES:
            try:
                # Get account info
                binance_account = await binance_futures_client.get_account()
                if binance_account:
                    account.balance = float(binance_account.get("availableBalance", 0))
                    account.equity = float(binance_account.get("totalWalletBalance", 0))
                    balance_source = "live"
                    
                    # Get positions
                    positions = await binance_futures_client.get_positions()
                    if positions:
                        live_positions = [
                            {
                                "symbol": p.get("symbol"),
                                "side": "LONG" if float(p.get("positionAmt", 0)) > 0 else "SHORT",
                                "size": abs(float(p.get("positionAmt", 0))),
                                "entry_price": float(p.get("entryPrice", 0)),
                                "mark_price": float(p.get("markPrice", 0)),
                                "unrealized_pnl": float(p.get("unRealizedProfit", 0)),
                                "leverage": int(p.get("leverage", 1)),
                            }
                            for p in positions if float(p.get("entryPrice", 0)) > 0
                        ]
                    
                    # Get open orders
                    orders = await binance_futures_client.get_open_orders(settings.symbol)
                    if orders:
                        live_orders = [
                            {
                                "order_id": o.get("orderId"),
                                "symbol": o.get("symbol"),
                                "side": o.get("side"),
                                "type": o.get("type"),
                                "quantity": float(o.get("origQty", 0)),
                                "price": float(o.get("price", 0)),
                                "status": o.get("status"),
                            }
                            for o in orders
                        ]
                else:
                    balance_warning = "Binance API returned invalid data"
                    balance_source = "fallback"
            except Exception as e:
                logger.error(f"Binance status error: {e}")
                balance_warning = f"Binance connection error: {str(e)}"
                balance_source = "fallback"
        else:
            balance_warning = "Bitunix trading unavailable"
            balance_source = "fallback"
    else:
        account.balance = settings.paper_balance
        account.equity = settings.paper_balance
    
    return {
        "mode": settings.trading_mode.value,
        "platform": settings.trading_platform if isinstance(settings.trading_platform, str) else settings.trading_platform.value,
        "testnet": settings.binance_testnet if (settings.trading_platform if isinstance(settings.trading_platform, str) else settings.trading_platform.value) == 'binance_futures' else False,
        "symbol": settings.symbol,
        "timeframe": settings.timeframe.value,
        "account": {
            "balance": account.balance,
            "equity": account.equity,
            "total_pnl": account.total_pnl,
        },
        "balance_source": balance_source,
        "balance_warning": balance_warning,
        "paper_positions": [p.dict() for p in account.open_positions],
        "live_positions": live_positions,
        "live_orders": live_orders,
        "total_trades": len(account.open_positions) + len(account.closed_trades),
    }


@router.post("/mode")
async def set_mode(mode: str):
    if mode in [m.value for m in TradingMode]:
        settings.trading_mode = TradingMode(mode)
        return {"status": "ok", "mode": settings.trading_mode.value}
    return {"status": "error", "msg": "Invalid mode. Use 'paper' or 'live'"}


@router.post("/platform")
async def set_platform(platform: str):
    if platform in [p.value for p in TradingPlatform]:
        settings.trading_platform = TradingPlatform(platform)
        return {"status": "ok", "platform": settings.trading_platform.value}
    return {"status": "error", "msg": "Invalid platform. Use 'bitunix' or 'binance_futures'"}


@router.post("/leverage")
async def set_leverage(symbol: str, leverage: int):
    """
    Set leverage for a symbol (1-125)
    Only works in live mode with Binance Futures
    """
    if settings.trading_mode.value != "live":
        return {"status": "error", "msg": "Only available in live mode"}
    
    if leverage < 1 or leverage > 125:
        return {"status": "error", "msg": "Leverage must be between 1 and 125"}
    
    # Set credentials
    if settings.binance_futures_api_key and settings.binance_futures_api_secret:
        binance_futures_client.set_credentials(
            settings.binance_futures_api_key,
            settings.binance_futures_api_secret
        )
    
    try:
        result = await binance_futures_client.set_leverage(symbol, leverage)
        if result:
            return {
                "status": "ok",
                "symbol": symbol,
                "leverage": result.get("leverage"),
                "max_notional": result.get("maxNotionalValue"),
            }
        else:
            return {"status": "error", "msg": "Failed to set leverage"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


@router.post("/margin-mode")
async def set_margin_mode(symbol: str, mode: str):
    """
    Set margin mode: ISOLATED or CROSSED
    Only works in live mode with Binance Futures
    """
    if settings.trading_mode.value != "live":
        return {"status": "error", "msg": "Only available in live mode"}
    
    if mode.upper() not in ["ISOLATED", "CROSSED"]:
        return {"status": "error", "msg": "Mode must be ISOLATED or CROSSED"}
    
    # Set credentials
    if settings.binance_futures_api_key and settings.binance_futures_api_secret:
        binance_futures_client.set_credentials(
            settings.binance_futures_api_key,
            settings.binance_futures_api_secret
        )
    
    try:
        result = await binance_futures_client.set_margin_mode(symbol, mode.upper())
        if result:
            return {
                "status": "ok",
                "symbol": symbol,
                "margin_mode": mode.upper(),
            }
        else:
            return {"status": "error", "msg": "Failed to set margin mode"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


@router.get("/account")
async def get_account():
    return trade_manager.get_account().dict()


@router.get("/open-trades")
async def get_open_trades():
    account = trade_manager.get_account()
    return [t.dict() for t in account.open_positions]


@router.get("/closed-trades")
async def get_closed_trades():
    account = trade_manager.get_account()
    return [t.dict() for t in account.closed_trades]


@router.post("/close-all")
async def close_all_trades(current_price: float):
    closed = trade_manager.close_all(current_price)
    return {
        "status": "ok",
        "closed": len(closed),
        "trades": [t.dict() for t in closed],
    }


@router.post("/reset")
async def reset_account():
    trade_manager.reset()
    return {"status": "ok", "balance": settings.paper_balance}


@router.post("/execute")
async def execute_trade(data: dict):
    """
    Execute a trade based on a signal
    Supports Paper Trading and Binance Futures (Live)
    
    Request body:
    {
        "signal_id": "abc123",
        "action": "buy",  // or "sell"
        "entry_price": 50000,
        "stop_loss": 49000,
        "take_profits": [51000, 52000],
        "quantity": 0.1  // optional, calculated if not provided
    }
    """
    # Set credentials
    if settings.binance_futures_api_key and settings.binance_futures_api_secret:
        binance_futures_client.set_credentials(
            settings.binance_futures_api_key,
            settings.binance_futures_api_secret
        )
        binance_futures_client.set_testnet(settings.binance_testnet)
    
    signal_id = data.get("signal_id")
    action = data.get("action", "buy")
    entry_price = data.get("entry_price", 0)
    stop_loss = data.get("stop_loss", 0)
    take_profits = data.get("take_profits", [])
    quantity = data.get("quantity")
    
    if not signal_id or entry_price == 0:
        return {"status": "error", "msg": "Invalid signal data"}
    
    # Paper mode - use local trade manager
    if settings.trading_mode.value == "paper":
        signal = Signal(
            id=signal_id,
            timestamp=datetime.now(timezone.utc),
            symbol=settings.symbol,
            timeframe=settings.timeframe.value,
            type=SignalType.LONG if action == "buy" else SignalType.SHORT,
            strength=SignalStrength.STRONG,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profits=take_profits,
            crv=2.0,
            confluence=None
        )
        
        trade = trade_manager.open_trade(signal, entry_price)
        if trade:
            return {
                "status": "ok",
                "msg": f"Paper trade opened successfully",
                "trade": trade.dict(),
                "mode": "paper"
            }
        else:
            return {"status": "error", "msg": "Failed to open paper trade"}
    
    # Live mode - Binance Futures
    if settings.trading_platform == TradingPlatform.BINANCE_FUTURES:
        try:
            # Calculate quantity if not provided
            if not quantity:
                quantity = await calculate_position_size(
                    entry_price, 
                    stop_loss, 
                    settings.risk.max_risk_per_trade
                )
            
            # Place market order
            order = await binance_futures_client.place_market_order(
                symbol=settings.symbol,
                side="BUY" if action == "buy" else "SELL",
                quantity=quantity,
                position_side="LONG" if action == "buy" else "SHORT",
                reduce_only=False
            )
            
            if order:
                response = {
                    "status": "ok",
                    "msg": f"Binance Futures order placed",
                    "order": {
                        "order_id": order.get("orderId"),
                        "symbol": order.get("symbol"),
                        "side": order.get("side"),
                        "type": order.get("type"),
                        "quantity": order.get("origQty"),
                        "price": order.get("price"),
                        "avg_price": order.get("avgPrice"),
                        "executed_qty": order.get("executedQty"),
                        "cum_quote": order.get("cumQuote"),
                        "status": order.get("status"),
                        "time_in_force": order.get("timeInForce"),
                        "reduce_only": order.get("reduceOnly"),
                        "position_side": order.get("positionSide"),
                        "update_time": order.get("updateTime"),
                    },
                    "platform": "binance_futures",
                    "testnet": settings.binance_testnet,
                }
                
                # Place take profit orders if specified
                if take_profits:
                    tp_orders = []
                    qty_per_tp = quantity / len(take_profits)
                    for i, tp_price in enumerate(take_profits):
                        tp_order = await binance_futures_client.place_limit_order(
                            symbol=settings.symbol,
                            side="SELL" if action == "buy" else "BUY",
                            quantity=round(qty_per_tp, 3),
                            price=tp_price,
                            position_side="LONG" if action == "buy" else "SHORT",
                            reduce_only=True
                        )
                        if tp_order:
                            tp_orders.append({
                                "tp_index": i,
                                "price": tp_price,
                                "order_id": tp_order.get("orderId")
                            })
                    
                    if tp_orders:
                        response["take_profit_orders"] = tp_orders
                
                # Place stop loss order
                if stop_loss > 0:
                    sl_order = await binance_futures_client.place_stop_order(
                        symbol=settings.symbol,
                        side="SELL" if action == "buy" else "BUY",
                        quantity=quantity,
                        stop_price=stop_loss,
                        position_side="LONG" if action == "buy" else "SHORT",
                        reduce_only=True
                    )
                    if sl_order:
                        response["stop_loss_order"] = {
                            "price": stop_loss,
                            "order_id": sl_order.get("orderId")
                        }
                
                return response
            else:
                return {"status": "error", "msg": "Failed to place Binance order"}
                
        except Exception as e:
            logger.error(f"Live trade execution error: {e}")
            return {"status": "error", "msg": f"Binance error: {str(e)}"}
    
    return {"status": "error", "msg": "Invalid trading platform"}


async def calculate_position_size(entry_price: float, stop_loss: float, risk_pct: float) -> float:
    """Calculate position size based on risk"""
    if entry_price == 0 or stop_loss == 0:
        return 0.001
    
    risk_amount = settings.paper_balance * risk_pct
    risk_per_unit = abs(entry_price - stop_loss)
    
    if risk_per_unit == 0:
        return 0.001
    
    return round((risk_amount / risk_per_unit), 3)
