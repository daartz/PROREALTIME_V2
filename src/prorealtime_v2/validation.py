"""Validations de données."""

from __future__ import annotations

import pandas as pd

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
    normalized[list(REQUIRED_OHLCV_COLUMNS)] = normalized[list(REQUIRED_OHLCV_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    normalized = normalized.dropna(subset=list(REQUIRED_OHLCV_COLUMNS))
    if normalized.empty:
        raise ValidationError("Le DataFrame OHLCV ne contient aucune ligne exploitable")
    if (normalized["Close"] <= 0).any():
        raise ValidationError("Les prix de clôture doivent être strictement positifs")
    return normalized
