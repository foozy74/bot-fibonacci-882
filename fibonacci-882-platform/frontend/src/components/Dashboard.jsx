// frontend/src/components/Dashboard.jsx
import React, { useState, useEffect, useRef } from 'react'
import { api } from '../utils/api'
import HistoryPanel from './HistoryPanel'
import './Dashboard.css'

export default function Dashboard() {
    const [status, setStatus] = useState(null)
    const [price, setPrice] = useState(0)
    const [signals, setSignals] = useState([])
    const [fibonacci, setFibonacci] = useState(null)
    const [wsConnected, setWsConnected] = useState(false)
    const [lastUpdate, setLastUpdate] = useState(null)
    const [tradingMode, setTradingMode] = useState('paper')
    const wsRef = useRef(null)

    useEffect(() => {
        connectWebSocket()
        loadInitialData()

        return () => {
            if (wsRef.current) {
                wsRef.current.close()
            }
        }
    }, [])

    const connectWebSocket = () => {
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws/live`

        try {
            const ws = new WebSocket(wsUrl)
            wsRef.current = ws

            ws.onopen = () => {
                setWsConnected(true)
                console.log('WebSocket connected')
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)

                    if (data.type === 'tick') {
                        setPrice(data.price || 0)
                        setLastUpdate(new Date())

                        if (data.account) {
                            setStatus(prev => ({ ...prev, account: data.account }))
                        }

                        if (data.signals && data.signals.length > 0) {
                            setSignals(data.signals)
                        }

                        if (data.fibonacci) {
                            setFibonacci(data.fibonacci)
                        }
                    }
                } catch (err) {
                    console.error('WS parse error:', err)
                }
            }

            ws.onclose = () => {
                setWsConnected(false)
                console.log('WebSocket disconnected, reconnecting in 5s...')
                setTimeout(connectWebSocket, 5000)
            }

            ws.onerror = (err) => {
                console.error('WebSocket error:', err)
                setWsConnected(false)
            }
        } catch (err) {
            console.error('WebSocket connection failed:', err)
            setTimeout(connectWebSocket, 5000)
        }
    }

    const loadInitialData = async () => {
        try {
            const statusData = await api.get('/trading/status')
            setStatus(statusData)
            if (statusData.mode) {
                setTradingMode(statusData.mode)
            }

            const priceData = await api.get('/signals/price')
            if (priceData && priceData.price) {
                setPrice(priceData.price)
            }

            const fibData = await api.get('/signals/fibonacci')
            if (fibData && fibData.status === 'ok') {
                setFibonacci(fibData.levels)
            }
        } catch (err) {
            console.error('Initial load error:', err)
        }
    }

    const scanSignals = async () => {
        try {
            const result = await api.get('/signals/scan')
            if (result && result.signals) {
                setSignals(result.signals)
            }
        } catch (err) {
            console.error('Scan error:', err)
        }
    }

    const executeTrade = async (signal, action) => {
        if (!window.confirm(`${action.toUpperCase()} ${signal.symbol} at $${signal.entry_price}?`)) {
            return
        }

        try {
            const result = await api.post('/trading/execute', {
                signal_id: signal.id,
                action: action,
                entry_price: signal.entry_price,
                stop_loss: signal.stop_loss,
                take_profits: signal.take_profits
            })
            
            if (result.status === 'ok') {
                alert(`Trade ${action} executed successfully!`)
                const statusData = await api.get('/trading/status')
                setStatus(statusData)
            } else {
                alert(`Trade failed: ${result.msg || 'Unknown error'}`)
            }
        } catch (err) {
            console.error('Trade execution error:', err)
            alert(`Trade error: ${err.message}`)
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

    const formatTime = (date) => {
        if (!date) return '--'
        return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    }

    const getStrengthColor = (strength) => {
        switch (strength) {
            case 'SNIPER': return '#00ffcc'
            case 'STRONG': return '#00cc99'
            case 'MODERATE': return '#ffaa00'
            case 'WEAK': return '#ff5555'
            default: return '#888'
        }
    }

    return (
        <div className="dashboard">
            {/* Header Stats Row */}
            <div className="dashboard-header">
                <div className="glass-card stat-card">
                    <div className="stat-label">BTC/USDT</div>
                    <div className="stat-value price-value">
                        {formatPrice(price)}
                    </div>
                    <div className="stat-sub">
                        <span className={`ws-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
                            {wsConnected ? '● LIVE' : '○ OFFLINE'}
                        </span>
                        <span className="last-update">{formatTime(lastUpdate)}</span>
                    </div>
                </div>

                <div className="glass-card stat-card">
                    <div className="stat-label">Balance</div>
                    <div className="stat-value">
                        {formatPrice(status?.account?.balance || status?.account?.equity || 0)}
                    </div>
                    <div className="stat-sub">
                        <span className={`mode-badge mode-${tradingMode}`}>{tradingMode.toUpperCase()}</span>
                        <span className={`balance-source ${status?.balance_source === 'live' ? 'live' : status?.balance_source === 'fallback' ? 'warning' : ''}`}>
                            {status?.balance_source === 'live' ? '🟢 LIVE API' : status?.balance_source === 'fallback' ? '⚠️ FALLBACK' : '📄 PAPER'}
                        </span>
                    </div>
                    {status?.balance_warning && (
                        <div className="balance-warning">
                            ⚠️ {status.balance_warning}
                        </div>
                    )}
                </div>

                <div className="glass-card stat-card">
                    <div className="stat-label">P&L</div>
                    <div className={`stat-value ${(status?.account?.total_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                        {formatPrice(status?.account?.total_pnl || 0)}
                    </div>
                    <div className="stat-sub">
                        <span>Open: {status?.account?.open_count || 0}</span>
                        <span>Closed: {status?.account?.closed_count || 0}</span>
                    </div>
                </div>

                <div className="glass-card stat-card">
                    <div className="stat-label">Signals</div>
                    <div className="stat-value">{signals.length}</div>
                    <div className="stat-sub">
                        <button className="scan-btn" onClick={scanSignals}>🔍 Scan Now</button>
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="dashboard-grid">
                {/* Fibonacci Levels Panel */}
                <div className="glass-card fib-panel">
                    <h3 className="panel-title">📐 Fibonacci Levels</h3>

                    {fibonacci ? (
                        <div className="fib-levels-list">
                            <FibLevel label="Swing High (0.0)" price={fibonacci.level_0} current={price} type="boundary" />
                            <FibLevel label="23.6%" price={fibonacci.level_236} current={price} type="standard" />
                            <FibLevel label="38.2%" price={fibonacci.level_382} current={price} type="standard" />
                            <FibLevel label="50.0%" price={fibonacci.level_500} current={price} type="standard" />
                            <FibLevel label="61.8% (Golden Pocket)" price={fibonacci.level_618} current={price} type="golden" />
                            <FibLevel label="78.6%" price={fibonacci.level_786} current={price} type="entry" />
                            <div className="fib-separator" />
                            <FibLevel label="⭐ 88.2% (Primary Sniper)" price={fibonacci.level_882} current={price} type="sniper" />
                            <FibLevel label="⭐ 94.1% (Deep Value)" price={fibonacci.level_941} current={price} type="sniper" />
                            <div className="fib-separator" />
                            <FibLevel label="Swing Low (1.0)" price={fibonacci.swing_low} current={price} type="boundary" />
                        </div>
                    ) : (
                        <div className="no-data">Waiting for Fibonacci data...</div>
                    )}
                </div>

                {/* Signal Panel */}
                <div className="glass-card signal-panel">
                    <h3 className="panel-title">🎯 Active Signals</h3>

                    {signals.length > 0 ? (
                        <div className="signals-list">
                            {signals.map(signal => (
                                <div key={signal.id} className="signal-card">
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
                                            <span className="label">TPs:</span>
                                            <span className="value">
                                                {signal.take_profits.map((tp, i) => (
                                                    <span key={i}>{formatPrice(tp)}{i < signal.take_profits.length - 1 ? ', ' : ''}</span>
                                                ))}
                                            </span>
                                        </div>
                                        <div className="detail-row">
                                            <span className="label">CRV:</span>
                                            <span className="value">{signal.crv?.toFixed(2)}</span>
                                        </div>
                                    </div>

                                    <div className="signal-actions">
                                        <button 
                                            className="action-btn buy-btn"
                                            onClick={() => executeTrade(signal, 'buy')}
                                            disabled={tradingMode !== 'live'}
                                        >
                                            🟢 BUY
                                        </button>
                                        <button 
                                            className="action-btn sell-btn"
                                            onClick={() => executeTrade(signal, 'sell')}
                                            disabled={tradingMode !== 'live'}
                                        >
                                            🔴 SELL
                                        </button>
                                    </div>

                                    {tradingMode !== 'live' && (
                                        <div className="paper-mode-notice">
                                            Switch to Live Mode to execute trades
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="no-data">
                            No active signals. Click "Scan Now" to search for opportunities.
                        </div>
                    )}
                </div>
            </div>

            {/* History Panel */}
            <HistoryPanel />
        </div>
    )
}

// FibLevel Component
function FibLevel({ label, price, current, type }) {
    const proximity = current && price ? ((current - price) / price * 100).toFixed(3) : 0
    const isClose = Math.abs(proximity) < 0.5

    return (
        <div className={`fib-level ${type} ${isClose ? 'active' : ''}`}>
            <div className="fib-label">{label}</div>
            <div className="fib-price">${price?.toFixed(2)}</div>
            <div className="fib-proximity">{proximity > 0 ? '+' : ''}{proximity}%</div>
        </div>
    )
}
