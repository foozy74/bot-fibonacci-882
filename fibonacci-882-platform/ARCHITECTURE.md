# 🎯 Fibonacci-882 Platform - C4 Architektur Dokumentation

## Überblick

Fibonacci-882 ist eine automatisierte Trading-Plattform für Binance Futures, die auf Fibonacci-Retracement-Leveln basiert und tiefwertige Einstiegspunkte identifiziert.

---

## C4 Level 1: System Context Diagram

### Hauptakteure

```
┌─────────────────┐
│   Trader/User   │
│                 │
│ - Konfiguriert  │
│ - Überwacht     │
│ - Tradet        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     FIBONACCI-882 PLATFORM              │
│                                         │
│  Automatisierte Trading-Plattform für   │
│  Binance Futures mit Fibonacci-Strategie│
└────────┬────────────────┬───────────────┘
         │                │
         ▼                ▼
┌────────────────┐ ┌──────────────────┐
│ Binance Futures│ │ Telegram Bot     │
│ API            │ │ (Notifications)  │
│                │ │                  │
│ - Trading      │ │ - Signale        │
│ - Market Data  │ │ - Trade Updates  │
│ - Account Info │ │ - Fehler         │
└────────────────┘ └──────────────────┘
```

### Externe Systeme

| System | Typ | Beschreibung |
|--------|-----|--------------|
| **Binance Futures API** | Externe API | USDS-Margined Futures Trading Platform |
| **Telegram Bot API** | Externe API | Push-Benachrichtigungen für Signale und Trades |
| **Browser** | Client | React Frontend für UI/UX |

---

## C4 Level 2: Container Diagram

### System-Architektur

```
┌──────────────────────────────────────────────────────────┐
│                    FIBONACCI-882 PLATFORM                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐         ┌─────────────┐                │
│  │   Frontend  │         │   Backend   │                │
│  │   (React)   │◄───────►│  (FastAPI)  │                │
│  │             │  HTTP/  │             │                │
│  │ - Dashboard │  WS     │ - API       │                │
│  │ - Charts    │         │ - Scanner   │                │
│  │ - Settings  │         │ - Trading   │                │
│  │ - Help/FAQ  │         │ - WebSocket │                │
│  └─────────────┘         └──────┬──────┘                │
│         │                       │                        │
│         │                       ▼                        │
│         │              ┌─────────────────┐               │
│         │              │  Services Layer │               │
│         │              │                 │               │
│         │              │ - Binance Client│               │
│         │              │ - Signal Detector│              │
│         │              │ - Trade Manager │               │
│         │              │ - WebSocket     │               │
│         │              │ - Scanner       │               │
│         │              └────────┬────────┘               │
│         │                       │                        │
│         └───────────────────────┼────────────────────────┘
│                                 │
│                    ┌────────────┴────────────┐
│                    │   Data Persistence      │
│                    │                         │
│                    │ - settings.json         │
│                    │ - scanner_history.json  │
│                    │ - signals.json          │
│                    └─────────────────────────┘
└──────────────────────────────────────────────────────────┘
```

### Container Details

| Container | Technologie | Verantwortung |
|-----------|-------------|---------------|
| **Frontend** | React 18, Vite | Benutzeroberfläche, Dashboard, Charts, Settings |
| **Backend API** | FastAPI, Python 3.11 | REST API, Business Logic, Trading-Engine |
| **Binance Client** | aiohttp, asyncio | HTTP/REST Integration mit Binance Futures |
| **WebSocket Client** | aiohttp WebSocket | Real-time Market Data Streams |
| **Signal Detector** | Custom Algorithm | Fibonacci-Level Erkennung + Indikator-Konfluenz |
| **Trade Manager** | Custom Logic | Order-Management, Position Tracking, PnL |
| **Scanner Service** | APScheduler | Hintergrund-Scanner für Multi-Symbol-Analyse |
| **Telegram Bot** | python-telegram-bot | Push-Benachrichtigungen |
| **Data Storage** | JSON Files | Persistente Konfiguration und History |

---

## C4 Level 3: Component Diagram

### Backend Components

