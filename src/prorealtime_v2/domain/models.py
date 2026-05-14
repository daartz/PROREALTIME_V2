from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


ORDER_BUY = "BUY"
ORDER_SELL = "SELL"
ORDER_HOLD = "HOLD"
ORDER_VAD_SELL = "VAD SELL"
ORDER_VAD_BUY = "VAD BUY"
ORDER_VAD_HOLD = "VAD HOLD"


@dataclass(frozen=True)
class HoldReportConfig:
    stocks_file: Path
    output_dir: Path
    prices_dir: Path | None = None
    analyse_dir: Path | None = None
    markets: tuple[str, ...] = ()
    allow_long: bool = True
    allow_short: bool = True
    min_score: int = 0
    report_date: date = field(default_factory=date.today)
    write_html: bool = True
    write_csv: bool = True
    update_universe_copy: bool = True


@dataclass(frozen=True)
class TimeframeSignal:
    comment: str = "Wait"
    opportunity: str = ""
    ts: int = 0
    ks: int = 0
    cloud: int = 0


@dataclass
class DecisionRow:
    values: dict[str, Any]

    @property
    def order(self) -> str:
        return str(self.values.get("ORDER", ""))

    @property
    def stock(self) -> str:
        return str(self.values.get("STOCK", ""))


@dataclass(frozen=True)
class HoldReportResult:
    rows: list[DecisionRow]
    failures: list[dict[str, Any]]
    output_files: list[Path]
    summary: dict[str, int]


REQUIRED_STOCK_COLUMNS = {
    "STOCK",
    "MARKET",
    "SENS",
    "SCORING",
    "DEVISE",
    "Pos",
    "QUARTER",
    "Q Opp",
    "MONTH",
    "M Opp",
}

REPORT_COLUMNS = [
    "MARKET",
    "STOCK",
    "STOCK2",
    "NAME",
    "SECTOR",
    "SCORE",
    "DEVISE",
    "SENS",
    "DATE",
    "Pos",
    "ORDER",
    "BUY",
    "VAR %",
    "SL",
    "SL %",
    "Day",
    "D OPP",
    "dTS",
    "dKS",
    "dCloud",
    "Week",
    "W OPP",
    "wTS",
    "wKS",
    "wCloud",
    "Month",
    "M OPP",
    "mTS",
    "mKS",
    "mCloud",
    "Quarter",
    "Q OPP",
    "qTS",
    "qKS",
    "qCloud",
    "BUY DATE",
    "BUY PRICE",
    "SELL DATE",
    "SELL PRICE",
    "EVOL",
    "4001",
    "4001%",
    "4002",
    "4002%",
    "5001",
    "5001%",
]
