// frontend/src/components/ControlPanel.jsx
import React from 'react'
import './ControlPanel.css'

export default function ControlPanel({ settings, account, liveData, onSettingsUpdate, onReset }) {
    const price = liveData?.price || 0

    return (
        <div className="glass-card control-panel">
            <h3>⚙️ Control Center</h3>

            <div className="stats-grid">
                <div className="stat">
                    <span className="stat-label">Price</span>
                    <span className="stat-value mono">${price.toLocaleString()}</span>
                </div>
                <div className="stat">
                    <span className="stat-label">Balance</span>
                    <span className="stat-value mono">
                        ${account?.balance?.toFixed(2) || '0.00'}
                    </span>
                </div>
                <div className="stat">
                    <span className="stat-label">Equity</span>
                    <span className="stat-value mono">
                        ${account?.equity?.toFixed(2) || '0.00'}
                    </span>
                </div>
                <div className="stat">
                    <span className="stat-label">PnL</span>
                    <span className={`stat-value mono ${(account?.total_pnl || 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                        ${account?.total_pnl?.toFixed(2) || '0.00'}
                    </span>
                </div>
            </div>

            <div className="controls">
                <label>
                    <span>Timeframe</span>
                    <select
                        value={settings?.timeframe || '15m'}
                        onChange={e => onSettingsUpdate({ timeframe: e.target.value })}
                    >
                        <option value="15m">15 min</option>
                        <option value="30m">30 min</option>
                        <option value="60m">60 min</option>
                    </select>
                </label>

                <label>
                    <span>Mode</span>
                    <select
                        value={settings?.trading_mode || 'paper'}
                        onChange={e => onSettingsUpdate({ trading_mode: e.target.value })}
                    >
                        <option value="paper">📝 Paper</option>
                        <option value="live">🔴 Live</option>
                    </select>
                </label>
            </div>

            <div className="open-positions">
                <h4>Open Positions: {account?.open_positions?.length || 0}</h4>
                {account?.open_positions?.map((t, i) => (
                    <div key={i} className="position-row">
                        <span className="badge badge-strong">{t.fib_level}</span>
                        <span className="mono">${t.entry_price}</span>
                        <span className={`mono ${((price - t.entry_price) * t.position_size) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                            {((price - t.entry_price) * t.position_size).toFixed(2)}
                        </span>
                    </div>
                ))}
            </div>

            <button className="btn btn-danger" onClick={onReset}>Reset Account</button>
        </div>
    )
}
