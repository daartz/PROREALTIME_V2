from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Palette:
    bg = "#f4f7fb"
    sidebar = "#102033"
    sidebar_active = "#1f6feb"
    card = "#ffffff"
    text = "#152238"
    muted = "#667085"
    border = "#d9e2ef"
    primary = "#1f6feb"
    success = "#0f9f6e"
    danger = "#d92d20"
    warning = "#f79009"


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=Palette.bg)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=Palette.bg)
    style.configure("Card.TFrame", background=Palette.card, relief="flat")
    style.configure("Sidebar.TFrame", background=Palette.sidebar)
    style.configure("TLabel", background=Palette.bg, foreground=Palette.text, font=("Segoe UI", 10))
    style.configure("Title.TLabel", background=Palette.bg, foreground=Palette.text, font=("Segoe UI", 20, "bold"))
    style.configure("Subtitle.TLabel", background=Palette.bg, foreground=Palette.muted, font=("Segoe UI", 10))
    style.configure("CardTitle.TLabel", background=Palette.card, foreground=Palette.text, font=("Segoe UI", 12, "bold"))
    style.configure("CardValue.TLabel", background=Palette.card, foreground=Palette.text, font=("Segoe UI", 22, "bold"))
    style.configure("CardMuted.TLabel", background=Palette.card, foreground=Palette.muted, font=("Segoe UI", 9))
    style.configure("Primary.TButton", background=Palette.primary, foreground="white", padding=(14, 8), font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton", background=[("active", "#1557c0")])
    style.configure("Secondary.TButton", background="#e9eef8", foreground=Palette.text, padding=(12, 8))
    style.configure("Danger.TButton", background=Palette.danger, foreground="white", padding=(12, 8))
    style.configure("TEntry", fieldbackground="white", bordercolor=Palette.border, padding=6)
    style.configure("TCombobox", fieldbackground="white", bordercolor=Palette.border, padding=6)
    style.configure("Treeview", rowheight=28, background="white", fieldbackground="white", foreground=Palette.text)
    style.configure("Treeview.Heading", background="#eef3fb", foreground=Palette.text, font=("Segoe UI", 9, "bold"))
