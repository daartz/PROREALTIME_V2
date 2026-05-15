"""Indicateurs techniques purs et testables."""

from __future__ import annotations

import pandas as pd

from prorealtime_v2.validation import validate_ohlcv


def add_returns(data: pd.DataFrame) -> pd.DataFrame:
    df = validate_ohlcv(data)
    df["Evolution"] = df["Close"].diff()
    df["Evolution_rate"] = df["Close"].pct_change() * 100
    return df


def add_macd(data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    if fast_period >= slow_period:
        raise ValueError("fast_period doit être inférieur à slow_period")
    df = validate_ohlcv(data)
    fast = df["Close"].ewm(span=fast_period, adjust=False).mean()
    slow = df["Close"].ewm(span=slow_period, adjust=False).mean()
    df["macd"] = fast - slow
    df["macd_signal"] = df["macd"].ewm(span=signal_period, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["macd_hist_prev"] = df["macd_hist"].shift(1)
    return df.round(6)


def add_ichimoku(data: pd.DataFrame) -> pd.DataFrame:
    df = validate_ohlcv(data)
    tenkan_high = df["High"].rolling(window=9, min_periods=9).max()
    tenkan_low = df["Low"].rolling(window=9, min_periods=9).min()
    kijun_high = df["High"].rolling(window=26, min_periods=26).max()
    kijun_low = df["Low"].rolling(window=26, min_periods=26).min()
    df["tenkan_sen"] = (tenkan_high + tenkan_low) / 2
    df["kijun_sen"] = (kijun_high + kijun_low) / 2
    df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)
    df["senkou_span_b"] = ((df["High"].rolling(window=52, min_periods=52).max() + df["Low"].rolling(window=52, min_periods=52).min()) / 2).shift(26)
    df["chikou_span"] = df["Close"].shift(-26)
    return df.round(6)


def add_atr(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    df = validate_ohlcv(data)
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift(1)).abs()
    low_close = (df["Low"] - df["Close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = true_range.rolling(window=period, min_periods=period).mean()
    return df.round(6)


def enrich_indicators(data: pd.DataFrame) -> pd.DataFrame:
    df = add_returns(data)
    df = add_macd(df)
    df = add_ichimoku(df)
    df = add_atr(df)
    return df


def add_v1_macd(data: pd.DataFrame) -> pd.DataFrame:
    df = validate_ohlcv(data)
    price = df["Close"]
    exp1 = price.ewm(span=12, adjust=False).mean()
    exp2 = price.ewm(span=26, adjust=False).mean()
    df["macd"] = exp1 - exp2
    df["macd_diff3"] = pd.DataFrame(df["macd"]).diff(periods=2)
    df["macd_roll"] = pd.DataFrame(df["macd"]).rolling(5).sum()
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["hist"] = df["macd"] - df["signal"]
    df["hist_prev"] = df["hist"].shift(1)
    df["hist_prev2"] = df["hist"].shift(2)
    df["hist_diff"] = df["hist"] - df["hist_prev"]
    df["hist_diff2"] = df["hist"] - df["hist_prev2"]
    return df.round(6)


def add_v1_ichimoku(data: pd.DataFrame) -> pd.DataFrame:
    df = validate_ohlcv(data)
    tenkan_max = df["High"].rolling(window=9, min_periods=1).max()
    tenkan_min = df["Low"].rolling(window=9, min_periods=1).min()
    df["TS"] = (tenkan_max + tenkan_min) / 2
    kijun_max = df["High"].rolling(window=26, min_periods=1).max()
    kijun_min = df["Low"].rolling(window=26, min_periods=1).min()
    df["KS"] = (kijun_max + kijun_min) / 2
    df["SSA"] = ((df["TS"] + df["KS"]) / 2).shift(25)
    df["SSB"] = ((df["High"].rolling(window=52).max() + df["Low"].rolling(window=52).min()) / 2).shift(25)
    df["CS"] = df["Close"].shift(-26)
    return df.round(6)


def add_accumulation_distribution(data: pd.DataFrame) -> pd.DataFrame:
    df = validate_ohlcv(data)
    denominator = (df["High"] - df["Low"]).replace(0, pd.NA)
    clv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / denominator
    clv = clv.fillna(0)
    df["AD"] = (clv * df["Volume"]).cumsum()
    df["ad_diff"] = df["AD"].diff()
    df["ad_pct_change"] = df["AD"].pct_change().replace([pd.NA, pd.NaT], 0).fillna(0) * 100
    df["ad_ma3"] = df["AD"].rolling(window=3, min_periods=1).mean()
    return df.round(6)


def enrich_v1_hold_indicators(data: pd.DataFrame) -> pd.DataFrame:
    df = add_returns(data)
    df = add_v1_macd(df)
    df = add_v1_ichimoku(df)
    df = add_accumulation_distribution(df)
    return df
