from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from prorealtime_v2.presentation.desktop.theme import Palette


class Card(ttk.Frame):
    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, style="Card.TFrame", padding=16, **kwargs)


class MetricCard(Card):
    def __init__(self, parent: tk.Widget, title: str, value: str = "0"):
        super().__init__(parent)
        self.value_var = tk.StringVar(value=value)
        ttk.Label(self, text=title, style="CardMuted.TLabel").pack(anchor="w")
        ttk.Label(self, textvariable=self.value_var, style="CardValue.TLabel").pack(anchor="w", pady=(4, 0))

    def set(self, value: object) -> None:
        self.value_var.set(str(value))


class PathPicker(ttk.Frame):
    def __init__(self, parent: tk.Widget, label: str, mode: str = "file"):
        super().__init__(parent)
        self.mode = mode
        self.value = tk.StringVar()
        ttk.Label(self, text=label).pack(anchor="w")
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(4, 0))
        ttk.Entry(row, textvariable=self.value).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Parcourir", command=self.pick, style="Secondary.TButton").pack(side="left", padx=(8, 0))

    def pick(self) -> None:
        if self.mode == "folder":
            selected = filedialog.askdirectory()
        else:
            selected = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("Tous les fichiers", "*.*")])
        if selected:
            self.value.set(selected)

    def path(self) -> Path | None:
        text = self.value.get().strip()
        return Path(text) if text else None


class LogConsole(Card):
    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        ttk.Label(self, text="Journal", style="CardTitle.TLabel").pack(anchor="w")
        self.text = tk.Text(self, height=12, wrap="word", bg="white", fg=Palette.text, relief="flat", font=("Consolas", 9))
        self.text.pack(fill="both", expand=True, pady=(8, 0))

    def write(self, message: str) -> None:
        self.text.insert("end", message.rstrip() + "\n")
        self.text.see("end")

    def clear(self) -> None:
        self.text.delete("1.0", "end")
