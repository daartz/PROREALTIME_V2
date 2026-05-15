"""Registry des analyses autonomes pilotables depuis CLI/Tkinter."""

from __future__ import annotations

from prorealtime_v2.analysis.runners import (
    ANALYSES,
    AnalysisConfig,
    AnalysisDefinition,
    AnalysisResult,
    get_analysis,
    run_analysis,
)

__all__ = [
    "ANALYSES",
    "AnalysisConfig",
    "AnalysisDefinition",
    "AnalysisResult",
    "get_analysis",
    "run_analysis",
]
