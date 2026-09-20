from datetime import date, timedelta
import numpy as np
import pandas as pd
import yfinance as yf

CACHE = {}
MIN_DATE = date(2021, 1, 1)
MAX_DATE = date(2026, 9, 20)


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
    return add_indicators(df, sma_short, sma_long, ema_period, rolling_window)


def date_bounds(selected_date=None, start_date=None, end_date=None, period=None, start=None, end=None):
    if selected_date:
        try:
            selected = pd.Timestamp(selected_date).date()
        except (TypeError, ValueError) as error:
            raise ValueError("Date must use YYYY-MM-DD format") from error
        if selected < MIN_DATE:
            raise ValueError("Selected date cannot be before 2021-01-01")
        if selected > MAX_DATE:
            raise ValueError("Selected date cannot be after 2026-09-20")
        return MIN_DATE, selected + timedelta(days=1)
    first_value = start_date or start or MIN_DATE.isoformat()
    last_value = end_date or end or MAX_DATE.isoformat()
    try:
        first = pd.Timestamp(first_value).date()
        last = pd.Timestamp(last_value).date()
    except (TypeError, ValueError) as error:
        raise ValueError("Dates must use YYYY-MM-DD format") from error
    if first < MIN_DATE:
        raise ValueError("Start date cannot be before 2021-01-01")
    if last > MAX_DATE:
        raise ValueError("End date cannot be after 2026-09-20")
    if first >= last:
        raise ValueError("FROM date must be earlier than TO date")
    return first, last + timedelta(days=1)


def get_asset_data(ticker, selected_date=None, period=None, start_date=None, end_date=None, start=None, end=None, sma_short=20, sma_long=50, ema_period=20, rolling_window=20):
    first, last = date_bounds(selected_date, start_date, end_date, period, start, end)
    key = (ticker, selected_date, first.isoformat(), last.isoformat(), sma_short, sma_long, ema_period, rolling_window)
    if key not in CACHE:
        download_args = {
            "start": first.isoformat(),
            "end": last.isoformat(),
            "interval": "1d",
            "auto_adjust": True,
            "progress": False,
            "threads": False,
        }
        raw = yf.download(ticker, **download_args)
        frame = clean(raw, sma_short, sma_long, ema_period, rolling_window)
        if selected_date and pd.Timestamp(selected_date) not in frame.index:
            raise ValueError("No market data available for this date.")
        CACHE[key] = frame
    return CACHE[key].copy()


def get_all_assets(assets, **kwargs):
    return {name: get_asset_data(ticker, **kwargs) for name, ticker in assets.items()}
