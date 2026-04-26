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
        <>

            <div className="dashboard-header">
                <div className="glass-card stat-card">
                    <div className="stat-label">MARKET PRICE</div>
                    <div className="stat-value price-value">{formatPrice(price)}</div>
                    <div className="stat-sub">
                        <span className={`ws-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
                            {wsConnected ? '● NEURAL_LINK_OK' : '○ LINK_LOST'}
                        </span>
                        <span className="last-update">{formatTime(lastUpdate)}</span>
                    </div>
                </div>

                <div className="glass-card stat-card">
                    <div className="stat-label">EQUITY // BALANCE</div>
                    <div className="stat-value">
                        {formatPrice(status?.account?.balance || status?.account?.equity || 0)}
                    </div>
                    <div className="stat-sub">
                        <span className={`badge ${tradingMode === 'live' ? 'badge-live' : 'badge-paper'}`}>{tradingMode}</span>
                        <span className="uppercase text-[9px] tracking-widest font-black">
                            {status?.balance_source === 'live' ? 'API_VERIFIED' : 'PAPER_SIM'}
                        </span>
                    </div>
                </div>

                <div className="glass-card stat-card">
                    <div className="stat-label">PROFIT & LOSS</div>
                    <div className={`stat-value ${(status?.account?.total_pnl || 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                        {formatPrice(status?.account?.total_pnl || 0)}
                    </div>
                    <div className="stat-sub">
                        <span>OPEN: {status?.account?.open_count || 0}</span>
                        <span>CLOSED: {status?.account?.closed_count || 0}</span>
                    </div>
                </div>

                <div className="glass-card stat-card">
                    <div className="stat-label">ACTIVE SIGNALS</div>
                    <div className="stat-value text-blue">{signals.length}</div>
                    <div className="stat-sub">
                        <span className="uppercase text-[9px] tracking-widest font-black">SQUAWK_BOX_ACTIVE</span>
                    </div>
                </div>
            </div>

            <div className="dashboard-grid">
                <div className="glass-card fib-panel">
                    <h3 className="panel-title">
                        <span>FIBONACCI_LEVELS</span>
                        <span className="text-[10px] text-teal opacity-50">AUTO_SCAN</span>
                    </h3>

                    {fibonacci ? (
                        <div className="fib-levels-list">
                            <FibLevel label="SWING_HIGH" price={fibonacci.level_0} current={price} type="boundary" />
                            <FibLevel label="0.236_LEVEL" price={fibonacci.level_236} current={price} type="standard" />
                            <FibLevel label="0.382_LEVEL" price={fibonacci.level_382} current={price} type="standard" />
                            <FibLevel label="0.500_LEVEL" price={fibonacci.level_500} current={price} type="standard" />
                            <FibLevel label="0.618_GOLDEN" price={fibonacci.level_618} current={price} type="golden" />
                            <FibLevel label="0.786_DEEP" price={fibonacci.level_786} current={price} type="entry" />
                            <div className="h-px bg-white/5 my-2" />
                            <FibLevel label="0.882_SNIPER" price={fibonacci.level_882} current={price} type="sniper" />
                            <FibLevel label="0.941_ALPHA" price={fibonacci.level_941} current={price} type="sniper" />
                            <div className="h-px bg-white/5 my-2" />
                            <FibLevel label="SWING_LOW" price={fibonacci.swing_low} current={price} type="boundary" />
                        </div>
                    ) : (
                        <div className="text-text-faint text-center py-12 font-mono text-xs uppercase tracking-widest animate-pulse">
                            CALIBRATING_LEVELS...
                        </div>
                    )}
                </div>

                <div className="glass-card signal-panel">
                    <h3 className="panel-title">
                        <span>NEURAL_SIGNALS</span>
                        <span className="text-[10px] text-blue opacity-50">READY</span>
                    </h3>

                    {signals.length > 0 ? (
                        <div className="signals-list">
                            {signals.map(signal => (
                                <div key={signal.id} className="signal-card group">
                                    <div className="signal-header border-b border-white/5 pb-3 mb-4">
                                        <span className="font-black text-white tracking-tighter">{signal.symbol}</span>
                                        <span 
                                            className="signal-crv ml-auto"
                                            style={{ color: getStrengthColor(signal.strength) }}
                                        >
                                            {signal.strength} // CRV {signal.crv?.toFixed(2)}
                                        </span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4 mb-6">
                                        <div className="flex flex-col">
                                            <span className="text-[9px] text-text-faint font-black uppercase tracking-widest">Entry</span>
                                            <span className="font-mono text-xs text-white">{formatPrice(signal.entry_price)}</span>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-[9px] text-text-faint font-black uppercase tracking-widest">Risk</span>
                                            <span className="font-mono text-xs text-red-400">{formatPrice(signal.stop_loss)}</span>
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        <button 
                                            className="btn btn-primary flex-1 !py-3 !text-[10px]"
                                            onClick={() => executeTrade(signal, 'buy')}
                                            disabled={tradingMode !== 'live'}
                                        >
                                            EXECUTE_LONG
                                        </button>
                                        <button 
                                            className="btn flex-1 !py-3 !text-[10px] border-red-500/20 text-red-400 hover:bg-red-500/10"
                                            onClick={() => executeTrade(signal, 'sell')}
                                            disabled={tradingMode !== 'live'}
                                        >
                                            EXECUTE_SHORT
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-text-faint text-center py-12 font-mono text-xs uppercase tracking-widest">
                            NO_CONFLUENCE_DETECTED
                        </div>
                    )}
                </div>
            </div>
            
            <HistoryPanel />
        </>
    )
}

function FibLevel({ label, price, current, type }) {
    const proximity = current && price ? ((current - price) / price * 100).toFixed(3) : 0
    const isAtLevel = Math.abs(proximity) < 0.05

    return (
        <div className={`fib-row fib-row-${type} ${isAtLevel ? 'fib-at-level' : ''}`}>
            <div className="fib-label">{label}</div>
            <div className="fib-price font-mono">{price?.toFixed(2)}</div>
            <div className={`fib-proximity font-mono ${proximity > 0 ? 'above' : 'below'}`}>
                {proximity > 0 ? '+' : ''}{proximity}%
            </div>
        </div>
    )
}
