// frontend/src/components/TradeLog.jsx
import React from 'react'
import './TradeLog.css'

export default function TradeLog({ trades }) {
    const sorted = [...(trades || [])].reverse()

    const totalPnl = sorted.reduce((sum, t) => sum + (t.pnl || 0), 0)
    const wins = sorted.filter(t => (t.pnl || 0) > 0).length
    const losses = sorted.filter(t => (t.pnl || 0) <= 0).length
    const winRate = sorted.length > 0 ? (wins / sorted.length) * 100 : 0

    return (
        <div className="glass-card trade-log">
            <h3>📋 Trade History</h3>

            <div className="log-stats">
                <div className="log-stat">
                    <span>Total Trades</span>
                    <span className="mono">{sorted.length}</span>
                </div>
                <div className="log-stat">
                    <span>Win Rate</span>
                    <span className={`mono ${winRate >= 50 ? 'pnl-positive' : 'pnl-negative'}`}>
                        {winRate.toFixed(1)}%
                    </span>
                </div>
                <div className="log-stat">
                    <span>Total PnL</span>
                    <span className={`mono ${totalPnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                        ${totalPnl.toFixed(2)}
                    </span>
                </div>
                <div className="log-stat">
                    <span>W / L</span>
                    <span className="mono">
                        <span className="pnl-positive">{wins}</span> / <span className="pnl-negative">{losses}</span>
                    </span>
                </div>
            </div>

            {sorted.length === 0 ? (
                <div className="empty-state">No trades yet. Start scanning for signals.</div>
            ) : (
                <div className="trade-list">
                    {sorted.map((trade, i) => (
                        <div key={i} className={`trade-row ${(trade.pnl || 0) >= 0 ? 'trade-win' : 'trade-loss'}`}>
                            <div className="trade-row-left">
                                <span className={`badge ${(trade.pnl || 0) >= 0 ? 'badge-strong' : 'badge-weak'}`}>
                                    {trade.status === 'closed_tp' ? 'TP' : trade.status === 'closed_sl' ? 'SL' : 'CLOSED'}
                                </span>
                                <span className="badge badge-moderate">{trade.fib_level}</span>
                                <span className="trade-symbol">{trade.symbol}</span>
                            </div>
                            <div className="trade-row-center">
                                <span className="trade-prices mono">
                                    ${trade.entry_price?.toFixed(2)} → ${trade.exit_price?.toFixed(2)}
                                </span>
                                <span className="trade-size mono">Size: {trade.position_size?.toFixed(6)}</span>
                            </div>
                            <div className="trade-row-right">
                                <span className={`trade-pnl mono ${(trade.pnl || 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                    {(trade.pnl || 0) >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                                </span>
                                <span className={`trade-pnl-pct mono ${(trade.pnl_percent || 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                    {(trade.pnl_percent || 0) >= 0 ? '+' : ''}{trade.pnl_percent?.toFixed(2)}%
                                </span>
                            </div>
                            <div className="trade-row-time">
                                {trade.timestamp_open && (
                                    <span className="trade-time">
                                        {new Date(trade.timestamp_open).toLocaleString('de-DE', {
                                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                        })}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
