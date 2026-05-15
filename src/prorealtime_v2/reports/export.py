"""Exports CSV/HTML pour les signaux."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from prorealtime_v2.models import Signal


def signals_to_dataframe(signals: list[Signal]) -> pd.DataFrame:
    """Convertit des signaux en DataFrame stable."""

    return pd.DataFrame([signal.to_dict() for signal in signals])


def write_signals_csv(signals: list[Signal], output_path: Path) -> Path:
    """Écrit les signaux en CSV UTF-8."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    signals_to_dataframe(signals).to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def write_html_report(
    signals: list[Signal], output_path: Path, title: str = "PROREALTIME V2"
) -> Path:
    """Écrit un rapport HTML simple et autonome."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = signals_to_dataframe(signals)
    table = (
        df.to_html(index=False, escape=True, classes="signals")
        if not df.empty
        else "<p>Aucun signal.</p>"
    )
    html = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .BUY {{ color: #047857; font-weight: 700; }}
    .SELL {{ color: #b91c1c; font-weight: 700; }}
    .HOLD {{ color: #6b7280; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {table}
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def read_signals_csv(input_path: Path) -> pd.DataFrame:
    """Lit un fichier de signaux avec validation minimale des colonnes."""

    df = pd.read_csv(input_path)
    required = {"ticker", "market", "action", "price", "reason", "created_at"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans {input_path}: {', '.join(sorted(missing))}")
    return df
