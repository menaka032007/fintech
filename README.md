# Quantitative Multi-Asset Financial Intelligence & Backtesting Platform

A Flask and Plotly research terminal for historical analysis of Gold (`GC=F`), Bitcoin (`BTC-USD`), and NVIDIA (`NVDA`). It combines data engineering, quantitative indicators, risk modelling, correlation analysis, transparent market regimes, and configurable strategy backtesting in one runnable application.

## Problem and approach

The platform turns raw Yahoo Finance OHLCV data into reproducible research outputs. The dashboard selects one historical date using dependent year, month, and date dropdowns. The backend loads history from the supported start date through the selected date, verifies that the exact selected date has market data for every requested asset, and uses that history for indicators, risk, correlation, and backtesting. Backtest positions are shifted one session so a signal generated at time `t` cannot use the return at `t` or information after it.

## Features

- Single historical date selection from 2021-01-01 through 2026-09-20 using dependent year, month, and date selectors
- Exact selected-date validation; weekends and market holidays return a clear no-data error instead of silently selecting another day
- OHLCV, daily return, cumulative return, annualized return, SMA, EMA, rolling return
- Historical/annualized volatility, downside volatility, rolling Sharpe, drawdown, and Sharpe ratio
- Normalized price, raw price, return, volatility, drawdown, correlation, and rolling-correlation charts
- SMA crossover, EMA trend, momentum, and mean-reversion strategies
- Configurable capital, position size, transaction cost, and indicator periods
- Cash, holdings, portfolio value, signals, trades, entry/exit price, trade count, and costs
- Same-period buy-and-hold benchmark comparison
- Historical bull/bear and high/low-volatility regime summaries
- CSV export links for market data and trades
- Loading/error states, responsive dark financial-terminal UI, and reduced-motion support
- Data-driven plain-language explanations for asset cards, charts, regimes, correlations, metrics, signals, and backtests
- Risk-versus-return scatter, CAGR/trend context, drawdown peak/trough/recovery details, and historical strategy comparison
- Clickable historical chart dates with synchronized selected-date OHLC/indicator, return, regime, and signal details
- Simple Mode for beginners and Research Mode for detailed trade and regime tables

## Run locally

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

Run tests:

```powershell
python -m pytest -q
```

The project can also be run with the included virtual environment on Windows:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Environment variables

```text
INITIAL_CAPITAL=1000
TRANSACTION_COST=0.001
```

`TRANSACTION_COST` is a decimal fraction: `0.001` means 0.10% per position turnover.

## API routes

- `GET /api/config`
- `GET /health`
- `GET /api/market-data?date=2025-09-26&assets=GC%3DF,BTC-USD,NVDA`
- `GET /api/overview?date=2025-09-26`
- `GET /api/asset/Gold?date=2025-09-26`
- `GET /api/analysis?date=2025-09-26`
- `GET /api/risk?date=2025-09-26`
- `GET /api/correlation?date=2025-09-26`
- `GET /api/backtest?date=2025-09-26&asset=Gold&strategy=sma`
- `GET /api/summary?date=2025-09-26`
- `GET /api/strategy-comparison?date=2025-09-26&asset=Gold`
- `GET /api/export/market.csv?date=2025-09-26`
- `GET /api/export/trades.csv?date=2025-09-26&asset=Gold&strategy=sma`

The `date` parameter must be formatted as `YYYY-MM-DD` and must fall between `2021-01-01` and `2026-09-20`. The dashboard sends this value after the user clicks Apply. Each endpoint uses the selected date consistently.

The Asset Analysis price and normalized-performance charts use Plotly click events. Selecting any available daily point updates the Selected Date Details panel without a page reload. Metrics that cannot be calculated for a short history are displayed as `Insufficient data`.

Overview, asset, correlation, and backtest responses include neutral explanation fields generated from the calculated results. The dashboard's `Explain this backtest` action uses those fields rather than inventing a conclusion.

Common parameters include `date`, `assets`, `sma_short`, `sma_long`, `ema_period`, and `rolling_window`. Backtests additionally accept `initial_capital`, `position_size`, and `transaction_cost`. If Yahoo Finance has no row for the selected date, the API returns `No market data available for this date.` rather than substituting another date.

## Methodology

SMA crossover enters when the short moving average is above the long moving average. EMA trend uses a fast EMA against a slower EMA. Momentum holds when the selected lookback return is positive. Mean reversion enters below a negative z-score and exits as price reverts. Signals are shifted before returns are applied. Turnover costs are subtracted from strategy returns, and the benchmark buys at the beginning of the selected period.

Regimes are explainable historical labels based on price relative to the long SMA and rolling volatility relative to its historical median. They are descriptive classifications, not forecasts. Moving averages, rolling statistics, and strategy signals use the available history ending at the selected date; warm-up values remain unavailable until enough observations exist.

## Architecture

```text
app.py                         Flask routes, date validation, exports
src/data/market_data.py        yfinance loading, exact-date checks, indicators
src/analysis/metrics.py        risk, returns, correlation, regime metrics
src/analysis/explanations.py   data-driven dashboard explanations
src/backtesting/engine.py      signals, portfolio simulation, benchmark
templates/                     shared shell and dashboard modules
static/                        Plotly client and responsive terminal CSS
tests/                         core and quantitative regression tests
```

The calculation modules are intentionally separated from rendering so future portfolio optimization, Monte Carlo, VaR, paper trading, live data, and ML regime detection can be added without replacing the dashboard.

## Limitations and disclaimer

Yahoo Finance availability, ticker history, adjusted prices, holidays, and data revisions can affect results. A selected weekend or market holiday may return no data. This is not a production execution simulator and does not model slippage, taxes, spreads, or market impact. Historical backtest results do not guarantee future performance. This platform is for quantitative research and educational purposes and does not constitute financial advice.
