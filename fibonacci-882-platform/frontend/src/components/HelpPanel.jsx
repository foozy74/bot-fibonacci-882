// frontend/src/components/HelpPanel.jsx
import React, { useState } from 'react'
import logo from '../assets/logo.svg'
import './HelpPanel.css'

export default function HelpPanel({ onClose }) {
    const [activeSection, setActiveSection] = useState('strategy')
    const sections = ['strategy', 'fibonacci', 'trading', 'setup', 'faq']

    const content = {
        strategy: <div><h3>🎯 Fibonacci-882 Strategie</h3><div className="info-card"><h4>📋 Überblick</h4><p>Kombination aus Fibonacci-Retracement-Leveln mit technischen Indikatoren für präzise Einstiegspunkte.</p></div><div className="info-card"><h4>🔑 Kernkomponenten</h4><div className="feature-grid"><div className="feature-item"><span className="feature-icon">📐</span><h5>Fibonacci-Levels</h5><p>0.236, 0.382, 0.5, 0.618, 0.786</p></div><div className="feature-item"><span className="feature-icon">📊</span><h5>RSI Indikator</h5><p>Überkauft/Überverkauft Signale</p></div><div className="feature-item"><span className="feature-icon">🌊</span><h5>Volatilität</h5><p>ATR-basierte Stop-Loss Berechnung</p></div><div className="feature-item"><span className="feature-icon">🎯</span><h5>Sniper Entries</h5><p>Präzise Einstiege an Konfluenz-Zonen</p></div></div></div></div>,
        fibonacci: <div><h3>🎯 Fibonacci Retracement</h3><div className="info-card"><h4>Die wichtigsten Levels</h4><div className="levels-table"><div className="level-row"><span className="level-value">0.382 (38.2%)</span><span className="level-desc">Wichtiges Level, häufiger Einstieg</span></div><div className="level-row highlight"><span className="level-value">0.5 (50%)</span><span className="level-desc">Psychologisch wichtig</span></div><div className="level-row super-highlight"><span className="level-value">0.618 (61.8%)</span><span className="level-desc">"Goldener Schnitt" - stärkstes Level</span></div></div></div></div>,
        trading: <div><h3>💹 Trading Guide</h3><div className="info-card"><h4>📝 Signal-Arten</h4><div className="signal-types"><div className="signal-type buy"><span className="signal-badge">🟢 LONG</span><p>Preis berührt Fibonacci-Level + RSI überverkauft</p></div><div className="signal-type sell"><span className="signal-badge">🔴 SHORT</span><p>Preis berührt Fibonacci-Level + RSI überkauft</p></div></div></div></div>,
        setup: <div><h3>⚙️ Setup Anleitung</h3><div className="info-card"><h4>🚀 Schnellstart</h4><ol className="steps-list"><li><strong>API Keys konfigurieren</strong><p>Settings → Binance Futures → API Key & Secret</p></li><li><strong>Testnet aktivieren</strong><p>☑ Testnet für sicheres Testen</p></li><li><strong>Verbindung testen</strong><p>"🧪 Test Connection" klicken</p></li></ol></div></div>,
        faq: <div><h3>❓ FAQ</h3><div className="faq-list"><div className="faq-item"><h4>💰 Wie viel Kapital brauche ich?</h4><p>Empfohlen: $500-1000 für sinnvolles Risk-Management.</p></div><div className="faq-item"><h4>🎯 Wie genau ist die Strategie?</h4><p>Ziel: 55-65% Win-Rate bei 1:2 Risk-Reward.</p></div><div className="faq-item"><h4>⏱️ Wie lange dauert ein Trade?</h4><p>15-Minuten-Timeframe: 1-8 Stunden typisch.</p></div></div></div>
    }

    return (
        <div className="help-overlay" onClick={onClose}>
            <div className="help-panel" onClick={e => e.stopPropagation()}>
                <div className="help-header">
                    <div className="help-logo-container">
                        <img src={logo} alt="Logo" className="help-logo" />
                        <h2>📖 Hilfe & FAQ</h2>
                    </div>
                    <button className="help-close-btn" onClick={onClose}>✕</button>
                </div>
                <div className="help-content">
                    <div className="help-nav">
                        {sections.map(s => <button key={s} className={`help-nav-btn ${activeSection === s ? 'active' : ''}`} onClick={() => setActiveSection(s)}>{s === 'strategy' ? '📊 Strategie' : s === 'fibonacci' ? '🎯 Fibonacci' : s === 'trading' ? '💹 Trading' : s === 'setup' ? '⚙️ Setup' : '❓ FAQ'}</button>)}
                    </div>
                    <div className="help-section">{content[activeSection]}</div>
                </div>
                <div className="help-footer"><p>⚠️ Disclaimer: Nur zu Bildungszwecken, keine Finanzberatung!</p></div>
            </div>
        </div>
    )
}
