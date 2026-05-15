"""Validations de données et garde-fous opérationnels."""

from __future__ import annotations

import pandas as pd

from prorealtime_v2.config import TradingLimits
from prorealtime_v2.models import Action, OrderRequest

REQUIRED_OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


class ValidationError(ValueError):
    """Erreur de validation métier."""


def validate_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Valide et normalise un DataFrame OHLCV."""

    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in data.columns]
    if missing:
        raise ValidationError(f"Colonnes OHLCV manquantes: {', '.join(missing)}")
    if data.empty:
        raise ValidationError("Le DataFrame OHLCV est vide")

    normalized = data.copy()
    normalized = normalized.loc[~normalized.index.duplicated(keep="last")]
    normalized = normalized.sort_index()
    normalized[list(REQUIRED_OHLCV_COLUMNS)] = normalized[list(REQUIRED_OHLCV_COLUMNS)].apply(
        pd.to_numeric, errors="coerce"
    )
    normalized = normalized.dropna(subset=list(REQUIRED_OHLCV_COLUMNS))
    if normalized.empty:
        raise ValidationError("Le DataFrame OHLCV ne contient aucune ligne exploitable")
    if (normalized["Close"] <= 0).any():
        raise ValidationError("Les prix de clôture doivent être strictement positifs")
    return normalized


def validate_orders(orders: list[OrderRequest], limits: TradingLimits) -> None:
    """Applique les limites de sécurité avant soumission d'ordres."""

    if len(orders) > limits.max_orders_per_run:
        raise ValidationError(f"Trop d'ordres: {len(orders)} > limite {limits.max_orders_per_run}")
    for order in orders:
        if order.action not in {Action.BUY, Action.SELL}:
            raise ValidationError(f"Action non soumettable au broker: {order.action}")
        if order.quantity <= 0:
            raise ValidationError(f"Quantité invalide pour {order.ticker}: {order.quantity}")
        if order.price <= 0:
            raise ValidationError(f"Prix invalide pour {order.ticker}: {order.price}")
        if order.notional > limits.max_notional_per_order:
            raise ValidationError(
                f"Notional trop élevé pour {order.ticker}: "
                f"{order.notional:.2f} > {limits.max_notional_per_order:.2f}"
            )
