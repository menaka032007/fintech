from datetime import date
from dateutil.relativedelta import relativedelta
import numpy as np
import pandas as pd
import yfinance as yf

CACHE = {}
PERIOD_YEARS = {"1Y": 1, "3Y": 3, "5Y": 5, "10Y": 10}


def _flatten(columns):
    return [column[0] if isinstance(column, tuple) else column for column in columns]


def add_indicators(frame, sma_short=20, sma_long=50, ema_period=20, rolling_window=20):
    if sma_short < 2 or sma_long <= sma_short or ema_period < 2 or rolling_window < 2:
        raise ValueError("Indicator periods must be positive and SMA long must exceed SMA short")
    df = frame.copy()
    df["DailyReturn"] = df.Close.pct_change()
    df["CumulativeReturn"] = (1 + df.DailyReturn.fillna(0)).cumprod() - 1
    df["AnnualizedReturn"] = (1 + df.CumulativeReturn).pow(252 / np.maximum(np.arange(len(df)), 1)) - 1
    df["SMA"] = df.Close.rolling(sma_short).mean()
    df["SMALong"] = df.Close.rolling(sma_long).mean()
    df["EMA"] = df.Close.ewm(span=ema_period, adjust=False).mean()
    df["RollingReturn"] = df.Close.pct_change(rolling_window)
    df["RollingVolatility"] = df.DailyReturn.rolling(rolling_window).std()
    df["AnnualizedVolatility"] = df.RollingVolatility * np.sqrt(252)
    df["RollingSharpe"] = df.DailyReturn.rolling(rolling_window).mean() / df.RollingVolatility.replace(0, np.nan) * np.sqrt(252)
    df["Drawdown"] = df.Close / df.Close.cummax() - 1
    median_vol = df.RollingVolatility.rolling(252, min_periods=30).median()
    uptrend = df.Close >= df.SMALong
    df["Regime"] = np.select(
        [uptrend & (df.RollingVolatility > median_vol), uptrend, (~uptrend) & (df.RollingVolatility > median_vol)],
        ["Bull / High Vol", "Bull / Low Vol", "Bear / High Vol"], default="Bear / Low Vol",
    )
    df["BuySignal"] = ((df.SMA > df.SMALong) & (df.SMA.shift(1) <= df.SMALong.shift(1))).fillna(False)
    df["SellSignal"] = ((df.SMA < df.SMALong) & (df.SMA.shift(1) >= df.SMALong.shift(1))).fillna(False)
    return df


def clean(raw, sma_short=20, sma_long=50, ema_period=20, rolling_window=20):
    if raw is None or raw.empty:
        raise ValueError("Yahoo Finance returned no data. Check your internet connection.")
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = _flatten(df.columns)
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise ValueError(f"Downloaded data is missing: {', '.join(missing)}")
    df = df[required].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if len(df) < max(60, sma_long + 5):
        raise ValueError("Not enough historical observations for the selected indicators")
    return add_indicators(df, sma_short, sma_long, ema_period, rolling_window)


def date_bounds(period="5Y", start=None, end=None):
    if start:
        first = pd.Timestamp(start).date()
    else:
        first = date.today() - relativedelta(years=PERIOD_YEARS.get(period, 5))
    last = pd.Timestamp(end).date() if end else date.today()
    if first >= last:
        raise ValueError("Start date must be before end date")
    return first, last + relativedelta(days=1)


def get_asset_data(ticker, period="5Y", start=None, end=None, sma_short=20, sma_long=50, ema_period=20, rolling_window=20):
    start_date, end_date = date_bounds(period, start, end)
    key = (ticker, start_date.isoformat(), end_date.isoformat(), sma_short, sma_long, ema_period, rolling_window)
    if key not in CACHE:
        download_args = {"auto_adjust": True, "progress": False, "threads": False}
        if period == "MAX" and not start:
            download_args["period"] = "max"
        else:
            download_args.update({"start": start_date.isoformat(), "end": end_date.isoformat()})
        raw = yf.download(ticker, **download_args)
        CACHE[key] = clean(raw, sma_short, sma_long, ema_period, rolling_window)
    return CACHE[key].copy()


def get_all_assets(assets, **kwargs):
    return {name: get_asset_data(ticker, **kwargs) for name, ticker in assets.items()}
