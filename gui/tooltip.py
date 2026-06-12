"""gui/tooltip.py — hover tooltip for any tkinter widget."""

import tkinter as tk
from tkinter import ttk


class ToolTip:
    """Tooltip for any regular tkinter widget. Shows after an optional delay."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 0):
        """
        delay: milliseconds before the tooltip appears (0 = instant).
        """
        self.widget     = widget
        self.text       = text
        self.delay      = delay
        self.tip_window = None
        self._after_id  = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        if self.delay:
            self._after_id = self.widget.after(self.delay, self.show)
        else:
            self.show()

    def _on_leave(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self.hide()

    def show(self, event=None):
        if self.tip_window or not self.text:
            return
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)

        label = tk.Label(
            tw, text=self.text, justify="left",
            background="#ffffe0", relief="solid", borderwidth=1,
            font=("Arial", 10), wraplength=300,
        )
        label.pack(ipadx=5, ipady=2)

        x = self.widget.winfo_pointerx() + 20
        y = self.widget.winfo_pointery() + 10
        tw.update_idletasks()
        w, h = tw.winfo_width(), tw.winfo_height()
        x = min(x, self.widget.winfo_screenwidth()  - w - 10)
        y = min(y, self.widget.winfo_screenheight() - h - 10)
        tw.wm_geometry(f"+{x}+{y}")

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class NotebookToolTip:
    """
    Tooltip for ttk.Notebook tabs. Since tabs aren't real widgets,
    this binds to the notebook itself and detects which tab is hovered.
    """

    TAB_TOOLTIPS = {
        "Random Wild":   "Randomly generate a wild Pokémon from a chosen created area.",
        "Wild":          "Manually pick a species and level to generate a wild Pokémon.",
        "Leveler":       "Level up a Pokémon.",
        "Trainer":       "Browse and edit trainer teams and add their Pokémon to the battle tracker.",
        "Fakemon":       "Create and edit custom Pokémon.",
        "Area Builder":  "Create and edit encounter areas used by the Random Wild tab.",
    }

    def __init__(self, notebook: ttk.Notebook, delay: int = 700):
        self.notebook   = notebook
        self.delay      = delay
        self.tip_window = None
        self._after_id  = None
        self._last_tab  = None

        notebook.bind("<Motion>",  self._on_motion)
        notebook.bind("<Leave>",   self._on_leave)

    def _get_tab_text(self, x: int, y: int) -> str | None:
        """Return the text of the tab at (x, y), or None if not over a tab."""
        try:
            # identify returns empty string when not over the tab strip
            if not self.notebook.identify(x, y):
                return None
            index = self.notebook.index(f"@{x},{y}")
            return self.notebook.tab(index, "text")
        except Exception:
            return None

    def _on_motion(self, event):
        tab_text = self._get_tab_text(event.x, event.y)

        # Same tab — do nothing
        if tab_text == self._last_tab:
            return

        # Different tab or moved off tabs — cancel pending and hide
        self._cancel()
        self.hide()
        self._last_tab = tab_text

        if tab_text and tab_text in self.TAB_TOOLTIPS:
            self._after_id = self.notebook.after(self.delay, lambda: self._show(tab_text))

    def _on_leave(self, event):
        self._cancel()
        self.hide()
        self._last_tab = None

    def _cancel(self):
        if self._after_id:
            self.notebook.after_cancel(self._after_id)
            self._after_id = None

    def _show(self, tab_text: str):
        self.hide()
        text = self.TAB_TOOLTIPS.get(tab_text, "")
        if not text:
            return

        self.tip_window = tw = tk.Toplevel(self.notebook)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)

        label = tk.Label(
            tw, text=text, justify="left",
            background="#ffffe0", relief="solid", borderwidth=1,
            font=("Arial", 10), wraplength=300,
        )
        label.pack(ipadx=5, ipady=2)

        x = self.notebook.winfo_pointerx() + 20
        y = self.notebook.winfo_pointery() + 10
        tw.update_idletasks()
        w, h = tw.winfo_width(), tw.winfo_height()
        x = min(x, self.notebook.winfo_screenwidth()  - w - 10)
        y = min(y, self.notebook.winfo_screenheight() - h - 10)
        tw.wm_geometry(f"+{x}+{y}")

    def hide(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
