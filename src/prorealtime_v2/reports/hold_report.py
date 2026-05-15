"""Orchestrateur du rapport de holding, basé sur hold_daily_report_V4.py.

Entrée principale: Stocks list with QUARTER.csv enrichi par les analyses.
Sorties principales: rapport global, fichiers BUY/SELL/HOLD/VAD, liste de stocks mise à jour.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

import pandas as pd

from prorealtime_v2.data.yahoo import resample_ohlcv
from prorealtime_v2.indicators import enrich_v1_hold_indicators
from prorealtime_v2.strategies.hold_conditions import (
    DecisionContext,
    HoldOrder,
    apply_order,
    decide_order,
    determine_comment_and_opportunity,
)
from prorealtime_v2.validation import validate_ohlcv

LOGGER = logging.getLogger(__name__)


class MarketDataProvider(Protocol):
    def download(self, ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Retourne un DataFrame OHLCV."""


@dataclass(frozen=True)
class HoldReportConfig:
    start_date: str = "2020-01-01"
    end_date: str = "2099-12-31"
    minimum_history_months: int = 36
    minimum_us_price: float = 2.0
    minimum_price: float = 1.0
    use_long: bool = True
    use_short: bool = True
    write_outputs: bool = True
    send_email: bool = False


@dataclass(frozen=True)
class HoldReportPaths:
    stocks_file: Path
    signals_dir: Path
    analyse_dir: Path


@dataclass
class HoldReportResult:
    report: pd.DataFrame
    updated_stocks: pd.DataFrame
    failures: pd.DataFrame
    output_files: list[Path] = field(default_factory=list)


def load_stocks_universe(stocks_file: Path) -> pd.DataFrame:
    if not stocks_file.exists():
        raise FileNotFoundError(f"Fichier univers introuvable: {stocks_file}")
    return pd.read_csv(stocks_file, delimiter=";", encoding="utf-8-sig")


def normalize_position(value: object) -> int:
    if value is None or pd.isna(value):
        return 0
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped in {"", "nan", "none"} or "n" in stripped:
            return 0
        return int(float(stripped))
    return int(float(value))


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value: object, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)


def _mapped_stock_name(stock: str) -> str:
    mapping = {
        "AMP.MI": "AMP2.MI",
        "RED.MC": "RED1.MC",
        "UNI.MC": "UNI1.MC",
        "SOL.MC": "SOL1.MC",
        "SAB.MC": "SAB1.MC",
        "DIA.MC": "DIA1.MC",
        "DBG.PA": "DBG1.PA",
        "ACO-X.TO": "ACO.X.TO",
        "BBD-B.TO": "BBD.B.TO",
        "BEI-UN.TO": "BEI.UN.TO",
        "CAR-UN.TO": "CAR.UN.TO",
        "CCL-B.TO": "CCL.B.TO",
        "IIP-UN.TO": "IIP.UN.TO",
        "QBR-B.TO": "QBR.B.TO",
        "REI-UN.TO": "REI.UN.TO",
    }
    return mapping.get(stock, stock)


def _months_between(first_date: pd.Timestamp, last_date: datetime) -> int:
    return (last_date.year - first_date.year) * 12 + (last_date.month - first_date.month)


def _seed_report_row(row: pd.Series, actual_date: str, position_count: int) -> dict[str, object]:
    market = _text(row.get("MARKET"))
    stock_ref = _text(row.get("STOCK"))
    data: dict[str, object] = {
        "MARKET": market,
        "STOCK": _mapped_stock_name(stock_ref),
        "NAME": _text(row.get("SHORT NAME")),
        "SECTOR": _text(row.get("SECTOR")),
        "SCORE": _safe_int(row.get("SCORING")),
        "DEVISE": _text(row.get("DEVISE")),
        "SENS": _safe_float(row.get("SENS")),
        "DATE": actual_date,
        "BUY DATE": row.get("BUY DATE", ""),
        "BUY PRICE": row.get("BUY PRICE", ""),
        "SELL DATE": row.get("SELL DATE", ""),
        "SELL PRICE": row.get("SELL PRICE", ""),
        "EVOL": 0,
        "END DATE": "",
        "Nb j": "",
        "BUY": 0,
        "VAR %": 0,
        "SL": 0,
        "SL %": 0,
        "Time": 0,
        "Pos": position_count,
        "4001": _text(row.get("4001"))[:5],
        "4001%": row.get("4001%", 0),
        "4002": _text(row.get("4002"))[:5],
        "4002%": row.get("4002%", 0),
        "5001": _text(row.get("5001"))[:5],
        "5001%": row.get("5001%", 0),
        "Quarter": _text(row.get("QUARTER")),
        "Q OPP": _text(row.get("Q Opp")) if "Opp" in _text(row.get("Q Opp")) else "",
        "Month": _text(row.get("MONTH")),
        "M OPP": _text(row.get("M Opp")) if "Opp" in _text(row.get("M Opp")) else "",
    }
    if market == "INDEX":
        data["REGION"] = _text(row.get("TV SCREENER"))
    for key in ["qTS", "qKS", "qCloud", "mTS", "mKS", "mCloud"]:
        data[key] = _safe_int(row.get(key, 0))
    return data


