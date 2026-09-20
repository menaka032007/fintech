"""Neutral, data-driven explanations for the research dashboard."""


def metric_definitions():
    return {
        "return": "Return measures the historical change in price over the selected period.",
        "cagr": "CAGR expresses the historical return as an annualized rate for comparison across periods.",
        "volatility": "Volatility measures how much prices fluctuated historically. Higher volatility means larger price movements.",
        "sharpe": "Sharpe Ratio compares historical return with historical volatility as a risk-adjusted measure.",
        "drawdown": "Maximum Drawdown measures the largest historical decline from a previous peak.",
        "correlation": "Correlation measures how closely two assets' historical returns moved together, from -1 to +1.",
        "sma": "Simple Moving Average calculates the average price over a selected number of periods.",
        "ema": "Exponential Moving Average gives more weight to recent prices.",
    }


def asset_explanation(asset, metrics, peer_metrics):
    peers = [item for item in peer_metrics if item["asset"] != asset]
    volatility_rank = sum(metrics.get("volatility", 0) > item.get("volatility", 0) for item in peers)
    drawdown_rank = sum(metrics.get("max_drawdown", 0) > item.get("max_drawdown", 0) for item in peers)
    volatility_text = "higher" if volatility_rank else "lower"
    drawdown_text = "smaller" if drawdown_rank == len(peers) else "larger" if drawdown_rank == 0 and peers else "different"
    return f"{asset} recorded a {('positive' if metrics.get('total_return', 0) >= 0 else 'negative')} historical return with {volatility_text} volatility relative to the other selected assets and a {drawdown_text} historical drawdown."


def what_happened(asset, metrics):
    direction = "positive" if metrics.get("total_return", 0) >= 0 else "negative"
    trend = "above" if metrics.get("regime", "").startswith("Bull") else "below"
    return f"During the selected historical period, {asset} recorded a {direction} cumulative return of {metrics.get('total_return', 0):.2%}. Its latest regime places price {trend} the long-term trend threshold, with a maximum historical drawdown of {metrics.get('max_drawdown', 0):.2%}."


def chart_explanation(asset, latest, metrics):
    close = latest.get("close") or 0
    sma_long = latest.get("sma_long") or 0
    sma_short = latest.get("sma") or 0
    rolling_volatility = latest.get("annualized_volatility") or 0
    volatility_metric = metrics.get("volatility") or 0
    price_relation = "above" if close >= sma_long else "below"
    volatility = "higher" if rolling_volatility >= volatility_metric else "lower"
    crossover = "short moving average is above the long moving average" if sma_short >= sma_long else "short moving average is below the long moving average"
    return f"{asset} price is currently {price_relation} SMA50, consistent with the historical {metrics.get('regime', 'transition').lower()} classification. Recent rolling volatility is {volatility} than the full-period annualized volatility, and the {crossover}."


def regime_explanation(latest):
    trend = "above" if (latest.get("close") or 0) >= (latest.get("sma_long") or 0) else "below"
    volatility = "above" if (latest.get("rolling_volatility") or 0) >= (latest.get("historical_volatility_median") or 0) else "below"
    return f"Price is {trend} SMA50 and current rolling volatility is {volatility} its historical median."


def strategy_explanation(strategy, parameters):
    if strategy == "sma":
        return f"Buy/hold exposure when SMA{parameters.get('sma_short', 20)} is above SMA{parameters.get('sma_long', 50)}. Exit when it falls to or below the long average."
    if strategy == "ema":
        return f"Uses the relationship between EMA{parameters.get('ema_period', 20)} and a slower EMA to identify historical trend conditions."
    if strategy == "momentum":
        return f"Uses the recent {parameters.get('momentum_lookback', 20)}-day price change; exposure is held while that historical momentum condition is positive."
    return f"Uses the distance between price and its recent {parameters.get('mean_reversion_lookback', 20)}-day mean, measured with a standard-deviation score."


def signal_reason(strategy, side, parameters):
    if strategy == "sma": return f"SMA{parameters.get('sma_short', 20)} crossed {'above' if side == 'BUY' else 'below'} SMA{parameters.get('sma_long', 50)}."
    if strategy == "ema": return f"Fast EMA moved {'above' if side == 'BUY' else 'below'} the slower EMA."
    if strategy == "momentum": return f"{parameters.get('momentum_lookback', 20)}-day momentum became {'positive' if side == 'BUY' else 'non-positive'}."
    return "Price moved below the lower deviation threshold." if side == "BUY" else "Price reverted above the exit threshold."


def backtest_explanation(asset, strategy_name, metrics, benchmark, parameters):
    return f"You tested {asset} using {strategy_name} with an initial capital of {parameters.get('initial_capital', 0):,.2f}. The strategy generated {metrics.get('trades', 0)} trades; its final simulated value was {metrics.get('final_value', 0):,.2f}, compared with {benchmark.get('final_value', 0):,.2f} for Buy & Hold. This is a historical simulation, not a future performance claim."


def correlation_explanation(matrix):
    pairs = []
    names = list(matrix)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1:]:
            value = matrix[left].get(right)
            if value is not None:
                pairs.append((value, left, right))
    if not pairs:
        return "Correlation requires at least two assets with overlapping returns."
    strongest = max(pairs, key=lambda pair: abs(pair[0]))
    direction = "positive" if strongest[0] >= 0 else "negative"
    return f"{strongest[1]} and {strongest[2]} showed the strongest {direction} historical return correlation in this period ({strongest[0]:.2f}). Correlation describes co-movement; it does not imply causation."