```
┌────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                      │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Routers    │  │   Services   │  │    Models    │     │
│  │              │  │              │  │              │     │
│  │ - trading.py │  │ - Binance    │  │ - Schemas    │     │
│  │ - signals.py │  │   Futures    │  │ - Pydantic   │     │
│  │ - scanner.py │  │ - WebSocket  │  │ - Enums      │     │
│  │ - settings.py│  │ - Signal     │  │              │     │
│  │ - websocket  │  │   Detector   │  │              │     │
│  │ - backtest   │  │ - Trade      │  │              │     │
│  └──────────────┘  │   Manager    │  └──────────────┘     │
│                    │ - Scanner    │                        │
│                    │ - Telegram   │                        │
│                    └──────────────┘                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Config & Utils                       │  │
│  │                                                      │  │
│  │ - config.py (Pydantic Settings)                      │  │
│  │ - main.py (FastAPI App, Lifespan)                    │  │
│  │ - requirements.txt                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Frontend Components

```
┌────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   App.jsx    │  │  Dashboard   │  │   Settings   │     │
│  │              │  │              │  │   Panel      │     │
│  │ - State Mgmt │  │ - Price      │  │ - Binance    │     │
│  │ - Routing    │  │ - Signals    │  │ - Telegram   │     │
│  │ - Layout     │  │ - Positions  │  │ - Backtest   │     │
│  └──────────────┘  │ - PnL        │  │ - Scanner    │     │
│                    └──────────────┘  │ - Trading    │     │
│                                      └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Help Panel  │  │  Chart Panel │  │ Signal Panel │     │
│  │              │  │              │  │              │     │
│  │ - Strategie  │  │ - Candlestick│  │ - LONG/SHORT │     │
│  │ - Fibonacci  │  │ - Fib Levels │  │ - Execute    │     │
│  │ - Trading    │  │ - Indicators │  │ - SL/TP      │     │
│  │ - Setup      │  │ - Volume     │  │              │     │
│  │ - FAQ        │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Utils & API                          │  │
│  │                                                      │  │
│  │ - utils/api.js (REST Client)                         │  │
│  │ - WebSocket Connection                               │  │
│  │ - CSS Stylesheets                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Component Details

#### Backend Router Components

| Component | Endpoints | Beschreibung |
|-----------|-----------|--------------|
| **trading.py** | `/trading/status`, `/trading/execute`, `/trading/leverage`, `/trading/margin-mode` | Trading-Operationen, Position Management |
| **signals.py** | `/signals/price`, `/signals/detected`, `/signals/history` | Signal-Erkennung und Historie |
| **scanner.py** | `/scanner/status`, `/scanner/history` | Multi-Symbol Scanner |
| **settings.py** | `/settings`, `/settings/status`, `/settings/test-telegram` | Konfiguration und Tests |
| **websocket.py** | `/ws/live` | WebSocket Endpoint für Real-time Updates |
| **backtest.py** | `/backtest/run` | Backtesting Engine |

#### Service Components

| Component | Verantwortung |
|-----------|---------------|
| **Binance Futures Client** | REST API Integration (Orders, Positions, Account, Market Data) |
| **WebSocket Client** | Real-time Kline, Ticker, Trade Streams |
| **Signal Detector** | Fibonacci-Level Berechnung, RSI, Volume Analyse |
| **Trade Manager** | Order-Execution, Position Tracking, PnL Calculation |
| **Scanner Service** | Hintergrundsprozess für Multi-Symbol-Signal-Scan |
| **Telegram Bot** | Push-Benachrichtigungen für Signale und Trades |

---

## C4 Level 4: Code Diagram

### Key Classes & Interfaces

#### Binance Futures Client

```python
class BinanceFuturesClient:
    """
    Binance Futures Trading Client
    - SIGNED endpoints (TRADE, USER_DATA)
    - Auto-retry with exponential backoff
    - Rate limit handling
    - Time synchronization
    """
    
    # Account Endpoints
    + get_account() -> Dict
    + get_balance() -> List[Dict]
    + get_positions(symbol?: str) -> List[Dict]
    
    # Order Endpoints
    + place_order(symbol, side, type, quantity, ...) -> Dict
    + place_market_order(symbol, side, quantity, ...) -> Dict
    + place_limit_order(symbol, side, quantity, price, ...) -> Dict
    + place_batch_orders(orders: List[Dict]) -> List[Dict]
    + cancel_order(symbol, order_id?) -> Dict
    + cancel_all_orders(symbol) -> Dict
    
    # Configuration
    + set_leverage(symbol, leverage) -> Dict
    + set_margin_mode(symbol, mode) -> Dict
    
    # History
    + get_income_history(symbol?, income_type?, ...) -> List[Dict]
    + get_force_orders(symbol?) -> List[Dict]
    + get_trades(symbol, limit) -> List[Dict]
```

