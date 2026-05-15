"""Analyses autonomes anciennement portées par les scripts ANALYSE_*.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import pandas as pd
import yfinance as yf

from prorealtime_v2.data.yahoo import YahooFinanceProvider, resample_ohlcv
from prorealtime_v2.indicators import add_v1_ichimoku, add_v1_macd, enrich_v1_hold_indicators
from prorealtime_v2.reports.hold_report import HoldReportConfig, HoldReportPaths, run_hold_report


class MarketDataProvider(Protocol):
    def download(self, ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Retourne un DataFrame OHLCV."""


@dataclass(frozen=True)
class AnalysisConfig:
    stocks_file: Path
    markets: tuple[str, ...]
    output_dir: Path
    start_date: str = "2020-01-01"
    end_date: str = "2099-12-31"
    max_tickers: int | None = None


@dataclass(frozen=True)
class AnalysisResult:
    key: str
    title: str
    rows: int
    output_files: list[Path] = field(default_factory=list)
    message: str = ""


@dataclass(frozen=True)
class AnalysisDefinition:
    key: str
    title: str
    description: str


ANALYSES: tuple[AnalysisDefinition, ...] = (
    AnalysisDefinition("backtest", "Backtest moteur Hold/VAD", "Exécute le moteur Hold/VAD V2 sans écriture puis agrège les ordres."),
    AnalysisDefinition("ks-break", "Instabilité autour de la Kijun", "Mesure croisements, proximité et fake breaks autour de KS."),
    AnalysisDefinition("ks-break-v2", "Qualité tendance / pullbacks KS", "Score tendance, distance à KS et qualité des pullbacks."),
    AnalysisDefinition("market-screener-score", "Score market screener", "Score synthétique basé sur tendance, MACD, cloud et volatilité."),
    AnalysisDefinition("analyst-forecast", "Prévisions analystes", "Écart au target mean Yahoo Finance quand disponible."),
    AnalysisDefinition("macd-stability", "Stabilité MACD", "Stabilité MACD day/week/month avec verdict swing."),
)


def get_analysis(key: str) -> AnalysisDefinition:
    for analysis in ANALYSES:
        if analysis.key == key:
            return analysis
    known = ", ".join(analysis.key for analysis in ANALYSES)
    raise KeyError(f"Analyse inconnue: {key}. Analyses disponibles: {known}")


def load_analysis_universe(config: AnalysisConfig) -> pd.DataFrame:
    if not config.stocks_file.exists():
        raise FileNotFoundError(f"Fichier univers introuvable: {config.stocks_file}")
    universe = pd.read_csv(config.stocks_file, delimiter=";", encoding="utf-8-sig")
    required = {"STOCK", "MARKET"}
    missing = required.difference(universe.columns)
    if missing:
        raise ValueError(f"Colonnes obligatoires manquantes: {', '.join(sorted(missing))}")
    filtered = universe[universe["MARKET"].astype(str).isin(config.markets)].copy()
    if config.max_tickers is not None:
        filtered = filtered.head(config.max_tickers)
    return filtered


def _ticker(row: pd.Series) -> str:
    return str(row["STOCK"]).strip()


def _base_row(row: pd.Series) -> dict[str, object]:
    return {
        "STOCK": _ticker(row),
        "MARKET": str(row.get("MARKET", "")),
        "SHORT NAME": str(row.get("SHORT NAME", _ticker(row))),
        "SECTOR": str(row.get("SECTOR", "")),
    }


def _write_result(config: AnalysisConfig, key: str, rows: list[dict[str, object]]) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    output = config.output_dir / f"{key}.csv"
    pd.DataFrame(rows).to_csv(output, index=False, encoding="utf-8-sig")
    return output


def _latest_indicators(data: pd.DataFrame) -> pd.Series:
    enriched = enrich_v1_hold_indicators(data)
    return enriched.dropna(subset=["Close"]).iloc[-1]


