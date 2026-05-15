"""Client minimal IBKR Gateway protégé par confirmation live explicite."""

from __future__ import annotations

import logging

import requests

from prorealtime_v2.brokers.base import Broker
from prorealtime_v2.config import IbkrConfig
from prorealtime_v2.models import Action, OrderRequest, OrderResult

LOGGER = logging.getLogger(__name__)


class IbkrGatewayBroker(Broker):
    """Soumet des ordres via IBKR Client Portal Gateway.

    Cette classe reste volontairement minimale: elle impose une configuration live explicite
    et retourne un résultat normalisé. Les ordres complexes peuvent être ajoutés ensuite.
    """

    def __init__(self, config: IbkrConfig, confirm_live: bool = False) -> None:
        if not confirm_live:
            raise PermissionError("IBKR live nécessite --confirm-live")
        if not config.account_id:
            raise ValueError("IBKR_ACCOUNT_ID est obligatoire en mode live")
        self.config = config
        self.session = requests.Session()

    def submit_order(self, order: OrderRequest) -> OrderResult:
        side = "BUY" if order.action == Action.BUY else "SELL"
        payload = {
            "orders": [
                {
                    "acctId": self.config.account_id,
                    "conid": order.ticker,
                    "orderType": "MKT",
                    "side": side,
                    "quantity": order.quantity,
                    "tif": "DAY",
                    "outsideRTH": False,
                }
            ]
        }
        url = f"{self.config.gateway_url}/iserver/account/{self.config.account_id}/orders"
        LOGGER.warning("Soumission ordre LIVE IBKR: %s", payload)
        response = self.session.post(url, json=payload, timeout=30, verify=False)
        response.raise_for_status()
        return OrderResult(
            accepted=True,
            dry_run=False,
            message="Ordre envoyé à IBKR Gateway",
            broker_order_id=str(response.json()),
        )
