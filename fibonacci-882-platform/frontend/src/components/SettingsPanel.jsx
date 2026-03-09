// frontend/src/components/SettingsPanel.jsx
import React, { useState, useEffect } from 'react'
import { settings as settingsApi } from '../utils/api'
import './SettingsPanel.css'

export default function SettingsPanel({ onClose }) {
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [toast, setToast] = useState(null)
    const [leverage, setLeverage] = useState(20)
    const [marginMode, setMarginMode] = useState('ISOLATED')
    
    const [formData, setFormData] = useState({
        binance_futures: { api_key: '', api_secret: '', testnet: true },
        bitunix: { api_key: '', api_secret: '', trading_mode: 'paper' },
        websocket: { primary_uri: '', fallback_uri: '' },
        telegram: { bot_token: '', chat_id: '', enabled: false, notify_signals: true, notify_trades: true, notify_errors: true, daily_summary: true },
        trading: { symbol: 'BTCUSDT', timeframe: '15m', risk_pct: 2.0, leverage: 20, margin_mode: 'ISOLATED' },
        backtest: { candles: 500 },
        scanner: { enabled: true, interval: 60 }
    })

    useEffect(() => { loadSettings() }, [])

    const loadSettings = async () => {
        setLoading(true)
        try {
            const data = await settingsApi.get()
            if (data.status === 'ok' && data.data) {
                setFormData(prev => ({
                    binance_futures: { ...prev.binance_futures, ...data.data.binance_futures },
                    bitunix: { ...prev.bitunix, ...data.data.bitunix },
                    websocket: { ...prev.websocket, ...data.data.websocket },
                    telegram: { ...prev.telegram, ...data.data.telegram },
                    trading: { ...prev.trading, ...data.data.trading },
                    backtest: { ...prev.backtest, ...data.data.backtest },
                    scanner: { ...prev.scanner, ...data.data.scanner }
                }))
                if (data.data.trading?.leverage) setLeverage(data.data.trading.leverage)
                if (data.data.trading?.margin_mode) setMarginMode(data.data.trading.margin_mode)
            }
        } catch (err) { console.error('Load error:', err) }
        finally { setLoading(false) }
    }

    const handleSave = async (section) => {
        setSaving(true)
        try {
            let data = { [section]: formData[section] }
            if (section === 'binance_futures') {
                if (!formData.binance_futures.api_key || formData.binance_futures.api_key.includes('...')) delete data.binance_futures.api_key
                if (!formData.binance_futures.api_secret || formData.binance_futures.api_secret.includes('...')) delete data.binance_futures.api_secret
            }
            if (section === 'telegram' && (!formData.telegram.bot_token || formData.telegram.bot_token.includes('...'))) delete data.telegram.bot_token
            const result = await settingsApi.save(data)
            if (result.status === 'ok') { showToast('✅ Settings saved!', 'success'); await loadSettings() }
            else showToast('❌ Save failed', 'error')
        } catch (err) { showToast('❌ Save error', 'error') }
        finally { setSaving(false) }
    }

    const handleTestBinance = async () => {
        setSaving(true)
        try {
            await handleSave('binance_futures')
            await new Promise(r => setTimeout(r, 500))
            const response = await fetch('/api/trading/status', { headers: { 'Content-Type': 'application/json' } })
            if (!response.ok) throw new Error('Server response: ' + response.status)
            const data = await response.json()
            if (data && data.account && data.account.balance) {
                const bal = parseFloat(data.account.balance)
                if (data.balance_source === 'live' || data.balance_source === 'paper')
                    showToast('✅ Connected! 

    const handleTestTelegram = async () => {
        setSaving(true)
        try {
            const result = await settingsApi.testTelegram()
            if (result.status === 'ok') showToast('✅ Test message sent!', 'success')
            else showToast(result.msg || '❌ Failed', 'error')
        } catch (err) { showToast('❌ Test error', 'error') }
        finally { setSaving(false) }
    }

    const handleSetLeverage = async () => {
        if (leverage < 1 || leverage > 125) { showToast('❌ 1-125 only', 'error'); return }
        try {
            const response = await fetch(`/api/trading/leverage?symbol=${formData.trading.symbol}&leverage=${leverage}`, { method: 'POST' })
            const data = await response.json()
            showToast(data.status === 'ok' ? `✅ ${data.leverage}x set` : '❌ Failed', data.status === 'ok' ? 'success' : 'error')
        } catch (err) { showToast('❌ Error', 'error') }
    }

    const handleSetMarginMode = async (mode) => {
        try {
            const response = await fetch(`/api/trading/margin-mode?symbol=${formData.trading.symbol}&mode=${mode}`, { method: 'POST' })
            const data = await response.json()
            if (data.status === 'ok') { showToast(`✅ ${mode} set`, 'success'); setMarginMode(mode) }
            else showToast('❌ Failed', 'error')
        } catch (err) { showToast('❌ Error', 'error') }
    }

    const handleReset = async () => {
        if (!window.confirm('Reset all settings?')) return
        const defaults = { binance_futures: { api_key: '', api_secret: '', testnet: true }, telegram: { enabled: false }, trading: { symbol: 'BTCUSDT', timeframe: '15m' }, backtest: { candles: 500 }, scanner: { enabled: true, interval: 60 } }
        setFormData(prev => ({ ...prev, ...defaults }))
        await settingsApi.save(defaults)
        showToast('✅ Reset to defaults', 'success')
    }

    const showToast = (message, type) => { setToast({ message, type }); setTimeout(() => setToast(null), 3000) }
    const updateFormData = (section, field, value) => setFormData(prev => ({ ...prev, [section]: { ...prev[section], [field]: value } }))

    if (loading) return <div className="settings-overlay" onClick={onClose}><div className="settings-panel loading">Loading...</div></div>

    return (
        <div className="settings-overlay" onClick={onClose}>
            <div className="settings-panel" onClick={e => e.stopPropagation()}>
                <div className="settings-header"><h2>⚙️ Settings</h2><button className="close-btn" onClick={onClose}>✕</button></div>
                <div className="settings-content">
                    {/* Binance Futures */}
                    <section className="settings-section">
                        <h3>🔷 Binance Futures</h3>
                        <div className="form-group"><label>API Key</label><input type="text" value={formData.binance_futures?.api_key || ''} onChange={e => updateFormData('binance_futures', 'api_key', e.target.value)} placeholder="Enter API Key"/></div>
                        <div className="form-group"><label>Secret Key</label><input type="password" value={formData.binance_futures?.api_secret || ''} onChange={e => updateFormData('binance_futures', 'api_secret', e.target.value)} placeholder="Enter Secret Key"/></div>
                        <div className="toggle-group"><label className="toggle-label"><input type="checkbox" checked={formData.binance_futures?.testnet} onChange={e => updateFormData('binance_futures', 'testnet', e.target.checked)}/><span className="toggle-text">🧪 Use Testnet</span></label></div>
                        <div className="button-row"><button className="test-btn" onClick={handleTestBinance} disabled={saving}>🧪 Test</button><button className="save-btn" onClick={() => handleSave('binance_futures')} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button></div>
                        <div className="advanced-settings"><h4>⚙️ Trading Settings</h4>
                            <div className="form-group"><label>Leverage (1-125x)</label><div className="leverage-control"><input type="number" min="1" max="125" value={leverage} onChange={e => setLeverage(parseInt(e.target.value))} className="leverage-input"/><button className="action-btn" onClick={handleSetLeverage} disabled={saving}>Set</button></div></div>
                            <div className="form-group"><label>Margin Mode</label><div className="margin-mode-buttons"><button className={`mode-btn ${marginMode === 'ISOLATED' ? 'active' : ''}`} onClick={() => handleSetMarginMode('ISOLATED')} disabled={saving}>ISOLATED</button><button className={`mode-btn ${marginMode === 'CROSSED' ? 'active' : ''}`} onClick={() => handleSetMarginMode('CROSSED')} disabled={saving}>CROSSED</button></div></div>
                        </div>
                    </section>

                    {/* Telegram */}
                    <section className="settings-section">
                        <h3>📱 Telegram Notifications</h3>
                        <div className="form-group"><label>Bot Token</label><input type="text" value={formData.telegram?.bot_token || ''} onChange={e => updateFormData('telegram', 'bot_token', e.target.value)} placeholder="Enter Bot Token"/></div>
                        <div className="form-group"><label>Chat ID</label><input type="text" value={formData.telegram?.chat_id || ''} onChange={e => updateFormData('telegram', 'chat_id', e.target.value)} placeholder="Enter Chat ID"/></div>
                        <div className="toggle-group"><label className="toggle-label"><input type="checkbox" checked={formData.telegram?.enabled} onChange={e => updateFormData('telegram', 'enabled', e.target.checked)}/><span className="toggle-text">Enable Telegram</span></label></div>
                        <div className="checkbox-group">
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.notify_signals} onChange={e => updateFormData('telegram', 'notify_signals', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Notify Signals</span></label>
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.notify_trades} onChange={e => updateFormData('telegram', 'notify_trades', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Notify Trades</span></label>
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.notify_errors} onChange={e => updateFormData('telegram', 'notify_errors', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Notify Errors</span></label>
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.daily_summary} onChange={e => updateFormData('telegram', 'daily_summary', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Daily Summary</span></label>
                        </div>
                        <div className="button-row"><button className="test-btn" onClick={handleTestTelegram} disabled={saving || !formData.telegram?.enabled}>Test Connection</button><button className="save-btn" onClick={() => handleSave('telegram')} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button></div>
                    </section>

                    {/* Backtest */}
                    <section className="settings-section">
                        <h3>📈 Backtest Configuration</h3>
                        <div className="form-group"><label>Candle Count: {formData.backtest?.candles || 500}</label><input type="range" min="100" max="1000" step="50" value={formData.backtest?.candles || 500} onChange={e => updateFormData('backtest', 'candles', parseInt(e.target.value))}/><div className="range-labels"><span>100</span><span>1000</span></div></div>
                        <button className="save-btn" onClick={() => handleSave('backtest')} disabled={saving}>{saving ? 'Saving...' : 'Save Backtest Settings'}</button>
                    </section>

                    {/* Scanner */}
                    <section className="settings-section">
                        <h3>🔍 Scanner Settings</h3>
                        <div className="toggle-group"><label className="toggle-label"><input type="checkbox" checked={formData.scanner?.enabled} onChange={e => updateFormData('scanner', 'enabled', e.target.checked)}/><span className="toggle-text">Enable Scanner</span></label></div>
                        <div className="form-group"><label>Scan Interval (seconds)</label><input type="number" min="30" max="300" value={formData.scanner?.interval || 60} onChange={e => updateFormData('scanner', 'interval', parseInt(e.target.value))}/></div>
                        <button className="save-btn" onClick={() => handleSave('scanner')} disabled={saving}>{saving ? 'Saving...' : 'Save Scanner Settings'}</button>
                    </section>

                    {/* Trading */}
                    <section className="settings-section">
                        <h3>💹 Trading Configuration</h3>
                        <div className="form-group"><label>Symbol</label><input type="text" value={formData.trading?.symbol || 'BTCUSDT'} onChange={e => updateFormData('trading', 'symbol', e.target.value)}/></div>
                        <div className="form-group"><label>Timeframe</label><select value={formData.trading?.timeframe || '15m'} onChange={e => updateFormData('trading', 'timeframe', e.target.value)}><option value="5m">5m</option><option value="15m">15m</option><option value="30m">30m</option><option value="1h">1h</option></select></div>
                        <div className="form-group"><label>Risk per Trade (%)</label><input type="number" min="0.5" max="5" step="0.5" value={formData.trading?.risk_pct || 2.0} onChange={e => updateFormData('trading', 'risk_pct', parseFloat(e.target.value))}/></div>
                        <button className="save-btn" onClick={() => handleSave('trading')} disabled={saving}>{saving ? 'Saving...' : 'Save Trading Settings'}</button>
                    </section>

                    <button className="reset-btn" onClick={handleReset}>♻️ Reset to Defaults</button>
                </div>
                {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
            </div>
        </div>
    )
}
 + bal.toFixed(2), 'success')
                else if (data.balance_warning)
                    showToast('⚠️ ' + data.balance_warning, 'warning')
                else
                    showToast('❌ Connection failed', 'error')
            } else {
                showToast('❌ Invalid server response', 'error')
            }
        } catch (err) {
            console.error('Test error:', err)
            showToast('❌ ' + err.message, 'error')
        } finally { setSaving(false) }
    }

    const handleTestTelegram = async () => {
        setSaving(true)
        try {
            const result = await settingsApi.testTelegram()
            if (result.status === 'ok') showToast('✅ Test message sent!', 'success')
            else showToast(result.msg || '❌ Failed', 'error')
        } catch (err) { showToast('❌ Test error', 'error') }
        finally { setSaving(false) }
    }

    const handleSetLeverage = async () => {
        if (leverage < 1 || leverage > 125) { showToast('❌ 1-125 only', 'error'); return }
        try {
            const response = await fetch(`/api/trading/leverage?symbol=${formData.trading.symbol}&leverage=${leverage}`, { method: 'POST' })
            const data = await response.json()
            showToast(data.status === 'ok' ? `✅ ${data.leverage}x set` : '❌ Failed', data.status === 'ok' ? 'success' : 'error')
        } catch (err) { showToast('❌ Error', 'error') }
    }

    const handleSetMarginMode = async (mode) => {
        try {
            const response = await fetch(`/api/trading/margin-mode?symbol=${formData.trading.symbol}&mode=${mode}`, { method: 'POST' })
            const data = await response.json()
            if (data.status === 'ok') { showToast(`✅ ${mode} set`, 'success'); setMarginMode(mode) }
            else showToast('❌ Failed', 'error')
        } catch (err) { showToast('❌ Error', 'error') }
    }

    const handleReset = async () => {
        if (!window.confirm('Reset all settings?')) return
        const defaults = { binance_futures: { api_key: '', api_secret: '', testnet: true }, telegram: { enabled: false }, trading: { symbol: 'BTCUSDT', timeframe: '15m' }, backtest: { candles: 500 }, scanner: { enabled: true, interval: 60 } }
        setFormData(prev => ({ ...prev, ...defaults }))
        await settingsApi.save(defaults)
        showToast('✅ Reset to defaults', 'success')
    }

    const showToast = (message, type) => { setToast({ message, type }); setTimeout(() => setToast(null), 3000) }
    const updateFormData = (section, field, value) => setFormData(prev => ({ ...prev, [section]: { ...prev[section], [field]: value } }))

    if (loading) return <div className="settings-overlay" onClick={onClose}><div className="settings-panel loading">Loading...</div></div>

    return (
        <div className="settings-overlay" onClick={onClose}>
            <div className="settings-panel" onClick={e => e.stopPropagation()}>
                <div className="settings-header"><h2>⚙️ Settings</h2><button className="close-btn" onClick={onClose}>✕</button></div>
                <div className="settings-content">
                    {/* Binance Futures */}
                    <section className="settings-section">
                        <h3>🔷 Binance Futures</h3>
                        <div className="form-group"><label>API Key</label><input type="text" value={formData.binance_futures?.api_key || ''} onChange={e => updateFormData('binance_futures', 'api_key', e.target.value)} placeholder="Enter API Key"/></div>
                        <div className="form-group"><label>Secret Key</label><input type="password" value={formData.binance_futures?.api_secret || ''} onChange={e => updateFormData('binance_futures', 'api_secret', e.target.value)} placeholder="Enter Secret Key"/></div>
                        <div className="toggle-group"><label className="toggle-label"><input type="checkbox" checked={formData.binance_futures?.testnet} onChange={e => updateFormData('binance_futures', 'testnet', e.target.checked)}/><span className="toggle-text">🧪 Use Testnet</span></label></div>
                        <div className="button-row"><button className="test-btn" onClick={handleTestBinance} disabled={saving}>🧪 Test</button><button className="save-btn" onClick={() => handleSave('binance_futures')} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button></div>
                        <div className="advanced-settings"><h4>⚙️ Trading Settings</h4>
                            <div className="form-group"><label>Leverage (1-125x)</label><div className="leverage-control"><input type="number" min="1" max="125" value={leverage} onChange={e => setLeverage(parseInt(e.target.value))} className="leverage-input"/><button className="action-btn" onClick={handleSetLeverage} disabled={saving}>Set</button></div></div>
                            <div className="form-group"><label>Margin Mode</label><div className="margin-mode-buttons"><button className={`mode-btn ${marginMode === 'ISOLATED' ? 'active' : ''}`} onClick={() => handleSetMarginMode('ISOLATED')} disabled={saving}>ISOLATED</button><button className={`mode-btn ${marginMode === 'CROSSED' ? 'active' : ''}`} onClick={() => handleSetMarginMode('CROSSED')} disabled={saving}>CROSSED</button></div></div>
                        </div>
                    </section>

                    {/* Telegram */}
                    <section className="settings-section">
                        <h3>📱 Telegram Notifications</h3>
                        <div className="form-group"><label>Bot Token</label><input type="text" value={formData.telegram?.bot_token || ''} onChange={e => updateFormData('telegram', 'bot_token', e.target.value)} placeholder="Enter Bot Token"/></div>
                        <div className="form-group"><label>Chat ID</label><input type="text" value={formData.telegram?.chat_id || ''} onChange={e => updateFormData('telegram', 'chat_id', e.target.value)} placeholder="Enter Chat ID"/></div>
                        <div className="toggle-group"><label className="toggle-label"><input type="checkbox" checked={formData.telegram?.enabled} onChange={e => updateFormData('telegram', 'enabled', e.target.checked)}/><span className="toggle-text">Enable Telegram</span></label></div>
                        <div className="checkbox-group">
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.notify_signals} onChange={e => updateFormData('telegram', 'notify_signals', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Notify Signals</span></label>
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.notify_trades} onChange={e => updateFormData('telegram', 'notify_trades', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Notify Trades</span></label>
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.notify_errors} onChange={e => updateFormData('telegram', 'notify_errors', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Notify Errors</span></label>
                            <label className="checkbox-label"><input type="checkbox" checked={formData.telegram?.daily_summary} onChange={e => updateFormData('telegram', 'daily_summary', e.target.checked)} disabled={!formData.telegram?.enabled}/><span>Daily Summary</span></label>
                        </div>
                        <div className="button-row"><button className="test-btn" onClick={handleTestTelegram} disabled={saving || !formData.telegram?.enabled}>Test Connection</button><button className="save-btn" onClick={() => handleSave('telegram')} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button></div>
                    </section>

                    {/* Backtest */}
                    <section className="settings-section">
                        <h3>📈 Backtest Configuration</h3>
                        <div className="form-group"><label>Candle Count: {formData.backtest?.candles || 500}</label><input type="range" min="100" max="1000" step="50" value={formData.backtest?.candles || 500} onChange={e => updateFormData('backtest', 'candles', parseInt(e.target.value))}/><div className="range-labels"><span>100</span><span>1000</span></div></div>
                        <button className="save-btn" onClick={() => handleSave('backtest')} disabled={saving}>{saving ? 'Saving...' : 'Save Backtest Settings'}</button>
                    </section>

                    {/* Scanner */}
                    <section className="settings-section">
                        <h3>🔍 Scanner Settings</h3>
                        <div className="toggle-group"><label className="toggle-label"><input type="checkbox" checked={formData.scanner?.enabled} onChange={e => updateFormData('scanner', 'enabled', e.target.checked)}/><span className="toggle-text">Enable Scanner</span></label></div>
                        <div className="form-group"><label>Scan Interval (seconds)</label><input type="number" min="30" max="300" value={formData.scanner?.interval || 60} onChange={e => updateFormData('scanner', 'interval', parseInt(e.target.value))}/></div>
                        <button className="save-btn" onClick={() => handleSave('scanner')} disabled={saving}>{saving ? 'Saving...' : 'Save Scanner Settings'}</button>
                    </section>

                    {/* Trading */}
                    <section className="settings-section">
                        <h3>💹 Trading Configuration</h3>
                        <div className="form-group"><label>Symbol</label><input type="text" value={formData.trading?.symbol || 'BTCUSDT'} onChange={e => updateFormData('trading', 'symbol', e.target.value)}/></div>
                        <div className="form-group"><label>Timeframe</label><select value={formData.trading?.timeframe || '15m'} onChange={e => updateFormData('trading', 'timeframe', e.target.value)}><option value="5m">5m</option><option value="15m">15m</option><option value="30m">30m</option><option value="1h">1h</option></select></div>
                        <div className="form-group"><label>Risk per Trade (%)</label><input type="number" min="0.5" max="5" step="0.5" value={formData.trading?.risk_pct || 2.0} onChange={e => updateFormData('trading', 'risk_pct', parseFloat(e.target.value))}/></div>
                        <button className="save-btn" onClick={() => handleSave('trading')} disabled={saving}>{saving ? 'Saving...' : 'Save Trading Settings'}</button>
                    </section>

                    <button className="reset-btn" onClick={handleReset}>♻️ Reset to Defaults</button>
                </div>
                {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
            </div>
        </div>
    )
}