def build_hold_report_row(row: pd.Series, provider: MarketDataProvider, config: HoldReportConfig, context: DecisionContext) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    stock_ref = _text(row.get("STOCK"))
    market = _text(row.get("MARKET"))
    name = _text(row.get("SHORT NAME"))
    score = _safe_int(row.get("SCORING"))
    position_count = normalize_position(row.get("Pos", 0))

    if market not in {"", "nan"} and "EURO ETF" in market and ".DE" not in stock_ref:
        return None, None
    if score < 0:
        return None, None

    data = _seed_report_row(row, str(context.today), position_count)

    try:
        ds_day_raw = validate_ohlcv(provider.download(stock_ref, config.start_date, config.end_date))
        ds_week_raw = resample_ohlcv(ds_day_raw, "W-FRI")
        if ds_week_raw.empty:
            return None, None
        if _months_between(pd.Timestamp(ds_week_raw.index[0]), datetime.today()) < config.minimum_history_months and position_count == 0:
            return None, None

        price = float(ds_week_raw["Close"].iloc[-1])
        if ("US" in market or "CANADA" in market) and price < config.minimum_us_price:
            return None, None
        if price < config.minimum_price:
            return None, None

        data["BUY"] = price
        data["Time"] = "Month"

        ds_week = enrich_v1_hold_indicators(ds_week_raw)
        week_signal = determine_comment_and_opportunity(name, ds_week, market)
        data["Week"], data["W OPP"], data["wTS"], data["wKS"], data["wCloud"] = week_signal.as_legacy_tuple()

        ds_day = enrich_v1_hold_indicators(ds_day_raw)
        data["VAR %"] = float(ds_day["Evolution_rate"].iloc[-1])
        day_signal = determine_comment_and_opportunity(name, ds_day, market)
        data["Day"], data["D OPP"], data["dTS"], data["dKS"], data["dCloud"] = day_signal.as_legacy_tuple()

        order = decide_order(position_count, data, weekly_trading=0, context=context, use_long=config.use_long, use_short=config.use_short)
        apply_order(data, order)
        if order == HoldOrder.WAIT:
            data["ORDER"] = ""

        data["STOCK2"] = _mapped_stock_name(stock_ref)
        ks = float(ds_day["KS"].iloc[-1])
        stop_loss = ks * 1.01 if "VAD" in _text(data.get("ORDER")) else ks * 0.99
        if market != "INDEX":
            data["SL"] = round(stop_loss, 2)
            data["SL %"] = round((1 - (round(stop_loss, 2) / price)) * -100, 2)

        updates = {
            "WEEK": data["Week"],
            "W Opp": data["W OPP"],
            "wTS": data["wTS"],
            "wKS": data["wKS"],
            "wCloud": data["wCloud"],
            "DAY": data["Day"],
            "D Opp": data["D OPP"],
            "dTS": data["dTS"],
            "dKS": data["dKS"],
            "dCloud": data["dCloud"],
        }
        if data.get("ORDER") in {"BUY", "VAD BUY"}:
            updates["BUY DATE"] = data["DATE"]
        if data.get("ORDER") in {"SELL", "VAD SELL"}:
            updates["SELL DATE"] = data["DATE"]
        return data, updates
    except Exception as exc:
        LOGGER.exception("Echec traitement %s", stock_ref)
        return None, {"STOCK": stock_ref, "MARKET": market, "ERROR": str(exc)}


def run_hold_report(markets: list[str], paths: HoldReportPaths, provider: MarketDataProvider, config: HoldReportConfig | None = None, context: DecisionContext | None = None) -> HoldReportResult:
    config = config or HoldReportConfig()
    context = context or DecisionContext.now()
    stocks = load_stocks_universe(paths.stocks_file)
    results: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for idx, row in stocks.iterrows():
        if _text(row.get("MARKET")) not in markets:
            continue
        report_row, update_or_failure = build_hold_report_row(row, provider, config, context)
        if report_row is not None:
            results.append(report_row)
            if update_or_failure:
                for column, value in update_or_failure.items():
                    stocks.loc[idx, column] = value
        elif update_or_failure:
            failures.append(update_or_failure)
    report = pd.DataFrame(results).round(2)
    failures_df = pd.DataFrame(failures)
    output_files: list[Path] = []
    if config.write_outputs:
        output_files = export_hold_report(report, stocks, failures_df, paths, "_".join(markets))
    return HoldReportResult(report, stocks, failures_df, output_files)


def export_hold_report(report: pd.DataFrame, stocks: pd.DataFrame, failures: pd.DataFrame, paths: HoldReportPaths, index_name: str) -> list[Path]:
    paths.signals_dir.mkdir(parents=True, exist_ok=True)
    paths.analyse_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.today().date().isoformat()
    written: list[Path] = []
    global_file = paths.signals_dir / f"{index_name} Holding stocks report.csv"
    report.to_csv(global_file, index=False, encoding="utf-8-sig")
    written.append(global_file)
    for order, filename in {"BUY": "buy signals", "SELL": "sell signals", "HOLD": "hold signals", "VAD SELL": "vad sell signals", "VAD BUY": "vad buy signals", "VAD HOLD": "vad hold signals"}.items():
        subset = report[report["ORDER"] == order] if "ORDER" in report.columns else pd.DataFrame()
        if not subset.empty:
            output = paths.signals_dir / f"{index_name} {filename} {today}.csv"
            subset.to_csv(output, index=False, encoding="utf-8-sig")
            written.append(output)
    analyse_report = paths.analyse_dir / f"{index_name} Holding stocks report.csv"
    report.to_csv(analyse_report, index=False, encoding="utf-8-sig")
    written.append(analyse_report)
    stocks_output = paths.analyse_dir / "Stocks list with QUARTER.csv"
    stocks.to_csv(stocks_output, index=False, sep=";", encoding="utf-8-sig")
    written.append(stocks_output)
    failures_output = paths.analyse_dir / f"{index_name} Stocks failed.csv"
    failures.to_csv(failures_output, index=False, encoding="utf-8-sig")
    written.append(failures_output)
    html_output = paths.signals_dir / f"{index_name} Holding stocks report.html"
    html_output.write_text(report.to_html(index=False) if not report.empty else "<p>Aucun signal.</p>", encoding="utf-8")
    written.append(html_output)
    return written
