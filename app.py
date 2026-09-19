import io
import os
import traceback

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, render_template, request
from flask_cors import CORS

from src.analysis.metrics import asset_metrics, correlation_matrix, drawdown_details, quant_insights, regime_summary
from src.analysis.explanations import asset_explanation, chart_explanation, correlation_explanation, metric_definitions, strategy_explanation, what_happened, regime_explanation, backtest_explanation
from src.backtesting.engine import run_backtest
from src.data.market_data import PERIOD_YEARS, get_all_assets, get_asset_data

load_dotenv()
app = Flask(__name__)
CORS(app)
ASSETS = {"Gold": "GC=F", "Bitcoin": "BTC-USD", "NVIDIA": "NVDA"}
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "1000"))
TRANSACTION_COST = float(os.getenv("TRANSACTION_COST", "0.001"))
STRATEGIES = {"sma", "ema", "momentum", "mean_reversion"}


def params():
    return {
        "period": request.args.get("period", "5Y"), "start": request.args.get("start") or None, "end": request.args.get("end") or None,
        "sma_short": int(request.args.get("sma_short", 20)), "sma_long": int(request.args.get("sma_long", 50)),
        "ema_period": int(request.args.get("ema_period", 20)), "rolling_window": int(request.args.get("rolling_window", 20)),
        "momentum_lookback": int(request.args.get("momentum_lookback", 20)), "mean_reversion_lookback": int(request.args.get("mean_reversion_lookback", 20)),
    }


def selected_assets():
    raw = request.args.get("assets")
    names = [item.strip() for item in raw.split(",")] if raw else list(ASSETS)
    unknown = [name for name in names if name not in ASSETS]
    if unknown: raise ValueError(f"Unknown asset(s): {', '.join(unknown)}")
    return {name: ASSETS[name] for name in names}


def number(value):
    try:
        return None if pd.isna(value) else float(value)
    except (TypeError, ValueError):
        return value


def records(df):
    keys = {"Open":"open", "High":"high", "Low":"low", "Close":"close", "Volume":"volume", "DailyReturn":"daily_return", "CumulativeReturn":"cumulative_return", "AnnualizedReturn":"annualized_return", "SMA":"sma", "SMALong":"sma_long", "EMA":"ema", "RollingReturn":"rolling_return", "RollingVolatility":"rolling_volatility", "AnnualizedVolatility":"annualized_volatility", "RollingSharpe":"rolling_sharpe", "Drawdown":"drawdown", "BuySignal":"buy_signal", "SellSignal":"sell_signal", "Regime":"regime"}
    result = []
    for index, row in df.iterrows():
        item = {"date": index.strftime("%Y-%m-%d")}
        for source, key in keys.items(): item[key] = bool(row[source]) if source in {"BuySignal", "SellSignal"} else number(row[source])
        result.append(item)
    return result


def load(names=None):
    settings = params()
    data_settings = {key: settings[key] for key in ["period", "start", "end", "sma_short", "sma_long", "ema_period", "rolling_window"]}
    return get_all_assets(names or selected_assets(), **data_settings)


def handle(function):
    try: return jsonify({"success": True, **function()})
    except ValueError as error: return jsonify({"success": False, "error": str(error)}), 400
    except Exception: return jsonify({"success": False, "error": "Market data or analysis could not be completed right now. Please try again."}), 502


def period_payload(frames, settings):
    first = min(frame.index[0] for frame in frames.values()).strftime("%Y-%m-%d")
    last = max(frame.index[-1] for frame in frames.values()).strftime("%Y-%m-%d")
    return {"period": {"start": first, "end": last, "label": settings["period"] if settings["period"] in PERIOD_YEARS or settings["period"] == "MAX" else "Custom"}, "source": "Yahoo Finance via yfinance", "parameters": settings}


@app.get("/")
def home(): return render_template("index.html")

@app.get("/health")
def health(): return jsonify({"status": "ok"})

@app.get("/api/config")
def config(): return jsonify({"success": True, "assets": ASSETS, "periods": ["1Y", "3Y", "5Y", "10Y", "MAX"], "strategies": sorted(STRATEGIES), "initial_capital": INITIAL_CAPITAL, "transaction_cost": TRANSACTION_COST})

@app.get("/api/market-data")
def market_data():
    def result():
        settings = params(); frames = load(); payload = period_payload(frames, settings)
        payload["assets"] = [{"asset": name, "ticker": ASSETS[name], "data": records(frame)} for name, frame in frames.items()]
        return payload
    return handle(result)

@app.get("/api/overview")
def overview():
    def result():
        settings = params(); frames = load(); payload = period_payload(frames, settings)
        payload["initial_capital"] = INITIAL_CAPITAL
        metrics = [{"asset": name, **asset_metrics(frame)} for name, frame in frames.items()]
        payload["assets"] = [{**item, "explanation": asset_explanation(item["asset"], item, metrics), "what_happened": what_happened(item["asset"], item)} for item in metrics]
        payload["definitions"] = metric_definitions()
        return payload
    return handle(result)

@app.get("/api/asset/<name>")
def asset(name):
    if name not in ASSETS: return jsonify({"success": False, "error": "Unknown asset"}), 404
    def result():
        settings = params(); data_settings = {key: settings[key] for key in ["period", "start", "end", "sma_short", "sma_long", "ema_period", "rolling_window"]}; frame = get_asset_data(ASSETS[name], **data_settings)
        metrics = asset_metrics(frame); latest = records(frame)[-1]
        return {"asset": name, "ticker": ASSETS[name], "metrics": metrics, "prices": records(frame), "regimes": regime_summary(frame), "drawdown": drawdown_details(frame), "explanations": {"what_happened": what_happened(name, metrics), "chart": chart_explanation(name, latest, metrics), "regime": regime_explanation({**latest, "historical_volatility_median": frame.RollingVolatility.median()})}, "definitions": metric_definitions(), **period_payload({name: frame}, settings)}
    return handle(result)

