import numpy as np
import pandas as pd
from src.analysis.metrics import asset_metrics, correlation_matrix, drawdown_details, regime_summary
from src.backtesting.engine import run_backtest, signal_for
from src.data.market_data import add_indicators


def frame(seed=1):
    index = pd.date_range("2021-01-01", periods=320, freq="B")
    rng = np.random.default_rng(seed)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, len(index))),), index=index)
    base = pd.DataFrame({"Open": close * .995, "High": close * 1.01, "Low": close * .99, "Close": close, "Volume": 100000}, index=index)
    return add_indicators(base)


def test_indicators_returns_and_risk_are_dynamic():
    data = add_indicators(frame().iloc[:, :5], sma_short=10, sma_long=30, ema_period=12, rolling_window=15)
    assert data.SMA.iloc[-1] != data.SMALong.iloc[-1]
    assert np.isclose(data.CumulativeReturn.iloc[-1], data.Close.iloc[-1] / data.Close.iloc[0] - 1)
    metrics = asset_metrics(data)
    assert metrics["volatility"] >= 0
    assert metrics["downside_volatility"] >= 0
    assert regime_summary(data)


def test_correlation_matrix_has_selected_assets():
    first, second = frame(1), frame(2)
    matrix = correlation_matrix({"Gold": first, "Bitcoin": second})
    assert list(matrix.columns) == ["Gold", "Bitcoin"]
    assert matrix.loc["Gold", "Gold"] == 1


def test_backtest_costs_and_no_lookahead():
    data = frame()
    result_free = run_backtest(data, "sma", initial=1000, cost=0)
    result_cost = run_backtest(data, "sma", initial=1000, cost=.01)
    assert result_free["metrics"]["final_value"] >= result_cost["metrics"]["final_value"]
    assert result_free["chart"][0]["position"] == 0
    signal, _ = signal_for(data, "momentum")
    assert signal.index.equals(data.index)


def test_all_supported_strategies_return_benchmarks():
    data = frame()
    for strategy in ("sma", "ema", "momentum", "mean_reversion"):
        result = run_backtest(data, strategy)
        assert result["metrics"]["final_value"] > 0
        assert result["buy_hold"]["final_value"] > 0
        assert result["trades"] is not None


def test_drawdown_details_identify_peak_and_trough():
    data = frame()
    details = drawdown_details(data)
    assert details["peak_date"] <= details["trough_date"]
    assert details["drawdown"] <= 0
