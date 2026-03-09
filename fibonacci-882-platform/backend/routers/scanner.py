# backend/routers/scanner.py
"""
Scanner control and statistics router
"""
from fastapi import APIRouter
from services.background_scanner import background_scanner
from config import settings as app_settings

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/status")
async def get_scanner_status():
    """Get background scanner status and statistics"""
    stats = background_scanner.get_stats()
    return {
        "status": "ok",
        "scanner": stats
    }


@router.post("/start")
async def start_scanner():
    """Start the background scanner"""
    if background_scanner.is_running:
        return {"status": "warning", "msg": "Scanner already running"}
    
    await background_scanner.start()
    return {"status": "ok", "msg": "Scanner started"}


@router.post("/stop")
async def stop_scanner():
    """Stop the background scanner"""
    if not background_scanner.is_running:
        return {"status": "warning", "msg": "Scanner not running"}
    
    await background_scanner.stop()
    return {"status": "ok", "msg": "Scanner stopped"}


@router.put("/interval")
async def set_scan_interval(interval: int):
    """
    Update scan interval
    
    Query params:
        interval: Scan interval in seconds (min: 10)
    """
    background_scanner.update_interval(interval)
    return {
        "status": "ok",
        "msg": f"Scan interval updated to {interval}s",
        "interval": background_scanner.scan_interval
    }


@router.get("/history")
async def get_signal_history(limit: int = 50):
    """
    Get signal history
    
    Query params:
        limit: Max signals to return (default: 50)
    """
    history = background_scanner._load_signal_history()
    
    # Sort by timestamp descending and limit
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "status": "ok",
        "count": len(history),
        "signals": history[:limit]
    }


@router.delete("/history")
async def clear_signal_history():
    """Clear signal history"""
    from pathlib import Path
    history_file = Path(__file__).parent.parent / "data" / "signal_history.json"
    
    if history_file.exists():
        history_file.unlink()
        return {"status": "ok", "msg": "Signal history cleared"}
    
    return {"status": "ok", "msg": "No history to clear"}
