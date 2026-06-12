"""
gui/trainer_tab.py
TrainerTab: browse trainers, view their Pokémon, add to tracker,
and remove Pokémon from a trainer's list.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from stores.trainer_store import (
    get_trainer_names,
    get_trainer_pokemon,
    remove_pokemon_from_trainer,
    load_trainers,
    delete_trainer,
)


def _pokemon_label(pokemon: dict) -> str:
    """Format a Pokémon entry as 'Rattata (Lv 2) - Female'."""
    name   = pokemon.get("name", "Unknown")
    level  = pokemon.get("level", "?")
    gender = pokemon.get("gender", "")
    label  = f"{name} (Lv {level})"
    if gender:
        label += f" - {gender}"
    return label


class TrainerTab(ttk.Frame):
    def __init__(self, parent, battler_frame):
        super().__init__(parent, padding=10)
        self.battler_frame   = battler_frame
        self._trainer_pokemon = []   # current trainer's pokemon list

        self._build_trainer_selector()
        self._build_pokemon_list()
        self._build_remove_section()
        self._refresh_trainers()  # safe to call now — all widgets exist

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_trainer_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 6))

        tk.Label(frame, text="Trainer:").pack(anchor="w")

        self.trainer_var = tk.StringVar()
        self.trainer_box = ttk.Combobox(
            frame, textvariable=self.trainer_var,
            state="readonly", width=24,
        )
        self.trainer_box.pack(anchor="w", pady=(0, 4))
        self.trainer_box.bind("<<ComboboxSelected>>", self._on_trainer_selected)

        self.refresh_btn = tk.Button(
            frame, text="🔄 Refresh", command=self._refresh_trainers,
        )
        self.refresh_btn.pack(side="left", anchor="w")
        self.refresh_btn.bind("<Return>", lambda e: self._refresh_trainers())

        self.delete_trainer_btn = tk.Button(
            frame, text="🗑️ Delete Trainer", fg="red",
            command=self._delete_trainer,
        )
        self.delete_trainer_btn.pack(side="left", padx=(8, 0), anchor="w")
        self.delete_trainer_btn.bind("<Return>", lambda e: self._delete_trainer())

    def _build_pokemon_list(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 6))

        self.add_all_btn = ttk.Button(
            frame, text="➕ Add All to Tracker",
            command=self._add_all, state="disabled",
        )
        self.add_all_btn.pack(anchor="w", pady=(0, 4))
        self.add_all_btn.bind("<Return>", lambda e: self._add_all())

        tk.Label(frame, text="Pokémon:").pack(anchor="w")

        list_frame = tk.Frame(frame)
        list_frame.pack(fill="x")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.pokemon_list = tk.Listbox(
            list_frame, height=10, width=30,
            yscrollcommand=scrollbar.set,
            activestyle="dotbox",
            cursor="hand2",
            takefocus=1,
        )
        scrollbar.config(command=self.pokemon_list.yview)
        self.pokemon_list.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.pokemon_list.bind("<Button-1>",  self._on_pokemon_clicked)
        self.pokemon_list.bind("<Return>",    self._on_pokemon_enter)
        self.pokemon_list.bind("<FocusIn>",   self._on_list_focus)

    def _build_remove_section(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(6, 0))

        tk.Label(frame, text="Remove Pokémon:").pack(anchor="w")

        self.remove_var = tk.StringVar()
        self.remove_box = ttk.Combobox(
            frame, textvariable=self.remove_var,
            state="readonly", width=24,
        )
        self.remove_box.pack(anchor="w", pady=(0, 4))

        ttk.Button(
            frame, text="🗑️ Remove",
            command=self._on_remove,
        ).pack(anchor="w")

    # -----------------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------------

    def _refresh_trainers(self):
        """Reload trainer names from file and update the dropdown."""
        names = get_trainer_names()
        self.trainer_box.configure(values=names)
        if names:
            current = self.trainer_var.get()
            if current not in names:
                self.trainer_var.set(names[0])
            self._load_trainer(self.trainer_var.get())
        else:
            self.trainer_var.set("")
            self._clear_pokemon_list()

    def _on_trainer_selected(self, event=None):
        name = self.trainer_var.get()
        if name:
            self._load_trainer(name)

    def _load_trainer(self, trainer_name: str):
        """Load and display a trainer's Pokémon."""
        self._trainer_pokemon = get_trainer_pokemon(trainer_name)
        self._populate_pokemon_list()

    def _populate_pokemon_list(self):
        """Fill the listbox and remove dropdown from current pokemon list."""
        self.pokemon_list.delete(0, tk.END)

        if not self._trainer_pokemon:
            self.pokemon_list.insert(tk.END, "No Pokémon saved")
            self.add_all_btn.config(state="disabled")
            self.remove_box.configure(values=[])
            self.remove_var.set("")
            return

        labels = [_pokemon_label(p) for p in self._trainer_pokemon]

        for label in labels:
            self.pokemon_list.insert(tk.END, label)

        self.add_all_btn.config(state="normal")
        self.remove_box.configure(values=labels)
        self.remove_var.set(labels[0])

    def _clear_pokemon_list(self):
        self._trainer_pokemon = []
        self.pokemon_list.delete(0, tk.END)
        self.add_all_btn.config(state="disabled")
        self.remove_box.configure(values=[])
        self.remove_var.set("")

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    def _on_list_focus(self, event=None):
        """When the listbox gains focus via Tab, select the first item if nothing is selected."""
        if not self.pokemon_list.curselection() and self.pokemon_list.size() > 0:
            self.pokemon_list.selection_set(0)
            self.pokemon_list.activate(0)

    def _on_pokemon_clicked(self, event=None):
        """Add the Pokémon that was clicked with the mouse."""
        idx = self.pokemon_list.nearest(event.y)
        if idx < 0 or idx >= len(self._trainer_pokemon):
            return
        self.pokemon_list.selection_clear(0, tk.END)
        self.pokemon_list.selection_set(idx)
        self.battler_frame.add_pokemon(self._trainer_pokemon[idx])

    def _on_pokemon_enter(self, event=None):
        """Enter on listbox adds the focused Pokémon and keeps focus on the list."""
        selection = self.pokemon_list.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(self._trainer_pokemon):
            return
        self.battler_frame.add_pokemon(self._trainer_pokemon[idx])
        # Keep focus and selection so the user can keep navigating
        self.pokemon_list.focus_set()

    def _add_all(self):
        for pokemon in self._trainer_pokemon:
            self.battler_frame.add_pokemon(pokemon)

    def _on_remove(self):
        """Confirm and remove the selected Pokémon from the trainer."""
        trainer_name = self.trainer_var.get()
        if not trainer_name or not self._trainer_pokemon:
            return

        label = self.remove_var.get()
        if not label:
            return

        # Find index by matching label
        labels = [_pokemon_label(p) for p in self._trainer_pokemon]
        if label not in labels:
            return
        idx = labels.index(label)
        pokemon_name = self._trainer_pokemon[idx].get("name", "this Pokémon")

        confirmed = messagebox.askyesno(
            "Remove Pokémon",
            f"Remove {pokemon_name} from {trainer_name}'s team?",
            parent=self,
        )
        if not confirmed:
            return

        try:
            remove_pokemon_from_trainer(trainer_name, idx)
            self._load_trainer(trainer_name)   # refresh list
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _delete_trainer(self):
        trainer_name = self.trainer_var.get()
        if not trainer_name:
            messagebox.showwarning("No Selection", "Select a trainer to delete.", parent=self)
            return
        if not messagebox.askyesno(
            "Delete Trainer",
            f"Delete {trainer_name} and all their Pokémon?",
            parent=self,
        ):
            return
        delete_trainer(trainer_name)
        self._refresh_trainers()

    def refresh(self):
        """Called externally after a Pokémon is saved to a trainer."""
        self._refresh_trainers()
