"""gui/battle_log.py — scrollable battle log panel."""

import tkinter as tk
from tkinter import ttk, scrolledtext

SEPARATOR = "─" * 30


class BattleLogFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        log_frame = ttk.LabelFrame(self, text="📜 Battle Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_widget = scrolledtext.ScrolledText(
            log_frame, width=40, height=30, wrap="word", state="disabled",
        )
        self.log_widget.pack(fill="both", expand=True)

        self.log_widget.tag_configure("separator", foreground="gray")
        self.log_widget.tag_configure("crit", foreground="green")
        self.log_widget.tag_configure("miss", foreground="red")
        self._first = True

    # ------------------------------------------------------------------

    def log(self, message: str, tag: str = None):
        self.log_widget.configure(state="normal")

        if not self._first:
            self.log_widget.insert("end", SEPARATOR + "\n", "separator")
        else:
            self._first = False

        if tag == "crit" and "(CRITICAL HIT!)" in message:
            self._insert_highlighted(message, "(CRITICAL HIT!)", "crit")
        elif tag == "miss" and "(CRITICAL MISS!)" in message:
            self._insert_highlighted(message, "(CRITICAL MISS!)", "miss")
        elif tag:
            self.log_widget.insert("end", f"{message}\n\n", tag)
        else:
            self.log_widget.insert("end", f"{message}\n\n")

        self.log_widget.see("end")
        self.log_widget.configure(state="disabled")

    def _insert_highlighted(self, message: str, keyword: str, tag: str):
        """Insert message with `keyword` coloured via `tag`."""
        parts = message.split(keyword)
        self.log_widget.insert("end", parts[0])
        self.log_widget.insert("end", keyword, tag)
        tail = parts[1] if len(parts) > 1 else ""
        self.log_widget.insert("end", f"{tail}\n\n")
