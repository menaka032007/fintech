from src.analysis.explanations import asset_explanation, correlation_explanation, signal_reason, strategy_explanation


def test_explanations_use_calculated_values():
    metrics = {"asset": "Gold", "total_return": 0.12, "volatility": 0.1, "max_drawdown": -0.08, "regime": "Bull / Low Vol"}
    peers = [metrics, {"asset": "Bitcoin", "total_return": 0.2, "volatility": 0.4, "max_drawdown": -0.7}]
    text = asset_explanation("Gold", metrics, peers)
    assert "Gold" in text and "lower volatility" in text
    assert "0.12" not in text


def test_strategy_and_signal_explanations_match_logic():
    parameters = {"sma_short": 10, "sma_long": 40, "momentum_lookback": 15}
    assert "SMA10" in strategy_explanation("sma", parameters)
    assert "crossed above" in signal_reason("sma", "BUY", parameters)
    assert "15-day" in strategy_explanation("momentum", parameters)


def test_correlation_explanation_identifies_strongest_pair():
    matrix = {"Gold": {"Gold": 1, "Bitcoin": .2}, "Bitcoin": {"Gold": .2, "Bitcoin": 1}}
    assert "Gold and Bitcoin" in correlation_explanation(matrix)
