"""Interfaces broker et implémentation dry-run."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from prorealtime_v2.models import OrderRequest, OrderResult

LOGGER = logging.getLogger(__name__)


class Broker(ABC):
    """Contrat minimal de soumission d'ordres."""

    @abstractmethod
    def submit_order(self, order: OrderRequest) -> OrderResult:
        """Soumet un ordre ou le simule."""


class DryRunBroker(Broker):
    """Broker de simulation: aucun ordre réel n'est envoyé."""

    def submit_order(self, order: OrderRequest) -> OrderResult:
        LOGGER.info(
            "DRY-RUN ordre %s %s qty=%s price=%.4f notional=%.2f",
            order.action,
            order.ticker,
            order.quantity,
            order.price,
            order.notional,
        )
        return OrderResult(
            accepted=True,
            dry_run=True,
            message=f"Ordre simulé: {order.action} {order.quantity} {order.ticker}",
        )
