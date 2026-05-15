"""Modèles métier typés."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Action(str, Enum):
    """Actions reconnues par le moteur de signaux."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    """Signal de trading généré par une stratégie."""

    ticker: str
    market: str
    action: Action
    price: float
    reason: str
    created_at: datetime
    score: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "market": self.market,
            "action": self.action.value,
            "price": self.price,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "score": self.score,
        }


@dataclass(frozen=True)
class OrderRequest:
    """Demande d'ordre prête à être validée puis soumise au broker."""

    ticker: str
    market: str
    action: Action
    quantity: int
    price: float
    reason: str
    created_at: datetime

    @property
    def notional(self) -> float:
        return self.quantity * self.price


@dataclass(frozen=True)
class OrderResult:
    """Résultat normalisé d'une soumission d'ordre."""

    accepted: bool
    dry_run: bool
    message: str
    broker_order_id: str | None = None


def utc_now() -> datetime:
    """Retourne un timestamp timezone-aware."""

    return datetime.now(timezone.utc)
