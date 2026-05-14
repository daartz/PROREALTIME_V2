from __future__ import annotations

import argparse
from pathlib import Path

from prorealtime_v2.analysis.registry import ANALYSIS_SCRIPTS, list_available, run_analysis
from prorealtime_v2.domain.models import HoldReportConfig
from prorealtime_v2.reports.hold_report import run_hold_report


def _hold_report(args: argparse.Namespace) -> int:
    config = HoldReportConfig(
        stocks_file=Path(args.stocks_file),
        output_dir=Path(args.output_dir),
        prices_dir=Path(args.prices_dir) if args.prices_dir else None,
        markets=tuple(args.market or []),
        allow_long=not args.no_long,
        allow_short=not args.no_short,
        min_score=args.min_score,
    )
    result = run_hold_report(config)
    print("Résumé Hold/VAD")
    for key, value in sorted(result.summary.items()):
        print(f"- {key}: {value}")
    for path in result.output_files:
        print(f"Fichier généré: {path}")
    return 0


def _analysis(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.list:
        available = list_available(root)
        for item in available or ANALYSIS_SCRIPTS:
            status = "OK" if (root / item.filename).exists() else "absent"
            print(f"{item.key} | {status} | {item.filename} | {item.label}")
        return 0
    completed = run_analysis(root, args.key)
    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr)
    return completed.returncode


def _gui(_: argparse.Namespace) -> int:
    from prorealtime_v2.presentation.desktop.app import run_app

    run_app()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prorealtime-v2")
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("hold-report", help="Générer le rapport Hold/VAD")
    report.add_argument("--stocks-file", required=True)
    report.add_argument("--output-dir", required=True)
    report.add_argument("--prices-dir")
    report.add_argument("--market", action="append")
    report.add_argument("--min-score", type=int, default=0)
    report.add_argument("--no-long", action="store_true")
    report.add_argument("--no-short", action="store_true")
    report.set_defaults(func=_hold_report)

    analysis = sub.add_parser("analysis", help="Lister ou lancer les scripts ANALYSE_")
    analysis.add_argument("--root", required=True)
    analysis.add_argument("--list", action="store_true")
    analysis.add_argument("--key", default="strategy_config")
    analysis.set_defaults(func=_analysis)

    gui = sub.add_parser("gui", help="Lancer l'interface Tkinter")
    gui.set_defaults(func=_gui)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
