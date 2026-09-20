import numpy as np
import pandas as pd


def safe(value):
    return None if value is None or not np.isfinite(value) else float(value)


def annualized_return(close):
    years = max((close.index[-1] - close.index[0]).days / 365.25, 1 / 365.25)
    return (close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1


def asset_metrics(df, risk_free_rate=0):
    returns = df.DailyReturn.dropna()
    drawdown = df.Drawdown if "Drawdown" in df else df.Close / df.Close.cummax() - 1
    enough_returns = len(returns) >= 2
    volatility = returns.std() * np.sqrt(252) if enough_returns else np.nan
    excess = returns - risk_free_rate / 252
    sharpe = excess.mean() / returns.std() * np.sqrt(252) if enough_returns and returns.std() > 0 else np.nan
    return {
        "latest_price": safe(df.Close.iloc[-1]), "daily_return": safe(df.DailyReturn.iloc[-1]),
        "total_return": safe(df.Close.iloc[-1] / df.Close.iloc[0] - 1),
        "annualized_return": safe(annualized_return(df.Close)), "volatility": safe(volatility),
        "sharpe": safe(sharpe), "max_drawdown": safe(drawdown.min()) if enough_returns else None,
        "downside_volatility": safe(returns[returns < 0].std() * np.sqrt(252)) if enough_returns else None,
        "observations": int(len(df)), "start_date": df.index[0].strftime("%Y-%m-%d"),
        "end_date": df.index[-1].strftime("%Y-%m-%d"), "regime": str(df.Regime.iloc[-1]),
    }


def correlation_matrix(data):
    return pd.concat({name: frame.DailyReturn for name, frame in data.items()}, axis=1).dropna().corr()


def regime_summary(df):
    rows = []
    for regime, group in df.groupby("Regime"):
        returns = group.DailyReturn.dropna()
        rows.append({"regime": regime, "observations": int(len(group)), "return": safe((1 + returns).prod() - 1),
                     "volatility": safe(returns.std() * np.sqrt(252)), "drawdown": safe(group.Drawdown.min())})
    return rows


def drawdown_details(df):
    drawdown = df.Drawdown if "Drawdown" in df else df.Close / df.Close.cummax() - 1
    trough = drawdown.idxmin()
    peak = df.Close.loc[:trough].idxmax()
    recovery = None
    peak_value = df.Close.loc[peak]
    after_trough = df.loc[trough:]
    recovered = after_trough[after_trough.Close >= peak_value]
    if not recovered.empty:
        recovery = recovered.index[0].strftime("%Y-%m-%d")
    return {"drawdown": safe(drawdown.loc[trough]), "peak_date": peak.strftime("%Y-%m-%d"),
            "trough_date": trough.strftime("%Y-%m-%d"), "recovery_date": recovery,
            "recovered": recovery is not None,
            "context": "Price was below SMA50 at the trough." if "SMALong" in df and df.SMALong.loc[trough] == df.SMALong.loc[trough] and df.Close.loc[trough] < df.SMALong.loc[trough] else "Price was not below SMA50 at the trough."}


def quant_insights(metrics, correlation):
    insights = []
    if metrics:
        highest_vol = max(metrics, key=lambda row: row.get("volatility") or -np.inf)
        lowest_vol = min(metrics, key=lambda row: row.get("volatility") or np.inf)
        largest_drawdown = min(metrics, key=lambda row: row.get("max_drawdown") or 0)
        insights.extend([f"{highest_vol['asset']} showed higher annualized volatility than {lowest_vol['asset']} during the selected period.", f"{largest_drawdown['asset']} experienced the largest historical maximum drawdown among the selected assets."])
    pairs = []
    names = list(correlation)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1:]: pairs.append((correlation[left].get(right), left, right))
    if pairs:
        value, left, right = max(pairs, key=lambda pair: abs(pair[0] or 0))
        insights.append(f"{left} and {right} showed a {'positive' if value >= 0 else 'negative'} daily-return correlation during the selected period.")
    return insights
