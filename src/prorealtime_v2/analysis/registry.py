from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys


@dataclass(frozen=True)
class AnalysisScript:
    key: str
    filename: str
    label: str
    description: str


ANALYSIS_SCRIPTS = [
    AnalysisScript("strategy_config", "ANALYSE_strategy_config_tester.py", "Testeur configurations stratégie", "Compare les configurations Ichimoku/MACD et profils de backtest."),
    AnalysisScript("ks", "ANALYSE_KS.py", "Analyse Kijun/KS", "Étudie les conditions liées à la Kijun et aux cassures."),
    AnalysisScript("market_screener", "ANALYSE_market_screener.py", "Screener marché", "Analyse large des marchés et univers."),
    AnalysisScript("forecast", "ANALYSE_forecast.py", "Prévisions", "Analyse prévisionnelle et suivi de tendance."),
    AnalysisScript("macd_stability", "ANALYSE_macd_stability.py", "Stabilité MACD", "Contrôle la stabilité des signaux MACD."),
]


def list_available(root: Path) -> list[AnalysisScript]:
    return [item for item in ANALYSIS_SCRIPTS if (root / item.filename).exists()]


def run_analysis(root: Path, key: str) -> subprocess.CompletedProcess[str]:
    matches = [item for item in ANALYSIS_SCRIPTS if item.key == key]
    if not matches:
        raise ValueError(f"Analyse inconnue : {key}")
    script = root / matches[0].filename
    if not script.exists():
        raise FileNotFoundError(f"Script introuvable : {script}")
    return subprocess.run([sys.executable, str(script)], cwd=str(root), text=True, capture_output=True, check=False)
