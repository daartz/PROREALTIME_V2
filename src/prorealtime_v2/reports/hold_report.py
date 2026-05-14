from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from prorealtime_v2.domain.models import DecisionRow, HoldReportConfig, HoldReportResult, REPORT_COLUMNS, REQUIRED_STOCK_COLUMNS
from prorealtime_v2.indicators.technical import enrich_indicators, weekly_from_daily
from prorealtime_v2.strategies.hold_rules import apply_order_rule
from prorealtime_v2.strategies.hold_signals import determine_comment_and_opportunity
from prorealtime_v2.utils.parsing import normalize_position, to_float, to_int, to_text


def _read_csv(path: Path) -> pd.DataFrame:
    for sep in (";", ","):
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
            if len(df.columns) > 1:
                return df
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=sep, encoding="ISO-8859-1")
            if len(df.columns) > 1:
                return df
    raise ValueError(f"Impossible de lire le fichier CSV : {path}")


def validate_stocks_file(df: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_STOCK_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError("Colonnes obligatoires absentes : " + ", ".join(missing))


def _history_file(prices_dir: Path, stock: str) -> Path | None:
    candidates = [
        prices_dir / f"{stock}.csv",
        prices_dir / f"{stock}_daily.csv",
        prices_dir / f"{stock}_2020-01-01_2099-12-31.csv",
    ]
    return next((p for p in candidates if p.exists()), None)


def _base_row(row: pd.Series, report_date: date) -> dict[str, Any]:
    stock = to_text(row.get("STOCK"))
    name = to_text(row.get("SHORT NAME")) or to_text(row.get("NAME"))
    position = normalize_position(row.get("Pos"))
    data: dict[str, Any] = {
        "MARKET": to_text(row.get("MARKET")),
        "STOCK": stock,
        "STOCK2": stock,
        "NAME": name,
        "SECTOR": to_text(row.get("SECTOR")),
        "SCORE": to_int(row.get("SCORING")),
        "DEVISE": to_text(row.get("DEVISE")),
        "SENS": to_float(row.get("SENS")),
        "DATE": str(report_date),
        "Pos": position,
        "ORDER": "",
        "BUY": 0,
        "VAR %": 0,
        "SL": 0,
        "SL %": 0,
        "BUY DATE": to_text(row.get("BUY DATE")),
        "BUY PRICE": to_float(row.get("BUY PRICE")),
        "SELL DATE": to_text(row.get("SELL DATE")),
        "SELL PRICE": to_float(row.get("SELL PRICE")),
        "EVOL": 0,
        "4001": to_text(row.get("4001"))[:5],
        "4001%": to_float(row.get("4001%")),
        "4002": to_text(row.get("4002"))[:5],
        "4002%": to_float(row.get("4002%")),
        "5001": to_text(row.get("5001"))[:5],
        "5001%": to_float(row.get("5001%")),
        "Quarter": to_text(row.get("QUARTER")),
        "Q OPP": to_text(row.get("Q Opp")) if "Opp" in to_text(row.get("Q Opp")) else "",
        "qTS": to_int(row.get("qTS")),
        "qKS": to_int(row.get("qKS")),
        "qCloud": to_int(row.get("qCloud")),
        "Month": to_text(row.get("MONTH")),
        "M OPP": to_text(row.get("M Opp")) if "Opp" in to_text(row.get("M Opp")) else "",
        "mTS": to_int(row.get("mTS")),
        "mKS": to_int(row.get("mKS")),
        "mCloud": to_int(row.get("mCloud")),
        "Day": to_text(row.get("DAY")),
        "D OPP": to_text(row.get("D Opp")) if "Opp" in to_text(row.get("D Opp")) else "",
        "dTS": to_int(row.get("dTS")),
        "dKS": to_int(row.get("dKS")),
        "dCloud": to_int(row.get("dCloud")),
        "Week": to_text(row.get("WEEK")),
        "W OPP": to_text(row.get("W Opp")) if "Opp" in to_text(row.get("W Opp")) else "",
        "wTS": to_int(row.get("wTS")),
        "wKS": to_int(row.get("wKS")),
        "wCloud": to_int(row.get("wCloud")),
    }
    return data


def _apply_price_history(data: dict[str, Any], config: HoldReportConfig) -> None:
    if not config.prices_dir:
        return
    history = _history_file(config.prices_dir, data["STOCK"])
    if history is None:
        return
    daily = _read_csv(history)
    daily = enrich_indicators(daily)
    weekly = enrich_indicators(weekly_from_daily(daily))
    if daily.empty or weekly.empty:
        return

    d_sig = determine_comment_and_opportunity(daily)
    w_sig = determine_comment_and_opportunity(weekly)
    data.update({"Day": d_sig.comment, "D OPP": d_sig.opportunity, "dTS": d_sig.ts, "dKS": d_sig.ks, "dCloud": d_sig.cloud})
    data.update({"Week": w_sig.comment, "W OPP": w_sig.opportunity, "wTS": w_sig.ts, "wKS": w_sig.ks, "wCloud": w_sig.cloud})
    price = to_float(daily["Close"].iloc[-1])
    data["BUY"] = price
    data["VAR %"] = round(to_float(daily["Evolution_rate"].iloc[-1]), 2)
    ks = to_float(daily["KS"].iloc[-1])
    if ks > 0 and price > 0:
        stop = ks * (1.01 if "VAD" in to_text(data.get("ORDER")) else 0.99)
        data["SL"] = round(stop, 2)
        data["SL %"] = round((1 - (stop / price)) * -100, 2)


def _write_outputs(config: HoldReportConfig, rows: list[DecisionRow], failures: list[dict[str, Any]]) -> list[Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = config.report_date.strftime("%Y%m%d")
    df = pd.DataFrame([r.values for r in rows])
    ordered = [c for c in REPORT_COLUMNS if c in df.columns] + [c for c in df.columns if c not in REPORT_COLUMNS]
    df = df[ordered] if not df.empty else df
    output_files: list[Path] = []

    if config.write_csv:
        csv_path = config.output_dir / f"hold_vad_report_{stamp}.csv"
        df.to_csv(csv_path, sep=";", index=False, encoding="utf-8-sig")
        output_files.append(csv_path)

    if config.write_html:
        html_path = config.output_dir / f"hold_vad_report_{stamp}.html"
        html_path.write_text(df.to_html(index=False, escape=False), encoding="utf-8")
        output_files.append(html_path)

    if failures:
        fail_path = config.output_dir / f"hold_vad_failures_{stamp}.csv"
        pd.DataFrame(failures).to_csv(fail_path, sep=";", index=False, encoding="utf-8-sig")
        output_files.append(fail_path)

    return output_files


def run_hold_report(config: HoldReportConfig) -> HoldReportResult:
    stocks = _read_csv(config.stocks_file)
    validate_stocks_file(stocks)
    rows: list[DecisionRow] = []
    failures: list[dict[str, Any]] = []
    selected_markets = set(config.markets)

    for _, source_row in stocks.iterrows():
        try:
            market = to_text(source_row.get("MARKET"))
            if selected_markets and market not in selected_markets:
                continue
            score = to_int(source_row.get("SCORING"))
            stock = to_text(source_row.get("STOCK"))
            if score < config.min_score:
                continue
            if market == "EURO ETF" and ".DE" not in stock:
                continue

            data = _base_row(source_row, config.report_date)
            _apply_price_history(data, config)
            position = normalize_position(source_row.get("Pos"))
            apply_order_rule(data, position, allow_long=config.allow_long, allow_short=config.allow_short)
            rows.append(DecisionRow(values=data))
        except Exception as exc:
            failures.append({"STOCK": to_text(source_row.get("STOCK")), "MARKET": to_text(source_row.get("MARKET")), "ERROR": str(exc)})

    output_files = _write_outputs(config, rows, failures)
    summary_counter = Counter(r.order or "NO ORDER" for r in rows)
    summary = dict(summary_counter)
    summary["TOTAL"] = len(rows)
    summary["FAILURES"] = len(failures)
    return HoldReportResult(rows=rows, failures=failures, output_files=output_files, summary=summary)