#### Signal Detector

```python
class SignalDetector:
    """
    Fibonacci Signal Detection Engine
    - Detects Swing Highs/Lows
    - Calculates Fibonacci Levels
    - Checks Confluence with Indicators
    """
    
    + detect_signals(candles: List[Dict]) -> List[Signal]
    + _detect_swing_points(candles) -> Tuple[swing_high, swing_low]
    + _calculate_fib_levels(swing_high, swing_low) -> FibLevels
    + _check_confluence(candles, fib_levels) -> ConfluenceScore
    + _validate_rsi(candles) -> bool
    + _validate_volume(candles) -> bool
```

#### WebSocket Client

```python
class BinanceWebSocketClient:
    """
    aiohttp-based WebSocket for Binance Futures
    - Auto-reconnect with exponential backoff
    - Multiple stream subscriptions
    - Data caching for latest values
    """
    
    + start() -> None
    + subscribe(stream_type, symbol, **kwargs) -> str
    + unsubscribe(stream_type, symbol, **kwargs) -> None
    + get_klines(symbol, interval, limit) -> List[Dict]
    + get_mark_price(symbol) -> Dict
    + get_ticker(symbol) -> Dict
    + get_trades(symbol, limit) -> List[Dict]
    + register_callback(event_type, callback) -> None
```

#### Data Models (Pydantic)

```python
class Signal(BaseModel):
    id: str
    timestamp: datetime
    symbol: str
    timeframe: str
    type: SignalType  # LONG or SHORT
    strength: SignalStrength  # WEAK, MEDIUM, STRONG
    entry_price: float
    stop_loss: float
    take_profits: List[float]
    crv: float  # Risk-Reward Ratio
    confluence: ConfluenceData

class Trade(BaseModel):
    id: str
    signal_id: str
    symbol: str
    side: str  # BUY or SELL
    entry_price: float
    quantity: float
    leverage: int
    stop_loss: float
    take_profits: List[float]
    status: TradeStatus  # OPEN, CLOSED, PARTIAL
    pnl: float
    timestamp_open: datetime
    timestamp_close?: datetime

class Account(BaseModel):
    balance: float
    equity: float
    total_pnl: float
    open_positions: List[Trade]
    closed_trades: List[Trade]
```

---

## Datenfluss-Diagramme

### Signal Detection Flow

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Binance   │────►│  WebSocket   │────►│   Signal     │
│   Market    │     │   Client     │     │   Detector   │
│   Data      │     │              │     │              │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │  Fibonacci   │
                                       │   Levels     │
                                       └──────┬───────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │  Confluence  │
                                       │   Check      │
                                       └──────┬───────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │   Signal     │
                                       │   Created    │
                                       └──────┬───────┘
                                                │
                    ┌───────────────────────────┼──────────┐
                    │                           │          │
                    ▼                           ▼          ▼
           ┌────────────┐            ┌────────────┐  ┌──────────┐
           │  Frontend  │            │  Telegram  │  │  Scanner │
           │  Dashboard │            │    Bot     │  │  History │
           └────────────┘            └────────────┘  └──────────┘
```

### Trade Execution Flow

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Signal    │────►│   User       │────►│   Trading    │
│   Detected  │     │   Review     │     │   Router     │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │  Position    │
                                       │  Size Calc   │
                                       └──────┬───────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │   Binance    │
                                       │   Futures    │
                                       │   Client     │
                                       └──────┬───────┘
                                                │
                                                ▼
                                       ┌──────────────┐
                                       │   Order      │
                                       │   Placed     │
                                       └──────┬───────┘
                                                │
                    ┌───────────────────────────┼──────────┐
                    │                           │          │
                    ▼                           ▼          ▼
           ┌────────────┐            ┌────────────┐  ┌──────────┐
           │  Stop Loss │            │Take Profit │  │  Trade   │
           │   Order    │            │  Orders    │  │  Logger  │
           └────────────┘            └────────────┘  └──────────┘
```

---

## Technologie Stack

### Backend

| Komponente | Technologie | Version |
|------------|-------------|---------|
| **Framework** | FastAPI | 0.104.1 |
| **Language** | Python | 3.11 |
| **HTTP Client** | aiohttp | 3.9.1 |
| **WebSocket** | aiohttp, websockets | 12.0 |
| **Validation** | Pydantic | 2.5.2 |
| **Scheduler** | APScheduler | 3.10.4 |
| **Data Processing** | pandas, numpy | 2.1.4, 1.26.2 |
| **Server** | Uvicorn | 0.24.0 |

