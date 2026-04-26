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
                        <div className="relative group">
                            <div className="absolute -inset-2 bg-teal/20 rounded-full blur-xl opacity-50 group-hover:opacity-100 transition-opacity" />
                            <img src={logo} alt="Fib-882 Logo" className="logo-image relative" />
                        </div>
                        <span className="logo-text">
                            <span className="logo-main uppercase">THESOLUTION<span style={{ color: 'var(--teal)' }}>.AT</span> // FIBONACCI_882</span>
                            <span className="logo-sub">
                                <span style={{ opacity: 0.2, marginRight: '8px' }}>—</span> 
                                DER SMARTE WEG ZU DEINEN TRADES
                            </span>
                        </span>
                    </h1>
                </div>
                <div className="header-right">
                    <span className="header-badge" title="Market Protocol">BTCUSDT // PERP</span>
                    <span className={`badge ${tradingMode === 'live' ? 'badge-live' : 'badge-paper'}`}>
                        {tradingMode.toUpperCase()} STRATEGY
                    </span>
                    {tradingPlatform === 'binance_futures' && (
                        <span className="header-badge font-bold text-blue">
                            {testnet ? 'TESTNET PROTOCOL' : 'BINANCE MAINNET'}
                        </span>
                    )}
                    <div className="flex gap-2 ml-4 border-l border-white/10 pl-4">
                        <button 
                            className="btn px-3"
                            onClick={() => setHelpOpen(true)}
                            title="Documentation"
                        >
                            DOCS
                        </button>
                        <button 
                            className="btn btn-primary"
                            onClick={() => setSettingsOpen(true)}
                            title="Neural Config"
                        >
                            CONFIG
                        </button>
                    </div>
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
