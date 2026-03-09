// frontend/src/components/BacktestPanel.jsx
import React, { useState } from 'react'
import { api } from '../utils/api'
import './BacktestPanel.css'

export default function BacktestPanel() {
    const [running, setRunning] = useState(false)
    const [result, setResult] = useState(null)
    const [config, setConfig] = useState({
        symbol: 'BTCUSDT',
        timeframe: '15m',
        initial_capital: 10000,
        fib_levels: ['0.882', '0.941'],
        require_confluence: 2,
    })

    const runBacktest = async () => {
        setRunning(true)
        try {
            const res = await api.post('/backtest/run', config)
            setResult(res)
        } catch (err) {
            console.error(err)
        }
        setRunning(false)
    }

    const toggleLevel = (level) => {
        setConfig(prev => ({
            ...prev,
            fib_levels: prev.fib_levels.includes(level)
                ? prev.fib_levels.filter(l => l !== level)
                : [...prev.fib_levels, level]
        }))
    }

    return (
        <div className="backtest-layout">
            <div className="glass-card backtest-config">
                <h3>🧪 Backtest Configuration</h3>

                <label>
                    <span>Timeframe</span>
                    <select value={config.timeframe} onChange={e => setConfig({ ...config, timeframe: e.target.value })}>
                        <option value="15m">15 min</option>
                        <option value="30m">30 min</option>
                        <option value="60m">60 min</option>
                    </select>
                </label>

                <label>
                    <span>Capital ($)</span>
                    <input
                        type="number"
                        value={config.initial_capital}
                        onChange={e => setConfig({ ...config, initial_capital: Number(e.target.value) })}
                    />
                </label>

                <label>
                    <span>Min Confluence</span>
                    <select
                        value={config.require_confluence}
                        onChange={e => setConfig({ ...config, require_confluence: Number(e.target.value) })}
                    >
                        <option value={1}>1 (Aggressive)</option>
                        <option value={2}>2 (Balanced)</option>
                        <option value={3}>3 (Conservative)</option>
                        <option value={4}>4 (Sniper Only)</option>
                    </select>
                </label>

                <div className="fib-toggles">
                    <span>Fibonacci Levels:</span>
                    <div className="toggle-row">
                        {['0.786', '0.882', '0.941'].map(level => (
                            <label key={level} className="toggle-label">
                                <input
                                    type="checkbox"
                                    checked={config.fib_levels.includes(level)}
                                    onChange={() => toggleLevel(level)}
                                />
                                <span className={`toggle-chip ${config.fib_levels.includes(level) ? 'toggle-active' : ''}`}>
                                    {level}
                                </span>
                            </label>
                        ))}
                    </div>
                </div>

                <button className="btn btn-primary" onClick={runBacktest} disabled={running}>
                    {running ? '⏳ Running Backtest...' : '▶️ Run Backtest'}
                </button>
            </div>

            {result && (
                <div className="glass-card backtest-results">
                    <h3>📊 Backtest Results</h3>

                    <div className="result-grid">
                        <div className="result-card">
                            <span className="result-label">Total Trades</span>
                            <span className="result-value mono">{result.total_trades}</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Win Rate</span>
                            <span className={`result-value mono ${result.win_rate >= 50 ? 'pnl-positive' : 'pnl-negative'}`}>
                                {result.win_rate?.toFixed(1)}%
                            </span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Total PnL</span>
                            <span className={`result-value mono ${result.total_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                ${result.total_pnl?.toFixed(2)}
                            </span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Final Balance</span>
                            <span className="result-value mono">${result.final_balance?.toFixed(2)}</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Return</span>
                            <span className={`result-value mono ${result.return_pct >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                {result.return_pct?.toFixed(2)}%
                            </span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Avg CRV</span>
                            <span className="result-value mono">{result.avg_crv?.toFixed(2)}</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Best Trade</span>
                            <span className="result-value mono pnl-positive">${result.best_trade?.toFixed(2)}</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Worst Trade</span>
                            <span className="result-value mono pnl-negative">${result.worst_trade?.toFixed(2)}</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Max Drawdown</span>
                            <span className="result-value mono pnl-negative">{result.max_drawdown?.toFixed(2)}%</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Profit Factor</span>
                            <span className="result-value mono">{result.profit_factor?.toFixed(2)}</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Wins</span>
                            <span className="result-value mono pnl-positive">{result.winning_trades}</span>
                        </div>
                        <div className="result-card">
                            <span className="result-label">Losses</span>
                            <span className="result-value mono pnl-negative">{result.losing_trades}</span>
                        </div>
                    </div>

                    {/* Equity Curve */}
                    {result.equity_curve && result.equity_curve.length > 0 && (
                        <div className="equity-curve-section">
                            <h4>Equity Curve</h4>
                            <EquityCurve data={result.equity_curve} initial={config.initial_capital} />
                        </div>
                    )}

                    {/* Trade List */}
                    {result.trades && result.trades.length > 0 && (
                        <div className="backtest-trades">
                            <h4>Trade History ({result.trades.length})</h4>
                            <div className="trade-table-wrapper">
                                <table className="trade-table">
                                    <thead>
                                        <tr>
                                            <th>#</th>
                                            <th>Fib Level</th>
                                            <th>Entry</th>
                                            <th>Exit</th>
                                            <th>PnL</th>
                                            <th>Result</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.trades.map((t, i) => (
                                            <tr key={i}>
                                                <td>{i + 1}</td>
                                                <td><span className="badge badge-strong">{t.fib_level}</span></td>
                                                <td className="mono">${t.entry_price?.toFixed(2)}</td>
                                                <td className="mono">${t.exit_price?.toFixed(2)}</td>
                                                <td className={`mono ${t.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                                    ${t.pnl?.toFixed(2)}
                                                </td>
                                                <td>
                                                    <span className={`badge ${t.pnl >= 0 ? 'badge-strong' : 'badge-weak'}`}>
                                                        {t.pnl >= 0 ? 'WIN' : 'LOSS'}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}


function EquityCurve({ data, initial }) {
    const canvasRef = React.useRef(null)

    React.useEffect(() => {
        if (!canvasRef.current || !data.length) return

        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        const rect = canvas.getBoundingClientRect()
        canvas.width = rect.width * 2
        canvas.height = rect.height * 2
        ctx.scale(2, 2)

        const w = rect.width
        const h = rect.height
        const pad = { top: 10, right: 10, bottom: 10, left: 10 }

        const values = [initial, ...data]
        const min = Math.min(...values) * 0.995
        const max = Math.max(...values) * 1.005

        const toX = (i) => pad.left + (i / (values.length - 1)) * (w - pad.left - pad.right)
        const toY = (v) => pad.top + ((max - v) / (max - min)) * (h - pad.top - pad.bottom)

        // Background
        ctx.fillStyle = 'rgba(0,0,0,0.3)'
        ctx.fillRect(0, 0, w, h)

        // Baseline
        ctx.strokeStyle = 'rgba(100,116,139,0.3)'
        ctx.lineWidth = 1
        ctx.setLineDash([4, 4])
        ctx.beginPath()
        ctx.moveTo(pad.left, toY(initial))
        ctx.lineTo(w - pad.right, toY(initial))
        ctx.stroke()
        ctx.setLineDash([])

        // Gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, h)
        const lastVal = values[values.length - 1]
        if (lastVal >= initial) {
            gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)')
            gradient.addColorStop(1, 'rgba(16, 185, 129, 0)')
            ctx.strokeStyle = '#10b981'
        } else {
            gradient.addColorStop(0, 'rgba(239, 68, 68, 0.3)')
            gradient.addColorStop(1, 'rgba(239, 68, 68, 0)')
            ctx.strokeStyle = '#ef4444'
        }

        // Line
        ctx.lineWidth = 2
        ctx.beginPath()
        values.forEach((v, i) => {
            const x = toX(i)
            const y = toY(v)
            if (i === 0) ctx.moveTo(x, y)
            else ctx.lineTo(x, y)
        })
        ctx.stroke()

        // Fill
        ctx.lineTo(toX(values.length - 1), h - pad.bottom)
        ctx.lineTo(pad.left, h - pad.bottom)
        ctx.closePath()
        ctx.fillStyle = gradient
        ctx.fill()

    }, [data, initial])

    return <canvas ref={canvasRef} className="equity-canvas" />
}