### Frontend

| Komponente | Technologie | Version |
|------------|-------------|---------|
| **Framework** | React | 18.x |
| **Build Tool** | Vite | 5.4.x |
| **Styling** | CSS3, Glassmorphism | - |
| **Charts** | Custom SVG/Canvas | - |
| **State** | React Hooks | - |

### Infrastructure

| Komponente | Technologie | Beschreibung |
|------------|-------------|--------------|
| **Container** | Docker, Docker Compose | Containerisierung und Orchestrierung |
| **Web Server** | Nginx | Frontend Serving, Reverse Proxy |
| **API Docs** | Swagger UI, ReDoc | Automatische API-Dokumentation |

---

## Sicherheitskonzept

### API Key Management

```
┌─────────────────────────────────────────────┐
│          API Key Security                   │
├─────────────────────────────────────────────┤
│                                             │
│  ✓ API Keys werden in .env gespeichert      │
│  ✓ Keine Commit in Git (.gitignore)         │
│  ✓ Nur Trading-Berechtigung (kein Withdraw) │
│  ✓ HMAC-SHA256 Signatur für Requests        │
│  ✓ Timestamp-basierte Replay-Protection     │
│  ✓ Testnet für Development                  │
│                                             │
└─────────────────────────────────────────────┘
```

### Rate Limiting

| Endpoint | Limit | Behandlung |
|----------|-------|------------|
| **Binance REST** | 1200 requests/min | Auto-Retry mit Backoff |
| **Binance Orders** | 300 orders/10s | Queue-System |
| **WebSocket** | 5 streams/connection | Auto-Reconnect |

---

## Deployment

### Docker Compose Setup

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data
    environment:
      - TRADING_MODE=paper
      - BINANCE_FUTURES_API_KEY=...
      - BINANCE_FUTURES_API_SECRET=...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

### Environment Variables

```bash
# Trading Mode
TRADING_MODE=paper          # paper oder live
TRADING_PLATFORM=binance_futures

# Binance Futures
BINANCE_FUTURES_API_KEY=your_api_key
BINANCE_FUTURES_API_SECRET=your_secret
BINANCE_TESTNET=true        # true für Testnet

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Scanner
SCANNER_INTERVAL=60         # Sekunden
```

---

## API Endpoints Übersicht

### Trading

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/trading/status` | Trading Status, Account, Positions |
| POST | `/trading/execute` | Trade ausführen |
| POST | `/trading/leverage` | Leverage setzen |
| POST | `/trading/margin-mode` | Margin Mode setzen |
| GET | `/trading/open-trades` | Offene Trades |
| GET | `/trading/closed-trades` | Abgeschlossene Trades |
| POST | `/trading/close-all` | Alle Trades schließen |

### Signals

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/signals/price` | Aktueller Preis |
| GET | `/signals/detected` | Erkannte Signale |
| GET | `/signals/history` | Signal-Historie |

### Settings

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/settings` | Alle Einstellungen |
| PUT | `/settings` | Einstellungen speichern |
| GET | `/settings/status` | Service-Status |
| POST | `/settings/test-telegram` | Telegram Test |

### Scanner

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/scanner/status` | Scanner Status |
| GET | `/scanner/history` | Scanner Historie |

---

## Performance & Monitoring

### Metriken

- **API Response Time**: < 200ms (lokal)
- **WebSocket Latency**: < 100ms
- **Signal Detection**: Alle 60s (konfigurierbar)
- **Order Execution**: < 1s

### Logging

```python
# Log Levels
DEBUG   # Request/Response Details
INFO    # Successful Operations
WARNING # Recoverable Errors, Rate Limits
ERROR   # API Failures, Signature Errors
CRITICAL # System Failures
```

---

## Lizenz & Disclaimer

⚠️ **Wichtiger Hinweis**: Diese Software dient nur zu Bildungszwecken und stellt keine Finanzberatung dar. Trading birgt erhebliche Risiken. Verwenden Sie nur Geld, dessen Verlust Sie sich leisten können.

---

## Kontakt & Support

- **GitHub**: https://github.com/bot_fibanoacci
- **Dokumentation**: http://localhost:8000/docs
- **Help Panel**: http://localhost:3000 (❓ Button)
