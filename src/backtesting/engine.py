import numpy as np
import pandas as pd
from src.analysis.explanations import signal_reason


def signal_for(df, strategy, sma_short=20, sma_long=50, ema_period=20, momentum_lookback=20, mean_reversion_lookback=20):
    close = df.Close
    if strategy == "sma":
        fast = close.rolling(sma_short).mean(); slow = close.rolling(sma_long).mean()
        signal = (fast > slow).astype(int); name = f"SMA {sma_short}/{sma_long} Crossover"
    elif strategy == "ema":
        fast = close.ewm(span=ema_period, adjust=False).mean(); slow = close.ewm(span=max(ema_period * 2, ema_period + 1), adjust=False).mean()
        signal = (fast > slow).astype(int); name = f"EMA {ema_period} Trend"
    elif strategy == "momentum":
        signal = (close.pct_change(momentum_lookback) > 0).astype(int); name = f"{momentum_lookback}-Day Momentum"
    elif strategy == "mean_reversion":
        mean = close.rolling(mean_reversion_lookback).mean(); deviation = close.rolling(mean_reversion_lookback).std()
        z_score = (close - mean) / deviation.replace(0, np.nan)
        raw = pd.Series(np.nan, index=df.index); raw[z_score < -1] = 1; raw[z_score > 0] = 0
        signal = raw.ffill().fillna(0).astype(int); name = f"{mean_reversion_lookback}-Day Mean Reversion"
    else:
        raise ValueError("Unsupported strategy")
    return signal, name


def metrics(equity, returns, trades):
    enough_returns = len(returns.dropna()) >= 2
    volatility = returns.std() * np.sqrt(252) if enough_returns else np.nan
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if enough_returns and returns.std() > 0 else np.nan
    return {"final_value": float(equity.iloc[-1]), "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1),
            "annualized_return": float((equity.iloc[-1] / equity.iloc[0]) ** (252 / max(len(equity), 1)) - 1),
            "volatility": float(volatility) if np.isfinite(volatility) else None,
            "sharpe": float(sharpe) if np.isfinite(sharpe) else None,
            "max_drawdown": float((equity / equity.cummax() - 1).min()) if enough_returns else None, "trades": int(trades)}


def run_backtest(df, strategy, initial=1000, cost=.001, position_size=1, **params):
    if initial <= 0 or not 0 < position_size <= 1 or cost < 0:
        raise ValueError("Initial capital, position size, and transaction cost are invalid")
    signal, name = signal_for(df, strategy, **params)
    position = signal.shift(1).fillna(0) * position_size
    daily_return = df.Close.pct_change().fillna(0)
    turnover = position.diff().abs().fillna(position.abs())
    strategy_returns = position * daily_return - turnover * cost
    equity = initial * (1 + strategy_returns).cumprod()
    benchmark_returns = daily_return
    benchmark = initial * (1 + benchmark_returns).cumprod()
    changes = signal.diff().fillna(signal)
    parameters = {"initial_capital": initial, "position_size": position_size, "transaction_cost": cost, **params}
    trades = []
    for index in df.index[changes != 0]:
        side = "BUY" if changes.loc[index] > 0 else "SELL"
        trades.append({"date": index.strftime("%Y-%m-%d"), "side": side, "price": float(df.Close.loc[index]), "entry_price": float(df.Close.loc[index]) if side == "BUY" else None, "exit_price": float(df.Close.loc[index]) if side == "SELL" else None, "reason": signal_reason(strategy, side, parameters), "position": float(position.loc[index]), "transaction_cost": float(initial * turnover.loc[index] * cost)})
    chart = [{"date": index.strftime("%Y-%m-%d"), "equity": float(equity.loc[index]), "buy_hold": float(benchmark.loc[index]), "cash": float(initial * (1 - position.loc[index])), "holdings": float(initial * position.loc[index] / max(df.Close.loc[index], 1)), "position": float(position.loc[index]), "buy": bool(changes.loc[index] > 0), "sell": bool(changes.loc[index] < 0)} for index in df.index]
    return {"strategy_name": name, "strategy": strategy, "parameters": parameters, "metrics": metrics(equity, strategy_returns, len(trades)), "buy_hold": metrics(benchmark, benchmark_returns, 0), "trades": trades, "chart": chart}
