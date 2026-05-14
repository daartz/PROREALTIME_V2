from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from prorealtime_v2.analysis.registry import ANALYSIS_SCRIPTS, list_available, run_analysis
from prorealtime_v2.domain.models import HoldReportConfig
from prorealtime_v2.presentation.desktop.theme import Palette, apply_theme
from prorealtime_v2.presentation.desktop.widgets import Card, LogConsole, MetricCard, PathPicker
from prorealtime_v2.reports.hold_report import run_hold_report


class CommandCenter(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PROREALTIME V2 — Command Center")
        self.geometry("1360x860")
        self.minsize(1180, 760)
        apply_theme(self)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.running = False
        self._build_layout()
        self.after(150, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=240)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.content = ttk.Frame(self, padding=22)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(1, weight=1)
        self._build_sidebar()
        self._build_pages()
        self.show_page("dashboard")

    def _build_sidebar(self) -> None:
        tk.Label(self.sidebar, text="PROREALTIME\nV2", bg=Palette.sidebar, fg="white", font=("Segoe UI", 20, "bold"), justify="left").pack(anchor="w", padx=22, pady=(28, 28))
        for key, label in [("dashboard", "Tableau de bord"), ("hold", "Rapport Hold/VAD"), ("analysis", "Analyses"), ("outputs", "Sorties & journal")]:
            btn = tk.Button(self.sidebar, text=label, anchor="w", bg=Palette.sidebar, fg="#d7e3f4", activebackground=Palette.sidebar_active, activeforeground="white", relief="flat", font=("Segoe UI", 11), padx=22, pady=12, command=lambda k=key: self.show_page(k))
            btn.pack(fill="x")
        tk.Label(self.sidebar, text="Mode sécurisé : aucune exécution IBKR réelle", bg=Palette.sidebar, fg="#9db0c8", wraplength=190, justify="left", font=("Segoe UI", 9)).pack(side="bottom", anchor="w", padx=22, pady=22)

    def _build_pages(self) -> None:
        self.header_title = ttk.Label(self.content, text="", style="Title.TLabel")
        self.header_title.grid(row=0, column=0, sticky="w")
        self.container = ttk.Frame(self.content)
        self.container.grid(row=1, column=0, sticky="nsew", pady=(18, 0))
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)
        self.pages: dict[str, ttk.Frame] = {}
        self._page_dashboard()
        self._page_hold()
        self._page_analysis()
        self._page_outputs()

    def _register_page(self, key: str) -> ttk.Frame:
        frame = ttk.Frame(self.container)
        frame.grid(row=0, column=0, sticky="nsew")
        self.pages[key] = frame
        return frame

    def show_page(self, key: str) -> None:
        titles = {"dashboard": "Tableau de bord", "hold": "Rapport Hold/VAD", "analysis": "Analyses ANALYSE_", "outputs": "Sorties & journal"}
        self.header_title.configure(text=titles[key])
        self.pages[key].tkraise()

    def _page_dashboard(self) -> None:
        page = self._register_page("dashboard")
        page.columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.metrics = {
            "TOTAL": MetricCard(page, "Lignes rapport"),
            "BUY": MetricCard(page, "BUY"),
            "SELL": MetricCard(page, "SELL"),
            "VAD SELL": MetricCard(page, "VAD SELL"),
            "FAILURES": MetricCard(page, "Échecs"),
        }
        for idx, card in enumerate(self.metrics.values()):
            card.grid(row=0, column=idx, sticky="ew", padx=6, pady=6)
        info = Card(page)
        info.grid(row=1, column=0, columnspan=5, sticky="nsew", padx=6, pady=16)
        ttk.Label(info, text="Centre de commande", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(info, text="Cette interface pilote le moteur Hold/VAD, génère les rapports et lance les analyses historiques sans modifier le code source.", style="CardMuted.TLabel").pack(anchor="w", pady=(6, 12))
        ttk.Button(info, text="Ouvrir le rapport Hold/VAD", style="Primary.TButton", command=lambda: self.show_page("hold")).pack(anchor="w")
        self.dashboard_log = LogConsole(page)
        self.dashboard_log.grid(row=2, column=0, columnspan=5, sticky="nsew", padx=6, pady=6)
        page.rowconfigure(2, weight=1)

    def _page_hold(self) -> None:
        page = self._register_page("hold")
        page.columnconfigure(0, weight=1)
        form = Card(page)
        form.grid(row=0, column=0, sticky="ew")
        form.columnconfigure((0, 1), weight=1)
        self.stocks_picker = PathPicker(form, "Fichier Stocks list with QUARTER.csv")
        self.stocks_picker.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        self.output_picker = PathPicker(form, "Dossier de sortie Signals", mode="folder")
        self.output_picker.grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        self.prices_picker = PathPicker(form, "Dossier historiques prix CSV", mode="folder")
        self.prices_picker.grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        self.markets_var = tk.StringVar(value="")
        box = ttk.Frame(form)
        box.grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Label(box, text="Marchés à traiter, séparés par virgules. Vide = tous").pack(anchor="w")
        ttk.Entry(box, textvariable=self.markets_var).pack(fill="x", pady=(4, 0))
        self.allow_long = tk.BooleanVar(value=True)
        self.allow_short = tk.BooleanVar(value=True)
        self.min_score = tk.IntVar(value=0)
        options = ttk.Frame(form)
        options.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=12)
        ttk.Checkbutton(options, text="Long", variable=self.allow_long).pack(side="left")
        ttk.Checkbutton(options, text="Short / VAD", variable=self.allow_short).pack(side="left", padx=(18, 0))
        ttk.Label(options, text="Score minimum").pack(side="left", padx=(28, 8))
        ttk.Spinbox(options, from_=-10, to=20, textvariable=self.min_score, width=6).pack(side="left")
        ttk.Button(form, text="Générer le rapport", style="Primary.TButton", command=self.run_hold_report_thread).grid(row=3, column=0, sticky="w", padx=6, pady=(8, 0))
        ttk.Button(form, text="Effacer le journal", style="Secondary.TButton", command=self._clear_logs).grid(row=3, column=1, sticky="e", padx=6, pady=(8, 0))

    def _page_analysis(self) -> None:
        page = self._register_page("analysis")
        page.columnconfigure(0, weight=1)
        card = Card(page)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)
        self.root_picker = PathPicker(card, "Dossier racine de l'ancien PROREALTIME", mode="folder")
        self.root_picker.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        self.analysis_key = tk.StringVar(value=ANALYSIS_SCRIPTS[0].key)
        ttk.Combobox(card, textvariable=self.analysis_key, values=[a.key for a in ANALYSIS_SCRIPTS], state="readonly").grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(card, text="Lister les analyses disponibles", style="Secondary.TButton", command=self.list_analysis).grid(row=2, column=0, sticky="w", padx=6, pady=6)
        ttk.Button(card, text="Lancer l'analyse", style="Primary.TButton", command=self.run_analysis_thread).grid(row=2, column=0, sticky="e", padx=6, pady=6)

    def _page_outputs(self) -> None:
        page = self._register_page("outputs")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        self.log_console = LogConsole(page)
        self.log_console.grid(row=0, column=0, sticky="nsew")

    def _log(self, message: str) -> None:
        self.log_console.write(message)
        self.dashboard_log.write(message)

    def _clear_logs(self) -> None:
        self.log_console.clear()
        self.dashboard_log.clear()

    def _set_running(self, value: bool) -> None:
        self.running = value

    def run_hold_report_thread(self) -> None:
        if self.running:
            messagebox.showwarning("Traitement en cours", "Un traitement est déjà en cours.")
            return
        stocks = self.stocks_picker.path()
        output = self.output_picker.path()
        if not stocks or not output:
            messagebox.showerror("Paramètres manquants", "Sélectionne le fichier stocks et le dossier de sortie.")
            return
        markets = tuple(x.strip() for x in self.markets_var.get().split(",") if x.strip())
        config = HoldReportConfig(stocks_file=stocks, output_dir=output, prices_dir=self.prices_picker.path(), markets=markets, allow_long=self.allow_long.get(), allow_short=self.allow_short.get(), min_score=self.min_score.get())
        self._set_running(True)
        self._log("Lancement du rapport Hold/VAD...")
        threading.Thread(target=self._worker_hold, args=(config,), daemon=True).start()

    def _worker_hold(self, config: HoldReportConfig) -> None:
        try:
            result = run_hold_report(config)
            self.events.put(("hold_done", result))
        except Exception as exc:
            self.events.put(("error", exc))

    def list_analysis(self) -> None:
        root = self.root_picker.path()
        if not root:
            messagebox.showerror("Dossier manquant", "Sélectionne le dossier racine PROREALTIME.")
            return
        available = list_available(root)
        self._log("Analyses disponibles :")
        for item in available:
            self._log(f"- {item.key} | {item.filename} | {item.label}")
        if not available:
            self._log("Aucun fichier ANALYSE_ connu trouvé dans ce dossier.")

    def run_analysis_thread(self) -> None:
        root = self.root_picker.path()
        if not root:
            messagebox.showerror("Dossier manquant", "Sélectionne le dossier racine PROREALTIME.")
            return
        self._set_running(True)
        key = self.analysis_key.get()
        self._log(f"Lancement analyse : {key}")
        threading.Thread(target=self._worker_analysis, args=(root, key), daemon=True).start()

    def _worker_analysis(self, root: Path, key: str) -> None:
        try:
            completed = run_analysis(root, key)
            self.events.put(("analysis_done", completed))
        except Exception as exc:
            self.events.put(("error", exc))

    def _poll_events(self) -> None:
        while not self.events.empty():
            kind, payload = self.events.get()
            self._set_running(False)
            if kind == "hold_done":
                result = payload
                for key, card in self.metrics.items():
                    card.set(result.summary.get(key, 0))
                self._log("Rapport terminé.")
                for path in result.output_files:
                    self._log(f"Fichier généré : {path}")
            elif kind == "analysis_done":
                completed = payload
                self._log(f"Analyse terminée. Code retour : {completed.returncode}")
                if completed.stdout:
                    self._log(completed.stdout)
                if completed.stderr:
                    self._log(completed.stderr)
            elif kind == "error":
                self._log(f"ERREUR : {payload}")
                messagebox.showerror("Erreur", str(payload))
        self.after(150, self._poll_events)

    def _on_close(self) -> None:
        if self.running and not messagebox.askyesno("Quitter", "Un traitement est en cours. Quitter quand même ?"):
            return
        if messagebox.askyesno("Quitter", "Fermer PROREALTIME V2 ?"):
            self.destroy()


def run_app() -> None:
    app = CommandCenter()
    app.mainloop()
