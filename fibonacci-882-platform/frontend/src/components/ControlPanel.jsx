// frontend/src/components/ChartPanel.jsx
import React, { useEffect, useRef } from 'react'
import './ChartPanel.css'

export default function ChartPanel({ levels, liveData }) {
    const canvasRef = useRef(null)

    const fibColors = {
        '0.000': '#6366f1',
        '0.236': '#818cf8',
        '0.382': '#a78bfa',
        '0.500': '#c084fc',
        '0.618': '#f59e0b',
        '0.786': '#f97316',
        '0.882': '#10b981',
        '0.941': '#06b6d4',
        '1.000': '#ef4444',
    }

    useEffect(() => {
        if (!levels?.levels || !canvasRef.current) return

        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        const rect = canvas.getBoundingClientRect()
        canvas.width = rect.width * 2
        canvas.height = rect.height * 2
        ctx.scale(2, 2)

        const width = rect.width
        const height = rect.height
        const l = levels.levels
        const padding = { top: 30, right: 100, bottom: 30, left: 20 }

        const priceRange = l.level_0 - l.level_100
        const toY = (price) => {
            return padding.top + ((l.level_0 - price) / priceRange) * (height - padding.top - padding.bottom)
        }

        // Background
        ctx.fillStyle = 'rgba(10, 14, 23, 0.9)'
        ctx.fillRect(0, 0, width, height)

        // Draw Fibonacci levels
        const drawLevel = (name, price, color) => {
            const y = toY(price)

            ctx.strokeStyle = color
            ctx.lineWidth = name === '0.882' || name === '0.941' ? 2 : 1
            ctx.setLineDash(name === '0.882' || name === '0.941' ? [] : [5, 5])
            ctx.beginPath()
            ctx.moveTo(padding.left, y)
            ctx.lineTo(width - padding.right, y)
            ctx.stroke()
            ctx.setLineDash([])

            // Zone highlight for 882 and 941
            if (name === '0.882' || name === '0.941') {
                ctx.fillStyle = color.replace(')', ', 0.08)').replace('rgb', 'rgba')
                ctx.fillRect(padding.left, y - 8, width - padding.left - padding.right, 16)
            }

            // Label
            ctx.fillStyle = color
            ctx.font = '11px JetBrains Mono'
            ctx.textAlign = 'left'
            ctx.fillText(`${name} — $${price.toFixed(0)}`, width - padding.right + 8, y + 4)
        }

        const levelEntries = [
            ['0.000', l.level_0],
            ['0.236', l.level_236],
            ['0.382', l.level_382],
            ['0.500', l.level_500],
            ['0.618', l.level_618],
            ['0.786', l.level_786],
            ['0.882', l.level_882],
            ['0.941', l.level_941],
            ['1.000', l.level_100],
        ]

        levelEntries.forEach(([name, price]) => {
            drawLevel(name, price, fibColors[name] || '#64748b')
        })

        // Current price line
        const currentPrice = liveData?.price || levels.current_price
        if (currentPrice) {
            const y = toY(currentPrice)
            ctx.strokeStyle = '#ffffff'
            ctx.lineWidth = 2
            ctx.setLineDash([3, 3])
            ctx.beginPath()
            ctx.moveTo(padding.left, y)
            ctx.lineTo(width - padding.right, y)
            ctx.stroke()
            ctx.setLineDash([])

            ctx.fillStyle = '#ffffff'
            ctx.font = 'bold 12px JetBrains Mono'
            ctx.fillText(`► $${currentPrice.toFixed(0)}`, padding.left + 5, y - 8)
        }

    }, [levels, liveData])

    return (
        <div className="glass-card chart-panel">
            <h3>📈 Fibonacci Levels — {levels?.levels ? 'BTCUSDT' : 'Loading...'}</h3>

            <div className="chart-container">
                <canvas ref={canvasRef} className="fib-canvas" />
            </div>

            {levels?.levels && (
                <div className="level-grid">
                    <div className="level-item target">
                        <span className="level-dot" style={{ background: '#10b981' }}></span>
                        <span>0.882</span>
                        <span className="mono">${levels.levels.level_882?.toFixed(2)}</span>
                    </div>
                    <div className="level-item target">
                        <span className="level-dot" style={{ background: '#06b6d4' }}></span>
                        <span>0.941</span>
                        <span className="mono">${levels.levels.level_941?.toFixed(2)}</span>
                    </div>
                    <div className="level-item">
                        <span className="level-dot" style={{ background: '#f97316' }}></span>
                        <span>0.786</span>
                        <span className="mono">${levels.levels.level_786?.toFixed(2)}</span>
                    </div>
                    <div className="level-item">
                        <span className="level-dot" style={{ background: '#ef4444' }}></span>
                        <span>Swing Low</span>
                        <span className="mono">${levels.levels.level_100?.toFixed(2)}</span>
                    </div>
                </div>
            )}
        </div>
    )
}
