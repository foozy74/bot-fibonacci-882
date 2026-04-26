// frontend/src/utils/api.js
const BASE_URL = import.meta.env.PROD ? '' : 'http://localhost:8000'

export const api = {
    async get(path) {
        const res = await fetch(`${BASE_URL}${path}`)
        if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
        return res.json()
    },

    async post(path, body = {}) {
        const res = await fetch(`${BASE_URL}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        })
        if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
        return res.json()
    },

    async put(path, body = {}) {
        const res = await fetch(`${BASE_URL}${path}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        })
        if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
        return res.json()
    },

    connectWebSocket(onMessage) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const host = import.meta.env.PROD ? window.location.host : 'localhost:8000'
        const ws = new WebSocket(`${protocol}//${host}/ws/live`)

        ws.onopen = () => console.log('🟢 WebSocket connected')
        ws.onclose = () => {
            console.log('🔴 WebSocket disconnected, reconnecting...')
            setTimeout(() => api.connectWebSocket(onMessage), 5000)
        }
        ws.onerror = (err) => console.error('WebSocket error:', err)
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                onMessage(data)
            } catch (e) {
                console.error('WS parse error:', e)
            }
        }

        return ws
    }
}

// Settings API helper
export const settings = {
    async get() {
        return api.get('/settings')
    },

    async save(data) {
        return api.put('/settings', data)
    },

    async testTelegram() {
        return api.post('/settings/test-telegram')
    },

    async getStatus() {
        return api.get('/settings/status')
    },

    async getSymbols() {
        return api.get('/settings/symbols')
    }
}