@app.get("/api/analysis")
def analysis():
    return market_data()

@app.get("/api/risk")
def risk():
    def result():
        settings = params(); frames = load(); payload = period_payload(frames, settings); payload["assets"] = []
        for name, frame in frames.items():
            metrics = asset_metrics(frame)
            metrics["asset"] = name; metrics["ticker"] = ASSETS[name]
            metrics["rolling_volatility"] = [{"date": index.strftime("%Y-%m-%d"), "value": number(value)} for index, value in frame.AnnualizedVolatility.items()]
            metrics["drawdown"] = [{"date": index.strftime("%Y-%m-%d"), "value": number(value)} for index, value in frame.Drawdown.items()]
            metrics["regimes"] = regime_summary(frame); metrics["explanation"] = asset_explanation(name, metrics, [asset_metrics(item) | {"asset": key} for key, item in frames.items()]); payload["assets"].append(metrics)
        return payload
    return handle(result)

@app.get("/api/correlation")
def correlation():
    def result():
        settings = params(); frames = load(); returns = pd.concat({name: frame.DailyReturn for name, frame in frames.items()}, axis=1).dropna(); matrix = returns.corr().round(5).to_dict(); window = settings["rolling_window"]
        pairs = {}
        for left in frames:
            for right in frames:
                if left >= right: continue
                series = returns[left].rolling(window).corr(returns[right]); pairs[f"{left}:{right}"] = [{"date": index.strftime("%Y-%m-%d"), "value": number(value)} for index, value in series.items()]
        return {"assets": list(frames), "matrix": matrix, "rolling_window": window, "rolling": pairs, "explanation": correlation_explanation(matrix), **period_payload(frames, settings)}
    return handle(result)

@app.get("/api/backtest")
def backtest():
    def result():
        name = request.args.get("asset", "NVIDIA"); strategy = request.args.get("strategy", "sma")
        if name not in ASSETS or strategy not in STRATEGIES: raise ValueError("Unknown asset or strategy")
        settings = params(); data_settings = {key: settings[key] for key in ["period", "start", "end", "sma_short", "sma_long", "ema_period", "rolling_window"]}; frame = get_asset_data(ASSETS[name], **data_settings)
        output = run_backtest(frame, strategy, float(request.args.get("initial_capital", INITIAL_CAPITAL)), float(request.args.get("transaction_cost", TRANSACTION_COST)), float(request.args.get("position_size", 1)), **{key: settings[key] for key in ["sma_short", "sma_long", "ema_period", "momentum_lookback", "mean_reversion_lookback"]})
        output["explanations"] = {"strategy": strategy_explanation(strategy, output["parameters"]), "summary": backtest_explanation(name, output["strategy_name"], output["metrics"], output["buy_hold"], output["parameters"])}
        return {"asset": name, "ticker": ASSETS[name], "strategy": strategy, **output, **period_payload({name: frame}, settings)}
    return handle(result)

@app.get("/api/summary")
def summary():
    def result():
        settings = params(); frames = load(); payload = period_payload(frames, settings); metrics = [{"asset": name, **asset_metrics(frame)} for name, frame in frames.items()]
        selected_strategy = request.args.get("strategy", "sma"); tests = [{"asset": name, **run_backtest(frame, selected_strategy, INITIAL_CAPITAL, TRANSACTION_COST)} for name, frame in frames.items()]
        highest_return = max(metrics, key=lambda row: row["total_return"])["asset"]; highest_vol = max(metrics, key=lambda row: row["volatility"])["asset"]
        payload.update({"assets": metrics, "strategy": tests, "insights": quant_insights(metrics, correlation_matrix(frames).round(5).to_dict()), "definitions": metric_definitions()})
        return payload
    return handle(result)

@app.get("/api/strategy-comparison")
def strategy_comparison():
    def result():
        settings = params(); name = request.args.get("asset", "Gold")
        if name not in ASSETS: raise ValueError("Unknown asset")
        frame = get_asset_data(ASSETS[name], **{key: settings[key] for key in ["period", "start", "end", "sma_short", "sma_long", "ema_period", "rolling_window"]})
        results = []
        for strategy in sorted(STRATEGIES):
            results.append({"strategy": strategy, **run_backtest(frame, strategy, INITIAL_CAPITAL, TRANSACTION_COST, 1, **{key: settings[key] for key in ["sma_short", "sma_long", "ema_period", "momentum_lookback", "mean_reversion_lookback"]})})
        return {"asset": name, "strategies": results, "period": period_payload({name: frame}, settings)["period"]}
    return handle(result)

@app.get("/api/export/<kind>.csv")
def export_csv(kind):
    try:
        if kind == "market": frame = next(iter(load().values())).reset_index()
        elif kind == "trades": frame = pd.DataFrame(backtest().json["trades"])
        else: return jsonify({"success": False, "error": "Unknown export"}), 400
        response = make_response(frame.to_csv(index=False)); response.headers["Content-Disposition"] = f"attachment; filename={kind}.csv"; response.headers["Content-Type"] = "text/csv"; return response
    except Exception as error: return jsonify({"success": False, "error": str(error)}), 502

if __name__ == "__main__": app.run(host="127.0.0.1", port=5000, debug=True)
