// frontend/src/components/HistoryPanel.jsx
import React, { useState, useEffect } from 'react'
import { api } from '../utils/api'
import './HistoryPanel.css'

export default function HistoryPanel() {
    const [activeTab, setActiveTab] = useState('trades')
    const [trades, setTrades] = useState([])
    const [scannerHistory, setScannerHistory] = useState([])
    const [scannerStats, setScannerStats] = useState(null)
    const [errors, setErrors] = useState([])

    useEffect(() => {
        loadTrades()
        loadScannerStats()
        const interval = setInterval(() => {
            loadTrades()
            loadScannerStats()
        }, 10000)
        return () => clearInterval(interval)
    }, [])

    const loadTrades = async () => {
        try {
            const status = await api.get('/trading/status')
            if (status && status.account) {
                const openPositions = status.account.open_positions || []
                const closedTrades = status.account.closed_trades || []
                const allTrades = [
                    ...openPositions.map(t => ({ ...t, status: 'OPEN' })),
                    ...closedTrades.map(t => ({ ...t, status: 'CLOSED' }))
                ]
                setTrades(allTrades.sort((a, b) => new Date(b.timestamp_open || 0) - new Date(a.timestamp_open || 0)))
            }
        } catch (err) {
            console.error('Failed to load trades:', err)
        }
    }

    const loadScannerStats = async () => {
        try {
            const statsData = await api.get('/scanner/status')
            if (statsData && statsData.scanner) {
                setScannerStats(statsData.scanner)
            }
            const historyData = await api.get('/scanner/history?limit=50')
            if (historyData && Array.isArray(historyData.signals)) {
                setScannerHistory(historyData.signals)
            }
        } catch (err) {
            // Silently fail - scanner endpoints may not exist
        }
    }

    const formatPrice = (p) => {
        if (!p) return '$0.00'
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(p)
    }

    const formatDate = (timestamp) => {
        if (!timestamp) return '--'
        const date = new Date(timestamp)
        return date.toLocaleString('de-DE', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const getStrengthColor = (strength) => {
        const colors = {
            'SNIPER': '#00ffcc',
            'STRONG': '#00cc99',
            'MODERATE': '#ffaa00',
            'WEAK': '#ff5555'
        }
        return colors[strength] || '#888'
    }

    return (
        <div className="history-panel">
            <div className="history-tabs">
                <button 
                    className={`tab-btn ${activeTab === 'trades' ? 'active' : ''}`}
                    onClick={() => setActiveTab('trades')}
                >
                    📊 Trades ({trades.length})
                </button>
                <button 
                    className={`tab-btn ${activeTab === 'scanner' ? 'active' : ''}`}
                    onClick={() => setActiveTab('scanner')}
                >
                    🔍 Scanner {scannerStats?.is_running ? '🟢' : '🔴'}
                </button>
                <button 
                    className={`tab-btn ${activeTab === 'signals' ? 'active' : ''}`}
                    onClick={() => setActiveTab('signals')}
                >
                    🎯 Signals ({scannerHistory.length})
                </button>
            </div>

            <div className="history-content">
                {activeTab === 'trades' && (
                    <div className="trades-list">
                        {trades.length > 0 ? (
                            trades.map(trade => (
                                <div key={trade.id} className={`trade-item ${trade.status.toLowerCase()} ${trade.pnl > 0 ? 'profit' : trade.pnl < 0 ? 'loss' : ''}`}>
                                    <div className="trade-header">
                                        <span className="trade-symbol">{trade.symbol}</span>
                                        <span className="trade-status">{trade.status}</span>
                                    </div>
                                    <div className="trade-details">
                                        <div className="detail-row">
                                            <span className="label">Side:</span>
                                            <span className="value">{trade.side}</span>
                                        </div>
                                        <div className="detail-row">
                                            <span className="label">Entry:</span>
                                            <span className="value">{formatPrice(trade.entry_price)}</span>
                                        </div>
                                        {trade.exit_price && (
                                            <div className="detail-row">
                                                <span className="label">Exit:</span>
                                                <span className="value">{formatPrice(trade.exit_price)}</span>
                                            </div>
                                        )}
                                        <div className="detail-row">
                                            <span className="label">P&L:</span>
                                            <span className={`value ${trade.pnl >= 0 ? 'profit' : 'loss'}`}>
                                                {formatPrice(trade.pnl)} ({trade.pnl_percent?.toFixed(2)}%)
                                            </span>
                                        </div>
                                        <div className="detail-row">
                                            <span className="label">Time:</span>
                                            <span className="value">{formatDate(trade.timestamp_open)}</span>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="no-data">No trades yet</div>
                        )}
                    </div>
                )}

                {activeTab === 'scanner' && scannerStats && (
                    <div className="scanner-stats">
                        <div className="stats-grid">
                            <div className="stat-item">
                                <div className="stat-label">Status</div>
                                <div className={`stat-value ${scannerStats.is_running ? 'running' : 'stopped'}`}>
                                    {scannerStats.is_running ? '🟢 RUNNING' : '🔴 STOPPED'}
                                </div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-label">Scan Interval</div>
                                <div className="stat-value">{scannerStats.scan_interval}s</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-label">Total Scans</div>
                                <div className="stat-value">{scannerStats.total_scans}</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-label">Signals Found</div>
                                <div className="stat-value">{scannerStats.signals_found}</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-label">Last Scan</div>
                                <div className="stat-value">{scannerStats.last_scan ? formatDate(scannerStats.last_scan) : 'Never'}</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-label">History</div>
                                <div className="stat-value">{scannerStats.history_count} signals</div>
                            </div>
                        </div>
                        
                        <div className="scanner-info">
                            <h4>ℹ️ Background Scanner</h4>
                            <p>
                                The scanner runs continuously in the background, scanning the market every {scannerStats.scan_interval} seconds.
                                When SNIPER or STRONG signals are detected, Telegram notifications are sent (if enabled).
                            </p>
                            <p className="production-note">
                                🚀 Production-ready for Coolify deployment
                            </p>
                        </div>
                    </div>
                )}

                {activeTab === 'signals' && (
                    <div className="signals-list">
                        {scannerHistory.length > 0 ? (
                            scannerHistory.map((signal, idx) => (
                                <div key={idx} className={`signal-item ${signal.strength.toLowerCase()}`}>
                                    <div className="signal-header">
                                        <span className="signal-symbol">{signal.symbol}</span>
                                        <span 
                                            className="signal-strength"
                                            style={{ color: getStrengthColor(signal.strength) }}
                                        >
                                            {signal.strength}
                                        </span>
                                    </div>
                                    <div className="signal-details">
                                        <div className="detail-row">
                                            <span className="label">Entry:</span>
                                            <span className="value">{formatPrice(signal.entry_price)}</span>
                                        </div>
                                        <div className="detail-row">
                                            <span className="label">SL:</span>
                                            <span className="value">{formatPrice(signal.stop_loss)}</span>
                                        </div>
                                        <div className="detail-row">
                                            <span className="label">CRV:</span>
                                            <span className="value">{signal.crv?.toFixed(2)}</span>
                                        </div>
                                        <div className="detail-row">
                                            <span className="label">Score:</span>
                                            <span className="value">{signal.confluence_score}/5</span>
                                        </div>
                                        <div className="detail-row">
                                            <span className="label">Time:</span>
                                            <span className="value">{formatDate(signal.timestamp)}</span>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="no-data">No signals found yet. Scanner will notify when opportunities arise.</div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
