"""Client Yahoo Finance avec retries bornés et validation OHLCV."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from prorealtime_v2.validation import validate_ohlcv

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class YahooFinanceProvider:
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    def download(self, ticker: str, start: str, end: str, interval: str = "1d", auto_adjust: bool = True) -> pd.DataFrame:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                LOGGER.info("Téléchargement %s %s->%s interval=%s", ticker, start, end, interval)
                data = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=auto_adjust, progress=False, repair=True, threads=False)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                return validate_ohlcv(data.round(4))
            except Exception as exc:
                last_error = exc
                LOGGER.warning("Échec téléchargement %s tentative %s/%s: %s", ticker, attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_seconds * attempt)
        raise RuntimeError(f"Impossible de récupérer les données pour {ticker}") from last_error


def resample_ohlcv(data: pd.DataFrame, frequency: str) -> pd.DataFrame:
    valid = validate_ohlcv(data)
    resampled = pd.DataFrame({
        "Open": valid["Open"].resample(frequency).first(),
        "High": valid["High"].resample(frequency).max(),
        "Low": valid["Low"].resample(frequency).min(),
        "Close": valid["Close"].resample(frequency).last(),
        "Volume": valid["Volume"].resample(frequency).sum(),
    })
    return validate_ohlcv(resampled.dropna())
