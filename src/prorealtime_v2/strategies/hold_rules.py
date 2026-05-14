from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from prorealtime_v2.domain.models import (
    ORDER_BUY,
    ORDER_HOLD,
    ORDER_SELL,
    ORDER_VAD_BUY,
    ORDER_VAD_HOLD,
    ORDER_VAD_SELL,
)
from prorealtime_v2.utils.parsing import contains, to_float, to_int, to_text


@dataclass(frozen=True)
class CalendarContext:
    weekday: int
    day_of_month: int

    @classmethod
    def today(cls) -> "CalendarContext":
        now = datetime.today()
        return cls(weekday=now.weekday(), day_of_month=now.day)


def should_sell(position_count: int, s: dict[str, Any], context: CalendarContext | None = None) -> bool:
    context = context or CalendarContext.today()
    market = to_text(s.get("MARKET"))
    if market == "INDEX":
        return contains(s.get("Week"), "Exit >>") or (
            contains(s.get("Week"), "Exit >") and contains(s.get("Month"), "Exit")
        ) or (to_int(s.get("wTS")) < 0 and context.weekday > 3 and context.day_of_month > 5)
    if position_count <= 0:
        return False
    return to_int(s.get("dKS")) < 0 and to_int(s.get("dTS")) < 0


def should_buy(position_count: int, s: dict[str, Any]) -> bool:
    market = to_text(s.get("MARKET"))
    if market == "INDEX":
        return contains(s.get("Week"), "Entry")
    if market == "US IPO" or position_count != 0:
        return False
    if any("OFF" in to_text(s.get(k)) for k in ("Day", "Week", "Month")):
        return False
    if to_int(s.get("wCloud")) <= 0 or to_int(s.get("dCloud")) <= 0:
        return False
    if to_float(s.get("SENS")) > 50:
        return False

    return (
        contains(s.get("Week"), "Entry")
        and contains(s.get("Day"), "Entry")
        and to_int(s.get("dKS")) > 0
        and to_int(s.get("wTS")) > 0
        and (
            to_int(s.get("wKS")) == 1
            or to_int(s.get("wTS")) == 1
            or to_text(s.get("W OPP")) == "Opp"
            or to_int(s.get("dKS")) >= 1
            or to_int(s.get("dTS")) == 1
            or to_text(s.get("D OPP")) == "Opp"
        )
    )


def should_vad_buy(position_count: int, s: dict[str, Any], context: CalendarContext | None = None) -> bool:
    context = context or CalendarContext.today()
    market = to_text(s.get("MARKET"))
    if market == "INDEX":
        return (
            contains(s.get("Week"), "Entry >")
            and contains(s.get("Month"), "Entry")
            and context.weekday > 3
            and context.day_of_month > 5
        ) or contains(s.get("Week"), "Entry >>")
    if position_count >= 0:
        return False
    return to_int(s.get("dTS")) > 0


def should_vad_sell(position_count: int, s: dict[str, Any], context: CalendarContext | None = None) -> bool:
    context = context or CalendarContext.today()
    market = to_text(s.get("MARKET"))
    if market in {"PEA", "EUROPE", "US IPO", "EURO ETF", "EUROFORCE"}:
        return False
    if market == "INDEX":
        return contains(s.get("Week"), "Exit >>") or (
            contains(s.get("Week"), "Exit") and contains(s.get("Month"), "Exit") and context.weekday > 3
        )
    if position_count != 0:
        return False
    if to_int(s.get("wCloud")) >= 0 or to_int(s.get("dCloud")) >= 0:
        return False
    if to_float(s.get("SENS")) > 40:
        return False

    return (
        contains(s.get("Week"), "Exit")
        and contains(s.get("Month"), "Exit")
        and contains(s.get("Day"), "Exit")
        and to_int(s.get("dKS")) < 0
        and to_int(s.get("wTS")) < 0
        and to_int(s.get("dTS")) < 0
        and (to_text(s.get("W OPP")) == "VAD Opp" or to_int(s.get("wTS")) == -1 or to_int(s.get("wKS")) == -1)
    )


def apply_order_rule(data: dict[str, Any], position_count: int, allow_long: bool = True, allow_short: bool = True) -> dict[str, Any]:
    if allow_long and should_sell(position_count, data):
        data["ORDER"] = ORDER_SELL
        data["SELL DATE"] = data.get("DATE", "")
        data["SELL PRICE"] = data.get("BUY", 0)
    elif allow_long and should_buy(position_count, data):
        data["ORDER"] = ORDER_BUY
        data["BUY DATE"] = data.get("DATE", "")
        data["BUY PRICE"] = data.get("BUY", 0)
    elif position_count > 0:
        data["ORDER"] = ORDER_HOLD
    elif allow_short and should_vad_sell(position_count, data):
        data["ORDER"] = ORDER_VAD_SELL
        data["SELL DATE"] = data.get("DATE", "")
        data["SELL PRICE"] = data.get("BUY", 0)
    elif allow_short and should_vad_buy(position_count, data):
        data["ORDER"] = ORDER_VAD_BUY
        data["BUY DATE"] = data.get("DATE", "")
        data["BUY PRICE"] = data.get("BUY", 0)
    elif position_count < 0:
        data["ORDER"] = ORDER_VAD_HOLD
    else:
        data["ORDER"] = ""
    return data
