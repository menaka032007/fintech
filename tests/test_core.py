import numpy as np,pandas as pd
from src.analysis.metrics import asset_metrics
from src.backtesting.engine import run_backtest
def df():
    i=pd.date_range('2022-01-01',periods=300,freq='B'); c=pd.Series(np.linspace(100,150,300),index=i); d=pd.DataFrame({'Close':c});d['DailyReturn']=c.pct_change();d['SMA20']=c.rolling(20).mean();d['SMA50']=c.rolling(50).mean();d['EMA20']=c.ewm(span=20,adjust=False).mean();d['EMA50']=c.ewm(span=50,adjust=False).mean();d['Regime']='Bull / Low Vol';return d
def test_metrics(): assert asset_metrics(df())['total_return']>0
def test_backtest(): assert run_backtest(df(),'sma')['metrics']['final_value']>0
