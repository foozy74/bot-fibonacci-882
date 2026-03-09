// frontend/src/components/SignalPanel.jsx
import React, { useState } from 'react'
import './SignalPanel.css'

export default function SignalPanel({ signals, onScan, onExecute }) {
    const [scanning, setScanning] = useState(false)
    const [lastMessage, setLastMessage] = useState('')

    const handleScan = async () => {
        setScanning(true)
        try {
            const res = await onScan()
            setLastMessage(res.message || 'Scan complete')
        } catch (err) {
            setLastMessage('Scan failed')
        }
        setScanning(false)
    }

    const strengthBadge = (strength) => {
        const map = { sniper: 'badge-sniper', strong: 'badge-strong', moderate: 'badge-moderate', weak: 'badge-weak' }
        return map[strength] || 'badge-weak'
    }

    return (
        <div className="glass-card signal-panel">
            <h3>🎯 Signal Scanner</h3>

            <button className="btn btn-primary scan-btn" onClick={handleScan} disabled={scanning}>
                {scanning ? '⏳ Scanning...' : '🔍 Scan Now'}
            </button>

            {lastMessage && <div className="scan-message">{lastMessage}</div>}

            <div className="signal-list">
                {signals.length === 0 && (
                    <div className="empty-state">No signals detected. Run a scan.</div>
                )}

                {signals.map((sig, i) => (
                    <div key={i} className="signal-card">
                        <div className="signal-header">
                            <span className={`badge ${strengthBadge(sig.strength)}`}>{sig.strength}</span>
                            <span className="mono signal-fib">Fib {sig.confluence?.fib_level_name}</span>
                            <span className="signal-crv">CRV: {sig.crv}</span>
                        </div>

                        <div className="signal-details">
                            <div className="signal-row">
                                <span>Entry</span>
                                <span className="mono">${sig.entry_price?.toLocaleString()}</span>
                            </div>
                            <div className="signal-row">
                                <span>Stop Loss</span>
                                <span className="mono pnl-negative">${sig.stop_loss?.toLocaleString()}</span>
                            </div>
                            <div className="signal-row">
                                <span>TP1</span>
                                <span className="mono pnl-positive">${sig.take_profits?.[0]?.toLocaleString()}</span>
                            </div>
                        </div>

                        <div className="confluence-bar">
                            <span>Confluence: {sig.confluence?.total_score}/{sig.confluence?.max_score}</span>
                            <div className="confluence-dots">
                                {sig.confluence?.fib_level_hit && <span className="dot dot-active" title="Fib Level">F</span>}
                                {sig.confluence?.hammer_detected && <span className="dot dot-active" title="Hammer">H</span>}
                                {sig.confluence?.guss_valid && <span className="dot dot-active" title="Guss">G</span>}
                                {sig.confluence?.lsob_present && <span className="dot dot-active" title="LSOB">L</span>}
                                {sig.confluence?.ema_confluence && <span className="dot dot-active" title="EMA">E</span>}
                            </div>
                        </div>

                        <button className="btn btn-success" onClick={() => onExecute(sig.id)}>
                            Execute Trade
                        </button>
                    </div>
                ))}
            </div>
        </div>
    )
}
