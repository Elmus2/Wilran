"""
gui/area_builder_tab.py
AreaBuilderTab: create and edit areas in areas.json.
Changes save immediately on every action.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from stores.area_store import (
    get_area_names, get_area, create_area, rename_area,
    add_pokemon_to_area, remove_pokemon_from_area, delete_area,
)


class AreaBuilderTab(ttk.Frame):
    def __init__(self, parent, all_pokemon_data: list):
        super().__init__(parent, padding=10)
        self.all_pokemon_data = all_pokemon_data
        self._current_area    = None   # name of the currently loaded area
        self._pokemon_list    = []     # list of pokemon dicts for current area

        # Sorted species names for the searchable dropdown
        self._species_names = sorted(p["name"] for p in all_pokemon_data)

        self._build_area_selector()
        self._build_name_editor()
        self._build_pokemon_list()
        self._build_add_row()
        self._build_action_buttons()

        self._refresh_area_dropdown()

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_area_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 6))

        tk.Label(frame, text="Area:").pack(side="left", padx=(0, 5))

        self._area_var = tk.StringVar()
        self._area_box = ttk.Combobox(
            frame, textvariable=self._area_var,
            state="readonly", width=24,
        )
        self._area_box.pack(side="left")
        self._area_box.bind("<<ComboboxSelected>>", self._on_area_selected)

        self._new_area_btn = tk.Button(frame, text="＋ New Area",
                  command=self._new_area)
        self._new_area_btn.pack(side="left", padx=(8, 0))
        self._new_area_btn.bind("<Return>", lambda e: self._new_area())

    def _build_name_editor(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 6))

        tk.Label(frame, text="Name:", width=8, anchor="w").pack(side="left")

        self._name_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=self._name_var, width=26)
        entry.pack(side="left")
        entry.bind("<Return>",   self._on_rename)
        entry.bind("<FocusOut>", self._on_rename)

    def _build_pokemon_list(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 4))

        tk.Label(frame, text="Pokémon in area:").pack(anchor="w", pady=(0, 2))

        list_frame = tk.Frame(frame)
        list_frame.pack(fill="x")

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        self._poke_listbox = tk.Listbox(
            list_frame, height=12, width=32,
            yscrollcommand=sb.set, exportselection=False,
            activestyle="dotbox",
        )
        sb.config(command=self._poke_listbox.yview)
        self._poke_listbox.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")

    def _build_add_row(self):
        # Row 1: species search
        row1 = tk.Frame(self)
        row1.pack(fill="x", pady=(0, 2))

        tk.Label(row1, text="Species:", width=8, anchor="w").pack(side="left")

        self._species_var = tk.StringVar()
        self._species_box = ttk.Combobox(
            row1, textvariable=self._species_var,
            values=self._species_names, state="normal", width=24,
        )
        self._species_box.pack(side="left")
        self._species_var.trace_add("write", self._filter_species)
        self._species_box.bind("<Return>", lambda e: self._add_pokemon())

        # Row 2: min/max levels + Add button
        row2 = tk.Frame(self)
        row2.pack(fill="x", pady=(0, 4))

        tk.Label(row2, text="Min Lv:", width=8, anchor="w").pack(side="left")
        self._min_var = tk.StringVar(value="1")
        min_spin = tk.Spinbox(row2, textvariable=self._min_var,
                   from_=1, to=20, width=3)
        min_spin.pack(side="left", padx=(0, 8))
        min_spin.bind("<Return>", lambda e: self._add_pokemon())

        tk.Label(row2, text="Max Lv:").pack(side="left", padx=(0, 4))
        self._max_var = tk.StringVar(value="20")
        max_spin = tk.Spinbox(row2, textvariable=self._max_var,
                   from_=1, to=20, width=3)
        max_spin.pack(side="left", padx=(0, 8))
        max_spin.bind("<Return>", lambda e: self._add_pokemon())

        self._add_btn = tk.Button(row2, text="➕ Add to Area",
                  command=self._add_pokemon)
        self._add_btn.pack(side="left")
        self._add_btn.bind("<Return>", lambda e: self._add_pokemon())

    def _build_action_buttons(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(4, 0))

        self._remove_btn = tk.Button(
            frame, text="🗑️ Remove Selected",
            command=self._remove_pokemon,
        )
        self._remove_btn.pack(side="left", padx=(0, 8))
        self._remove_btn.bind("<Return>", lambda e: self._remove_pokemon())

        self._delete_btn = tk.Button(
            frame, text="🗑️ Delete Area", fg="red",
            command=self._delete_area,
        )
        self._delete_btn.pack(side="left")
        self._delete_btn.bind("<Return>", lambda e: self._delete_area())

    # -----------------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------------

    def _refresh_area_dropdown(self):
        names = get_area_names()
        self._area_box.configure(values=names)

    def _on_area_selected(self, event=None):
        name = self._area_var.get()
        if name:
            self._load_area(name)

    def _load_area(self, name: str):
        area = get_area(name)
        if not area:
            return
        self._current_area = name
        self._name_var.set(name)
        self._pokemon_list = list(area.get("pokemon", []))
        self._repopulate_listbox()

    def _repopulate_listbox(self):
        self._poke_listbox.delete(0, tk.END)
        for p in self._pokemon_list:
            self._poke_listbox.insert(
                tk.END,
                f"{p['name']} (Lv {p['min_level']} - {p['max_level']})"
            )

    # -----------------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------------

    def _filter_species(self, *args):
        typed    = self._species_var.get().strip().lower()
        filtered = self._species_names if not typed else [
            n for n in self._species_names if typed in n.lower()
        ]
        self._species_box.configure(values=filtered)

    def _new_area(self):
        win = tk.Toplevel(self)
        win.title("New Area")
        win.geometry("260x110")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Area name:").pack(pady=(12, 4))
        name_var = tk.StringVar()
        entry = tk.Entry(win, textvariable=name_var, width=24)
        entry.pack()
        entry.focus_set()

        def confirm():
            name = name_var.get().strip()
            if not name:
                return
            try:
                create_area(name)
                self._refresh_area_dropdown()
                self._area_var.set(name)
                self._load_area(name)
                win.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=win)

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Create", width=8, command=confirm).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=8, command=win.destroy).pack(side="left", padx=4)
        entry.bind("<Return>", lambda e: confirm())
        win.wait_window()

    def _on_rename(self, event=None):
        if not self._current_area:
            return
        new_name = self._name_var.get().strip()
        if not new_name or new_name == self._current_area:
            return
        try:
            rename_area(self._current_area, new_name)
            self._current_area = new_name
            self._refresh_area_dropdown()
            self._area_var.set(new_name)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
            self._name_var.set(self._current_area)

    def _add_pokemon(self):
        if not self._current_area:
            messagebox.showwarning("No Area", "Select or create an area first.", parent=self)
            return

        species = self._species_var.get().strip()
        if species not in self._species_names:
            messagebox.showwarning("Invalid Species",
                                   f"'{species}' not found. Select a valid species.",
                                   parent=self)
            return

        try:
            min_lvl = int(self._min_var.get())
            max_lvl = int(self._max_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Level", "Levels must be numbers.", parent=self)
            return

        if min_lvl > max_lvl:
            messagebox.showwarning("Invalid Level",
                                   "Min level cannot be greater than max level.",
                                   parent=self)
            return

        add_pokemon_to_area(self._current_area, species, min_lvl, max_lvl)
        self._pokemon_list.append({
            "name": species, "min_level": min_lvl, "max_level": max_lvl
        })
        self._poke_listbox.insert(
            tk.END, f"{species} (Lv {min_lvl} - {max_lvl})"
        )
        self._species_var.set("")

    def _remove_pokemon(self):
        if not self._current_area:
            return
        sel = self._poke_listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Select a Pokémon to remove.", parent=self)
            return
        idx = sel[0]
        remove_pokemon_from_area(self._current_area, idx)
        self._pokemon_list.pop(idx)
        self._poke_listbox.delete(idx)

    def _delete_area(self):
        if not self._current_area:
            return
        if not messagebox.askyesno(
            "Delete Area",
            f"Delete '{self._current_area}'? This cannot be undone.",
            parent=self,
        ):
            return
        delete_area(self._current_area)
        self._current_area = None
        self._name_var.set("")
        self._pokemon_list = []
        self._poke_listbox.delete(0, tk.END)
        self._refresh_area_dropdown()
        self._area_var.set("")
