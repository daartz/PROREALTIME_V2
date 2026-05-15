"""Stratégie MACD + tendance inspirée de la V1, mais explicite et testable."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from prorealtime_v2.indicators import enrich_indicators
from prorealtime_v2.models import Action, Signal, utc_now
from prorealtime_v2.validation import validate_ohlcv


@dataclass(frozen=True)
class MacdTrendConfig:
    """Paramètres de stratégie versionnés et modifiables."""

    min_price: float = 1.0
    require_cloud_breakout: bool = False
    stop_loss_pct: float = 4.0


class MacdTrendStrategy:
    """Génère BUY/SELL/HOLD selon accélération MACD et filtre de tendance."""

    def __init__(self, config: MacdTrendConfig | None = None) -> None:
        self.config = config or MacdTrendConfig()

    def prepare(self, data: pd.DataFrame) -> pd.DataFrame:
        return enrich_indicators(validate_ohlcv(data))

    def latest_signal(self, ticker: str, market: str, data: pd.DataFrame) -> Signal:
        """Retourne le signal le plus récent."""

        prepared = self.prepare(data).dropna(subset=["macd_hist", "macd_hist_prev"])
        if prepared.empty:
            raise ValueError(f"Pas assez de données pour générer un signal sur {ticker}")

        row = prepared.iloc[-1]
        price = float(row["Close"])
        action, reason = self._decide(row)
        return Signal(
            ticker=ticker,
            market=market,
            action=action,
            price=round(price, 4),
            reason=reason,
            created_at=utc_now(),
        )

    def signal_history(self, ticker: str, market: str, data: pd.DataFrame) -> list[Signal]:
        """Construit l'historique des signaux pour comparaison/backtest rapide."""

        prepared = self.prepare(data).dropna(subset=["macd_hist", "macd_hist_prev"])
        signals: list[Signal] = []
        for _, row in prepared.iterrows():
            action, reason = self._decide(row)
            signals.append(
                Signal(
                    ticker=ticker,
                    market=market,
                    action=action,
                    price=round(float(row["Close"]), 4),
                    reason=reason,
                    created_at=utc_now(),
                )
            )
        return signals

    def _decide(self, row: pd.Series) -> tuple[Action, str]:
        price = float(row["Close"])
        hist = float(row["macd_hist"])
        hist_prev = float(row["macd_hist_prev"])
        above_min_price = price > self.config.min_price
        hist_improving = hist > hist_prev
        hist_declining = hist < hist_prev

        cloud_ok = True
        if self.config.require_cloud_breakout:
            span_a = row.get("senkou_span_a")
            span_b = row.get("senkou_span_b")
            cloud_ok = pd.notna(span_a) and pd.notna(span_b) and price > max(span_a, span_b)

        if above_min_price and hist_improving and cloud_ok:
            return Action.BUY, "MACD histogramme en amélioration avec filtre prix/tendance valide"
        if hist_declining and hist < 0:
            return Action.SELL, "MACD histogramme en dégradation sous zéro"
        return Action.HOLD, "Aucun signal exploitable"
