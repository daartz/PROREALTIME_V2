from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import math


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return default
        return int(float(text.replace(",", ".")))
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        text = str(value).strip().replace(",", ".")
        if not text or text.lower() in {"nan", "none", "null"}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    return str(value).strip()


def contains(text: Any, token: str) -> bool:
    return token in to_text(text)


def normalize_position(value: Any) -> int:
    return to_int(value, 0)


def sell_in_period(sell_date: Any, period: str = "Monthly", today: datetime | None = None) -> bool:
    today = today or datetime.now()
    if not sell_date or str(sell_date).strip().lower() in {"", "nan", "none"}:
        return False

    if isinstance(sell_date, str):
        parsed = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(sell_date[:19], fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            return False
        sell_dt = parsed
    elif isinstance(sell_date, date):
        sell_dt = datetime.combine(sell_date, datetime.min.time())
    elif isinstance(sell_date, datetime):
        sell_dt = sell_date
    else:
        return False

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=31)).replace(day=1) - timedelta(days=1)

    if period == "Weekly":
        return start_of_week <= sell_dt <= end_of_week
    if period == "Monthly":
        return start_of_month <= sell_dt <= end_of_month
    return False
