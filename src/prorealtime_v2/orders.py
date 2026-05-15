"""Construction et exécution sécurisée des ordres."""

from __future__ import annotations

import logging

import pandas as pd

from prorealtime_v2.brokers.base import Broker
from prorealtime_v2.config import TradingLimits
from prorealtime_v2.models import Action, OrderRequest, OrderResult, utc_now
from prorealtime_v2.validation import validate_orders

LOGGER = logging.getLogger(__name__)


def orders_from_signals(signals: pd.DataFrame, notional_per_order: float) -> list[OrderRequest]:
    """Transforme des signaux BUY/SELL en demandes d'ordres bornées par notional."""

    orders: list[OrderRequest] = []
    for _, row in signals.iterrows():
        action = Action(str(row["action"]).upper())
        if action == Action.HOLD:
            continue
        price = float(row["price"])
        quantity = int(notional_per_order // price)
        if quantity <= 0:
            LOGGER.warning("Signal ignoré, quantité nulle: %s", row.to_dict())
            continue
        orders.append(
            OrderRequest(
                ticker=str(row["ticker"]),
                market=str(row["market"]),
                action=action,
                quantity=quantity,
                price=price,
                reason=str(row["reason"]),
                created_at=utc_now(),
            )
        )
    return orders


def submit_orders(
    orders: list[OrderRequest], broker: Broker, limits: TradingLimits
) -> list[OrderResult]:
    """Valide puis soumet les ordres au broker fourni."""

    validate_orders(orders, limits)
    return [broker.submit_order(order) for order in orders]
