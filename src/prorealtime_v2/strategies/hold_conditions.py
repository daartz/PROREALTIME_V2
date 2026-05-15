from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

import pandas as pd

from prorealtime_v2.strategies.hold_rules import should_buy, should_sell, should_vad_buy, should_vad_sell
from prorealtime_v2.strategies.hold_signals import determine_comment_and_opportunity as _detect_signal


class HoldOrder(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    VAD_SELL = "VAD SELL"
    VAD_BUY = "VAD BUY"
    VAD_HOLD = "VAD HOLD"
    WAIT = "WAIT"


@dataclass(frozen=True)
class DecisionContext:
    today: date

    @property
    def day_of_month(self) -> int:
        return self.today.day

    @property
    def weekday(self) -> int:
        return self.today.weekday()

    @classmethod
    def now(cls) -> "DecisionContext":
        return cls(today=datetime.today().date())


@dataclass(frozen=True)
class CommentOpportunity:
    comment: str
    opportunity: str
    ts: int
    ks: int
    cloud: int

    def as_legacy_tuple(self) -> tuple[str, str, int, int, int]:
        return self.comment, self.opportunity, self.ts, self.ks, self.cloud


def determine_comment_and_opportunity(name: str, data: pd.DataFrame, market: str = "MARKET") -> CommentOpportunity:
    del name, market
    signal = _detect_signal(data)
    return CommentOpportunity(signal.comment, signal.opportunity, signal.ts, signal.ks, signal.cloud)


def decide_order(
    position_count: int,
    signals: dict[str, Any],
    weekly_trading: int = 0,
    context: DecisionContext | None = None,
    use_long: bool = True,
    use_short: bool = True,
) -> HoldOrder:
    del weekly_trading, context
    if use_long:
        if should_sell(position_count, signals):
            return HoldOrder.SELL
        if should_buy(position_count, signals):
            return HoldOrder.BUY
        if position_count > 0:
            return HoldOrder.HOLD
    if use_short:
        if should_vad_sell(position_count, signals):
            return HoldOrder.VAD_SELL
        if should_vad_buy(position_count, signals):
            return HoldOrder.VAD_BUY
        if position_count < 0:
            return HoldOrder.VAD_HOLD
    return HoldOrder.WAIT


def apply_order(data: dict[str, Any], order: HoldOrder) -> dict[str, Any]:
    data["ORDER"] = order.value
    if order in {HoldOrder.BUY, HoldOrder.VAD_BUY}:
        data["BUY DATE"] = data.get("DATE", "")
        data["BUY PRICE"] = data.get("BUY", 0)
    elif order in {HoldOrder.SELL, HoldOrder.VAD_SELL}:
        data["SELL DATE"] = data.get("DATE", "")
        data["SELL PRICE"] = data.get("BUY", 0)
    return data
