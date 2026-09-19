import pandas as pd

from app import records
from src.data.market_data import add_indicators


def test_market_rows_expose_selected_date_fields_and_warmup_nulls():
    dates = pd.date_range("2024-01-01", periods=80, freq="B")
    close = pd.Series(range(100, 180), index=dates, dtype=float)
    frame = pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000}, index=dates)
    data = add_indicators(frame)
    rows = records(data)
    expected = {"date", "close", "daily_return", "cumulative_return", "sma", "sma_long", "ema", "rolling_return", "annualized_volatility", "drawdown", "regime", "buy_signal", "sell_signal"}
    assert expected.issubset(rows[-1])
    assert rows[0]["sma"] is None
    assert rows[-1]["close"] == 179.0