def _macd_stability(hist: pd.Series) -> float:
    values = hist.dropna().tolist()
    if len(values) < 5:
        return 0.0
    states = []
    for previous, current in zip(values, values[1:], strict=False):
        if current > 0 and current > previous:
            states.append("V++")
        elif current > 0:
            states.append("V+")
        elif current < 0 and current > previous:
            states.append("R+")
        else:
            states.append("R++")
    blocks: list[tuple[str, int]] = []
    current_state = states[0]
    count = 1
    for state in states[1:]:
        if state == current_state:
            count += 1
        else:
            blocks.append((current_state, count))
            current_state = state
            count = 1
    blocks.append((current_state, count))
    if len(blocks) <= 2:
        return 1.0
    penalty = sum(1 for previous, current, following in zip(blocks, blocks[1:], blocks[2:], strict=False) if current[1] <= 2 and previous[0] == following[0] and current[0] != previous[0])
    return round(1 - penalty / (len(blocks) - 2), 2)


def _trend_duration(hist: pd.Series) -> float:
    values = hist.dropna().tolist()
    if len(values) < 5:
        return 0.0
    durations: list[int] = []
    current_direction = values[1] > values[0]
    count = 1
    for previous, current in zip(values[1:], values[2:], strict=False):
        direction = current > previous
        if direction == current_direction:
            count += 1
        else:
            durations.append(count)
            current_direction = direction
            count = 1
    durations.append(count)
    return round(sum(durations) / len(durations), 2) if durations else 0.0


def _verdict(scores: list[float]) -> str:
    high = sum(score >= 0.75 for score in scores)
    mid = sum(0.6 <= score < 0.75 for score in scores)
    low = sum(score < 0.6 for score in scores)
    if high >= 2:
        return "Très bon candidat swing"
    if high == 1 and mid == 2:
        return "Moyennement stable"
    if low >= 1:
        return "Instable"
    return "Situation intermédiaire"


def run_backtest(config: AnalysisConfig, provider: MarketDataProvider | None = None) -> AnalysisResult:
    definition = get_analysis("backtest")
    provider = provider or YahooFinanceProvider()
    paths = HoldReportPaths(stocks_file=config.stocks_file, signals_dir=config.output_dir, analyse_dir=config.stocks_file.parent)
    report_config = HoldReportConfig(start_date=config.start_date, end_date=config.end_date, write_outputs=False)
    result = run_hold_report(list(config.markets), paths, provider, report_config)
    if result.report.empty or "ORDER" not in result.report.columns:
        rows: list[dict[str, object]] = []
    else:
        rows = [{"ORDER": order, "COUNT": int(count)} for order, count in result.report["ORDER"].value_counts().items()]
    output = _write_result(config, "backtest", rows)
    return AnalysisResult("backtest", definition.title, len(rows), [output], "Backtest V2 terminé")


def run_ks_break(config: AnalysisConfig, provider: MarketDataProvider | None = None, advanced: bool = False) -> AnalysisResult:
    key = "ks-break-v2" if advanced else "ks-break"
    definition = get_analysis(key)
    provider = provider or YahooFinanceProvider()
    rows: list[dict[str, object]] = []
    for _, row in load_analysis_universe(config).iterrows():
        try:
            data = add_v1_ichimoku(provider.download(_ticker(row), config.start_date, config.end_date))
            data = data.dropna(subset=["KS"]).tail(80)
            if data.empty:
                continue
            distance = ((data["Close"] - data["KS"]) / data["KS"]).abs()
            side = (data["Close"] > data["KS"]).astype(int)
            cross_count = int(side.diff().abs().fillna(0).sum())
            near_ks_ratio = float((distance <= 0.01).mean())
            trend_ratio = float((data["Close"] > data["KS"]).mean())
            result_row = _base_row(row) | {
                "cross_count": cross_count,
                "near_ks_ratio": round(near_ks_ratio, 4),
                "mean_distance_pct": round(float(distance.mean() * 100), 2),
                "instability_score": round(cross_count * 0.5 + near_ks_ratio * 10, 2),
            }
            if advanced:
                result_row |= {"trend_ratio": round(trend_ratio, 4), "trend_quality_score": round((1 - near_ks_ratio) * trend_ratio * 100, 2)}
            rows.append(result_row)
        except Exception as exc:
            rows.append(_base_row(row) | {"error": str(exc)})
    output = _write_result(config, key, rows)
    return AnalysisResult(key, definition.title, len(rows), [output], "Analyse KS autonome terminée")


