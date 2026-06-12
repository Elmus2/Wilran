"""
gui/wild_tab.py
WildTab: lets the user pick a species and level, then generates a
wild Pokémon the same way the randomizer does.
"""

import tkinter as tk
from tkinter import ttk

import requests
from PIL import Image, ImageTk
from io import BytesIO

from config import MAX_LEVEL, DEFAULT_IMAGE_URL
from mechanics.pokemon import pick_random_pokemon
from gui.info_panel import PokemonInfoPanel


class WildTab(ttk.Frame):
    def __init__(self, parent, all_pokemon_data: list, battler_frame):
        super().__init__(parent, padding=10)
        self.all_pokemon_data = all_pokemon_data
        self.battler_frame    = battler_frame
        self.current_pokemon  = None

        self.pokemon_lookup = {p["name"]: p for p in all_pokemon_data}
        self.species_names  = sorted(self.pokemon_lookup.keys())

        self._build_species_selector()
        self._build_level_selector()
        self._build_generate_button()
        self._build_action_buttons()
        self._build_preview_card()

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_species_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text="Species:").pack(anchor="w")

        self.species_var = tk.StringVar()
        self.species_box = ttk.Combobox(
            frame,
            textvariable=self.species_var,
            values=self.species_names,
            state="normal",
            width=24,
        )
        self.species_box.pack(anchor="w", pady=(0, 5))

        self.species_var.trace_add("write", self._on_species_typed)
        self.species_box.bind("<<ComboboxSelected>>", self._on_species_selected)
        self.species_box.bind("<FocusOut>",           self._on_species_selected)
        self.species_box.bind("<Return>",             self._on_species_enter)

    def _build_level_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text="Level:").pack(anchor="w")

        self.level_var = tk.StringVar()
        self.level_box = ttk.Combobox(
            frame,
            textvariable=self.level_var,
            state="readonly",
            width=10,
        )
        self.level_box.pack(anchor="w", pady=(0, 5))

    def _build_generate_button(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=5)

        self.generate_btn = tk.Button(
            frame, text="⚙️ Generate Pokémon", command=self._generate,
        )
        self.generate_btn.pack(anchor="w")
        self.generate_btn.bind("<Return>", lambda e: self._generate())

    def _build_action_buttons(self):
        frame = tk.Frame(self)
        frame.pack(pady=5)

        self.add_btn = ttk.Button(
            frame, text="➕ Add to Tracker",
            command=self._add_to_battler, state="disabled",
        )
        self.add_btn.pack(side="left", padx=5)
        self.add_btn.bind("<Return>", lambda e: self._add_to_battler())

        self.view_btn = ttk.Button(
            frame, text="👀 View Pokémon",
            command=self._view_pokemon, state="disabled",
        )
        self.view_btn.pack(side="left", padx=5)
        self.view_btn.bind("<Return>", lambda e: self._view_pokemon())

    def _build_preview_card(self):
        card = ttk.Frame(self, relief="raised", padding=5, borderwidth=2)
        card.pack(fill="x", pady=10)

        self.img_label = tk.Label(card)
        self.img_label.pack(side="left", padx=5, pady=5)

        text_frame = ttk.Frame(card)
        text_frame.pack(side="left", padx=5, pady=5, anchor="n")

        self.name_label   = tk.Label(text_frame, font=("Arial", 14, "bold"))
        self.level_label  = tk.Label(text_frame, font=("Arial", 12))
        self.gender_label = tk.Label(text_frame, font=("Arial", 12))
        self.shiny_label  = tk.Label(text_frame, font=("Arial", 12), fg="gold")

        for lbl in (self.name_label, self.level_label, self.gender_label, self.shiny_label):
            lbl.pack(anchor="w")

    # -----------------------------------------------------------------------
    # Filtering helpers
    # -----------------------------------------------------------------------

    def _on_species_typed(self, *args):
        typed = self.species_var.get().strip().lower()
        filtered = self.species_names if not typed else [
            n for n in self.species_names if typed in n.lower()
        ]
        self.species_box.configure(values=filtered)

        exact = next((n for n in self.species_names if n.lower() == typed), None)
        if exact:
            self._populate_levels(exact)

    def _on_species_enter(self, event=None):
        """Enter on species box — confirm selection and move focus to level."""
        name = self.species_var.get().strip()
        if name in self.pokemon_lookup:
            self._populate_levels(name)
            self.level_box.focus_set()

    # -----------------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------------

    def _on_species_selected(self, event=None):
        name = self.species_var.get().strip()
        if name in self.pokemon_lookup:
            self._populate_levels(name)
        else:
            self.level_box.configure(values=[])
            self.level_var.set("")

    def _populate_levels(self, name: str):
        pokemon_data = self.pokemon_lookup.get(name)
        if not pokemon_data:
            return
        min_level = pokemon_data.get("minLevel", 1)
        levels    = list(range(min_level, MAX_LEVEL + 1))
        self.level_box.configure(values=levels)
        self.level_var.set(min_level)

    def _generate(self):
        name = self.species_var.get().strip()
        if name not in self.pokemon_lookup:
            return

        level_str = self.level_var.get()
        if not level_str:
            return

        level    = int(level_str)
        fake_area = {
            "pokemon": [{"name": name, "min_level": level, "max_level": level}]
        }

        pokemon = pick_random_pokemon(fake_area, self.all_pokemon_data)
        if not pokemon:
            return

        self.current_pokemon = pokemon
        self.add_btn.config(state="normal")
        self.view_btn.config(state="normal")
        self._update_preview(pokemon)
        self.generate_btn.focus_set()

    def _update_preview(self, pokemon: dict):
        url = pokemon.get("image_url", "").strip()
        if not url or not url.startswith("http"):
            url = DEFAULT_IMAGE_URL
        try:
            img = Image.open(BytesIO(requests.get(url, timeout=5).content))
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self.img_label.configure(image=tk_img, text="")
            self.img_label.image = tk_img
        except Exception:
            self.img_label.configure(image="", text="")

        self.name_label.config(text=pokemon["name"])
        self.level_label.config(text=f"Level: {pokemon['level']}")
        self.gender_label.config(text=f"Gender: {pokemon['gender']}")
        self.shiny_label.config(text="🌟 Shiny! 🌟" if pokemon.get("shiny") else "")

    def _add_to_battler(self):
        if self.current_pokemon:
            self.battler_frame.add_pokemon(self.current_pokemon)
            self.add_btn.focus_set()

    def _view_pokemon(self):
        if not self.current_pokemon:
            return

        win = tk.Toplevel(self)
        win.title(f"{self.current_pokemon['name']} Info")
        win.geometry("500x725")

        panel = PokemonInfoPanel(win)
        panel.all_pokemon_data = self.all_pokemon_data
        panel.pack(fill="both", expand=True, padx=10, pady=10)
        panel.display_pokemon(self.current_pokemon, show_save_button=True)
        self.view_btn.focus_set()
