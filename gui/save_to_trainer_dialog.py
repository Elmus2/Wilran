"""
gui/save_to_trainer_dialog.py
A small modal dialog that lets the user pick an existing trainer
or create a new one, then saves the given Pokémon to that trainer.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from stores.trainer_store import (
    get_trainer_names,
    create_trainer,
    add_pokemon_to_trainer,
)

NEW_TRAINER_OPTION = "＋ New Trainer..."


def open_save_dialog(parent: tk.Widget, pokemon: dict):
    """
    Open the Save to Trainer dialog.
    Blocks until the user confirms or cancels.
    """
    dialog = _SaveToTrainerDialog(parent, pokemon)
    dialog.run()


class _SaveToTrainerDialog:
    def __init__(self, parent: tk.Widget, pokemon: dict):
        self.pokemon = pokemon

        self.win = tk.Toplevel(parent)
        self.win.title("Save to Trainer")
        self.win.geometry("300x140")
        self.win.resizable(False, False)
        self.win.grab_set()

        self._build()

    def _build(self):
        tk.Label(
            self.win, text="Choose a trainer:",
            font=("Arial", 10),
        ).pack(pady=(12, 4))

        self.trainer_var = tk.StringVar()
        names = get_trainer_names()
        options = names + [NEW_TRAINER_OPTION]

        self.dropdown = ttk.Combobox(
            self.win, textvariable=self.trainer_var,
            values=options, state="readonly", width=28,
        )
        self.dropdown.pack(pady=4)
        if names:
            self.dropdown.set(names[0])
        else:
            self.dropdown.set(NEW_TRAINER_OPTION)

        btn_frame = tk.Frame(self.win)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Save", width=10,
            command=self._on_save,
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame, text="Cancel", width=10,
            command=self.win.destroy,
        ).pack(side="left", padx=5)

    def _on_save(self):
        choice = self.trainer_var.get()
        if not choice:
            return

        if choice == NEW_TRAINER_OPTION:
            name = self._prompt_new_trainer()
            if not name:
                return          # user cancelled the name prompt
        else:
            name = choice

        try:
            add_pokemon_to_trainer(name, self.pokemon)
            messagebox.showinfo(
                "Saved",
                f"{self.pokemon.get('name', 'Pokémon')} saved to {name}.",
                parent=self.win,
            )
            self.win.destroy()
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self.win)

    def _prompt_new_trainer(self) -> str | None:
        """Open a second small dialog to get the new trainer's name."""
        name_win = tk.Toplevel(self.win)
        name_win.title("New Trainer")
        name_win.geometry("260x110")
        name_win.resizable(False, False)
        name_win.grab_set()

        tk.Label(name_win, text="Trainer name:").pack(pady=(12, 4))

        name_var = tk.StringVar()
        entry = tk.Entry(name_win, textvariable=name_var, width=24)
        entry.pack()
        entry.focus_set()

        result = {"name": None}

        def confirm():
            n = name_var.get().strip()
            if not n:
                messagebox.showwarning(
                    "Invalid", "Name cannot be blank.", parent=name_win
                )
                return
            try:
                create_trainer(n)
                result["name"] = n
                name_win.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=name_win)

        btn_frame = tk.Frame(name_win)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Create", width=8, command=confirm).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=8, command=name_win.destroy).pack(side="left", padx=4)

        entry.bind("<Return>", lambda e: confirm())
        name_win.wait_window()

        # Refresh the main dropdown to include the new trainer
        if result["name"]:
            names   = get_trainer_names()
            options = names + [NEW_TRAINER_OPTION]
            self.dropdown.configure(values=options)
            self.trainer_var.set(result["name"])

        return result["name"]

    def run(self):
        self.win.wait_window()