def run_market_screener_score(config: AnalysisConfig, provider: MarketDataProvider | None = None) -> AnalysisResult:
    definition = get_analysis("market-screener-score")
    provider = provider or YahooFinanceProvider()
    rows: list[dict[str, object]] = []
    for _, row in load_analysis_universe(config).iterrows():
        try:
            latest = _latest_indicators(provider.download(_ticker(row), config.start_date, config.end_date))
            close = float(latest["Close"])
            ks = float(latest["KS"])
            hist = float(latest["hist"])
            cloud_top = max(float(latest.get("SSA", 0) or 0), float(latest.get("SSB", 0) or 0))
            score = 0
            score += 35 if close > ks else -20
            score += 30 if hist > 0 else -15
            score += 25 if close > cloud_top else 0
            score += 10 if float(latest.get("ad_diff", 0) or 0) > 0 else 0
            rows.append(_base_row(row) | {"Close": close, "KS": ks, "hist": hist, "score": score})
        except Exception as exc:
            rows.append(_base_row(row) | {"error": str(exc)})
    output = _write_result(config, "market-screener-score", rows)
    return AnalysisResult("market-screener-score", definition.title, len(rows), [output], "Score screener terminé")


def run_analyst_forecast(config: AnalysisConfig) -> AnalysisResult:
    definition = get_analysis("analyst-forecast")
    rows: list[dict[str, object]] = []
    for _, row in load_analysis_universe(config).iterrows():
        try:
            info = yf.Ticker(_ticker(row)).info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            target = info.get("targetMeanPrice")
            gap = None if not price or not target else (float(target) - float(price)) / float(price) * 100
            rows.append(_base_row(row) | {"current_price": price, "target_mean": target, "target_gap_pct": None if gap is None else round(gap, 2), "recommendation": info.get("recommendationKey")})
        except Exception as exc:
            rows.append(_base_row(row) | {"error": str(exc)})
    output = _write_result(config, "analyst-forecast", rows)
    return AnalysisResult("analyst-forecast", definition.title, len(rows), [output], "Prévisions analystes terminées")


def run_macd_stability(config: AnalysisConfig, provider: MarketDataProvider | None = None) -> AnalysisResult:
    definition = get_analysis("macd-stability")
    provider = provider or YahooFinanceProvider()
    rows: list[dict[str, object]] = []
    for _, row in load_analysis_universe(config).iterrows():
        try:
            day = provider.download(_ticker(row), config.start_date, config.end_date)
            week = resample_ohlcv(day, "W")
            month = resample_ohlcv(day, "M")
            frames = [add_v1_macd(frame) for frame in (day, week, month)]
            scores = [_macd_stability(frame["hist"]) for frame in frames]
            durations = [_trend_duration(frame["hist"]) for frame in frames]
            rows.append(_base_row(row) | {"Stability_Day": scores[0], "Stability_Week": scores[1], "Stability_Month": scores[2], "Trend_Duration_Day": durations[0], "Trend_Duration_Week": durations[1], "Trend_Duration_Month": durations[2], "Verdict": _verdict(scores)})
        except Exception as exc:
            rows.append(_base_row(row) | {"error": str(exc)})
    output = _write_result(config, "macd-stability", rows)
    return AnalysisResult("macd-stability", definition.title, len(rows), [output], "Stabilité MACD terminée")


def run_analysis(key: str, config: AnalysisConfig, provider: MarketDataProvider | None = None) -> AnalysisResult:
    if key == "backtest":
        return run_backtest(config, provider)
    if key == "ks-break":
        return run_ks_break(config, provider, advanced=False)
    if key == "ks-break-v2":
        return run_ks_break(config, provider, advanced=True)
    if key == "market-screener-score":
        return run_market_screener_score(config, provider)
    if key == "analyst-forecast":
        return run_analyst_forecast(config)
    if key == "macd-stability":
        return run_macd_stability(config, provider)
    get_analysis(key)
    raise AssertionError("Analyse connue mais non routée")
