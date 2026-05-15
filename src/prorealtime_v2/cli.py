from __future__ import annotations

import argparse
from pathlib import Path

from prorealtime_v2.config import load_settings
from prorealtime_v2.data.yahoo import YahooFinanceProvider
from prorealtime_v2.gui.tk_app import main as gui_main
from prorealtime_v2.logging_config import configure_logging
from prorealtime_v2.reports.hold_report import HoldReportConfig, HoldReportPaths, run_hold_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PROREALTIME V2")
    sub = parser.add_subparsers(dest="command", required=True)

    hold = sub.add_parser("hold-report", help="Lancer le moteur Hold/VAD")
    hold.add_argument("--stocks-file", type=Path, required=True)
    hold.add_argument("--markets", required=True, help="Liste séparée par virgule: CANADA,DJI,NASDAQ")
    hold.add_argument("--signals-dir", type=Path, default=None)
    hold.add_argument("--analyse-dir", type=Path, default=None)
    hold.add_argument("--start", default="2020-01-01")
    hold.add_argument("--end", default="2099-12-31")
    hold.add_argument("--no-long", action="store_true")
    hold.add_argument("--no-short", action="store_true")
    hold.add_argument("--no-write", action="store_true")

    sub.add_parser("gui", help="Ouvrir l'interface Tkinter")
    return parser


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    configure_logging(settings.log_level)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "gui":
        gui_main()
        return 0

    if args.command == "hold-report":
        markets = [market.strip() for market in args.markets.split(",") if market.strip()]
        paths = HoldReportPaths(
            stocks_file=args.stocks_file,
            signals_dir=args.signals_dir or settings.signals_dir,
            analyse_dir=args.analyse_dir or settings.data_dir / "Analyse",
        )
        config = HoldReportConfig(
            start_date=args.start,
            end_date=args.end,
            use_long=not args.no_long,
            use_short=not args.no_short,
            write_outputs=not args.no_write,
        )
        result = run_hold_report(markets, paths, YahooFinanceProvider(), config)
        print(f"Rapport généré: {len(result.report)} lignes")
        print(f"Erreurs: {len(result.failures)}")
        for output in result.output_files:
            print(output)
        return 0

    parser.error(f"Commande inconnue: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
