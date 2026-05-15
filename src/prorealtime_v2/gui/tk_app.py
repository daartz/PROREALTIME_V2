from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from prorealtime_v2.config import load_settings
from prorealtime_v2.data.yahoo import YahooFinanceProvider
from prorealtime_v2.logging_config import configure_logging
from prorealtime_v2.reports.hold_report import HoldReportConfig, HoldReportPaths, run_hold_report


class ProRealtimeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PROREALTIME V2 - Moteur Hold/VAD")
        self.geometry("1100x720")
        self.settings = load_settings()
        configure_logging(self.settings.log_level)
        self.events: queue.Queue[str] = queue.Queue()
        self.stocks_file = tk.StringVar(value=str(self.settings.data_dir / "Analyse" / "Stocks list with QUARTER.csv"))
        self.signals_dir = tk.StringVar(value=str(self.settings.signals_dir))
        self.analyse_dir = tk.StringVar(value=str(self.settings.data_dir / "Analyse"))
        self.markets = tk.StringVar(value="CANADA,US ETF,DJI,NASDAQ,SP500")
        self.start_date = tk.StringVar(value="2020-01-01")
        self.end_date = tk.StringVar(value="2099-12-31")
        self.write_outputs = tk.BooleanVar(value=True)
        self.use_long = tk.BooleanVar(value=True)
        self.use_short = tk.BooleanVar(value=True)
        self._build_layout()
        self.after(250, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True)
        run_tab = ttk.Frame(notebook, padding=12)
        logs_tab = ttk.Frame(notebook, padding=12)
        notebook.add(run_tab, text="Rapport Hold/VAD")
        notebook.add(logs_tab, text="Journal")
        self._build_run_tab(run_tab)
        self.log_text = tk.Text(logs_tab, height=30, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _build_run_tab(self, parent: ttk.Frame) -> None:
        form = ttk.LabelFrame(parent, text="Entrées / sorties", padding=10)
        form.pack(fill=tk.X)
        self._path_row(form, "Fichier stocks", self.stocks_file, True, 0)
        self._path_row(form, "Dossier signaux", self.signals_dir, False, 1)
        self._path_row(form, "Dossier analyse", self.analyse_dir, False, 2)
        ttk.Label(form, text="Marchés").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.markets, width=80).grid(row=3, column=1, sticky=tk.EW, pady=4)
        ttk.Label(form, text="Début").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.start_date, width=16).grid(row=4, column=1, sticky=tk.W, pady=4)
        ttk.Label(form, text="Fin").grid(row=4, column=1, padx=(160, 0), sticky=tk.W)
        ttk.Entry(form, textvariable=self.end_date, width=16).grid(row=4, column=1, padx=(200, 0), sticky=tk.W)
        options = ttk.LabelFrame(parent, text="Options moteur", padding=10)
        options.pack(fill=tk.X, pady=10)
        ttk.Checkbutton(options, text="Long BUY/SELL", variable=self.use_long).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(options, text="Short VAD", variable=self.use_short).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(options, text="Écrire les fichiers", variable=self.write_outputs).pack(side=tk.LEFT, padx=8)
        ttk.Button(parent, text="Lancer le rapport Hold/VAD", command=self._run_hold_report_thread).pack(anchor=tk.W, pady=8)
        ttk.Label(parent, text="Résumé").pack(anchor=tk.W)
        self.summary = tk.Text(parent, height=14, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=True)

    def _path_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, is_file: bool, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        ttk.Entry(parent, textvariable=variable, width=90).grid(row=row, column=1, sticky=tk.EW, pady=4)
        command = (lambda: self._choose_file(variable)) if is_file else (lambda: self._choose_dir(variable))
        ttk.Button(parent, text="Parcourir", command=command).grid(row=row, column=2, padx=6)
        parent.columnconfigure(1, weight=1)

    def _choose_file(self, variable: tk.StringVar) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Tous", "*.*")])
        if path:
            variable.set(path)

    def _choose_dir(self, variable: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            variable.set(path)

    def _run_hold_report_thread(self) -> None:
        threading.Thread(target=self._run_hold_report, daemon=True).start()

    def _run_hold_report(self) -> None:
        try:
            self.events.put("Démarrage rapport Hold/VAD...")
            markets = [market.strip() for market in self.markets.get().split(",") if market.strip()]
            paths = HoldReportPaths(Path(self.stocks_file.get()), Path(self.signals_dir.get()), Path(self.analyse_dir.get()))
            config = HoldReportConfig(self.start_date.get(), self.end_date.get(), use_long=self.use_long.get(), use_short=self.use_short.get(), write_outputs=self.write_outputs.get())
            result = run_hold_report(markets, paths, YahooFinanceProvider(), config)
            message = f"Rapport terminé: {len(result.report)} lignes\nErreurs: {len(result.failures)}\nFichiers:\n" + "\n".join(str(path) for path in result.output_files)
            self.events.put(message)
            self.summary.delete("1.0", tk.END)
            self.summary.insert(tk.END, message)
        except Exception as exc:
            self.events.put(f"ERREUR: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def _drain_events(self) -> None:
        while not self.events.empty():
            self.log_text.insert(tk.END, self.events.get() + "\n")
            self.log_text.see(tk.END)
        self.after(250, self._drain_events)

    def _on_close(self) -> None:
        if messagebox.askyesno("Quitter", "Fermer PROREALTIME V2 ?"):
            self.destroy()


def main() -> None:
    app = ProRealtimeApp()
    app.mainloop()
