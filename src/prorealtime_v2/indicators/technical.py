from __future__ import annotations

import pandas as pd


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    mapping = {c.lower(): c for c in out.columns}
    rename = {}
    for expected in ("Open", "High", "Low", "Close", "Volume"):
        if expected not in out.columns and expected.lower() in mapping:
            rename[mapping[expected.lower()]] = expected
    out = out.rename(columns=rename)
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"])
        out = out.set_index("Date")
    out = out.sort_index()
    return out


def weekly_from_daily(df: pd.DataFrame) -> pd.DataFrame:
    data = normalize_ohlcv(df)
    if data.empty:
        return data
    return data.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna(subset=["Close"])


def add_return(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_ohlcv(df)
    if out.empty:
        return out
    out["Evolution_rate"] = out["Close"].pct_change().fillna(0) * 100
    return out


def add_macd(df: pd.DataFrame, fast: int = 8, slow: int = 21, signal: int = 9) -> pd.DataFrame:
    out = normalize_ohlcv(df)
    if out.empty:
        return out
    ema_fast = out["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = out["Close"].ewm(span=slow, adjust=False).mean()
    out["MACD"] = ema_fast - ema_slow
    out["signal"] = out["MACD"].ewm(span=signal, adjust=False).mean()
    out["hist"] = out["MACD"] - out["signal"]
    return out


def add_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_ohlcv(df)
    if out.empty:
        return out
    high9 = out["High"].rolling(9, min_periods=1).max()
    low9 = out["Low"].rolling(9, min_periods=1).min()
    out["TS"] = (high9 + low9) / 2
    high26 = out["High"].rolling(26, min_periods=1).max()
    low26 = out["Low"].rolling(26, min_periods=1).min()
    out["KS"] = (high26 + low26) / 2
    out["SSA"] = ((out["TS"] + out["KS"]) / 2).shift(26).fillna((out["TS"] + out["KS"]) / 2)
    high52 = out["High"].rolling(52, min_periods=1).max()
    low52 = out["Low"].rolling(52, min_periods=1).min()
    out["SSB"] = ((high52 + low52) / 2).shift(26).fillna((high52 + low52) / 2)
    out["CS"] = out["Close"].shift(-26)
    return out


def add_ad_line(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_ohlcv(df)
    if out.empty:
        return out
    money_flow_multiplier = ((out["Close"] - out["Low"]) - (out["High"] - out["Close"])) / (out["High"] - out["Low"]).replace(0, pd.NA)
    money_flow_volume = money_flow_multiplier.fillna(0) * out["Volume"].fillna(0)
    out["ad"] = money_flow_volume.cumsum()
    out["ad_pct_change"] = out["ad"].pct_change().fillna(0) * 100
    return out


def enrich_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = add_return(df)
    out = add_macd(out)
    out = add_ichimoku(out)
    out = add_ad_line(out)
    return out
