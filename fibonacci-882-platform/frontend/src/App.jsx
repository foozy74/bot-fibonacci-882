// frontend/src/App.jsx
import React, { useState, useEffect } from 'react'
import Dashboard from './components/Dashboard'
import SettingsPanel from './components/SettingsPanel'
import HelpPanel from './components/HelpPanel'
import { api } from './utils/api'
import logo from './assets/logo.svg'
import './App.css'

export default function App() {
    const [settingsOpen, setSettingsOpen] = useState(false)
    const [helpOpen, setHelpOpen] = useState(false)
    const [tradingMode, setTradingMode] = useState('paper')
    const [tradingPlatform, setTradingPlatform] = useState('binance_futures')
    const [testnet, setTestnet] = useState(false)

    useEffect(() => {
        loadTradingMode()
        const interval = setInterval(loadTradingMode, 5000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        if (!settingsOpen) {
            loadTradingMode()
        }
    }, [settingsOpen])

    const loadTradingMode = async () => {
        try {
            const data = await api.get('/trading/status')
            if (data && data.mode) {
                setTradingMode(data.mode)
                setTradingPlatform(data.platform || 'binance_futures')
                setTestnet(data.testnet || false)
            }
        } catch (err) {
            console.error('Failed to load trading mode:', err)
        }
    }

    return (
        <div className="app">
            <header className="app-header">
                <div className="header-left">
                    <h1 className="logo">
                        <img src={logo} alt="Fibonacci-882 Logo" className="logo-image" />
                        <span className="logo-text">
                            <span className="logo-main">FIB-882</span>
                            <span className="logo-sub">Sniper Platform</span>
                        </span>
                    </h1>
                </div>
                <div className="header-right">
                    <span className="header-badge" title="Trading Pair">BTCUSDT</span>
                    <span className={`header-badge ${tradingMode === 'live' ? 'badge-live' : 'badge-paper'}`} title="Trading Mode">
                        {tradingMode.toUpperCase()}
                    </span>
                    {tradingPlatform === 'binance_futures' && (
                        <span className="header-badge badge-platform" title="Platform">
                            {testnet ? '🧪 TESTNET' : '🔷 BINANCE'}
                        </span>
                    )}
                    <button 
                        className="help-btn"
                        onClick={() => setHelpOpen(true)}
                        title="Help & FAQ"
                    >
                        ❓
                    </button>
                    <button 
                        className="settings-btn"
                        onClick={() => setSettingsOpen(true)}
                        title="Settings"
                    >
                        ⚙️
                    </button>
                </div>
            </header>
            <main>
                <Dashboard />
            </main>
            
            {settingsOpen && (
                <SettingsPanel onClose={() => setSettingsOpen(false)} />
            )}
            
            {helpOpen && (
                <HelpPanel onClose={() => setHelpOpen(false)} />
            )}
        </div>
    )
}
