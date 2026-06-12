"""
gui/app.py
Left panel container. Holds a ttk.Notebook with one tab per feature.
Tabs: Areas, Wild, Leveler, Trainer.
"""

import tkinter as tk
from tkinter import ttk

import requests
from PIL import Image, ImageTk
from io import BytesIO

from mechanics.pokemon import pick_random_pokemon
from gui.info_panel import PokemonInfoPanel
from config import DEFAULT_IMAGE_URL
from gui.wild_tab import WildTab
from gui.leveler_tab import LevelerTab
from gui.trainer_tab import TrainerTab
from gui.fakemon_tab import FakemonTab
from gui.area_builder_tab import AreaBuilderTab
from gui.tooltip import NotebookToolTip


class WilranApp(ttk.Frame):
    def __init__(self, parent, areas: dict, all_pokemon_data: list, battler_frame):
        super().__init__(parent, padding=5)
        self.areas            = areas
        self.all_pokemon_data = all_pokemon_data
        self.battler_frame    = battler_frame

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        areas_tab = AreasTab(self.notebook, areas, all_pokemon_data, battler_frame)
        self.notebook.add(areas_tab, text="Random Wild")

        wild_tab = WildTab(self.notebook, all_pokemon_data, battler_frame)
        self.notebook.add(wild_tab, text="Wild")

        self.leveler_tab = LevelerTab(self.notebook, all_pokemon_data, battler_frame)
        self.notebook.add(self.leveler_tab, text="Leveler")

        self.trainer_tab = TrainerTab(self.notebook, battler_frame)
        self.notebook.add(self.trainer_tab, text="Trainer")

        fakemon_tab = FakemonTab(self.notebook)
        self.notebook.add(fakemon_tab, text="Fakemon")

        area_builder_tab = AreaBuilderTab(self.notebook, all_pokemon_data)
        self.notebook.add(area_builder_tab, text="Area Builder")

        # Delayed tooltips on tab labels
        NotebookToolTip(self.notebook, delay=700)

    def switch_to_leveler(self):
        """Switch the visible tab to the Leveler."""
        idx = self.notebook.index(self.leveler_tab)
        self.notebook.select(idx)

    def refresh_trainer_tab(self):
        """Tell the Trainer tab to reload from file."""
        self.trainer_tab.refresh()


# ---------------------------------------------------------------------------
# Areas tab — exactly what WilranApp used to be
# ---------------------------------------------------------------------------

class AreasTab(ttk.Frame):
    def __init__(self, parent, areas: dict, all_pokemon_data: list, battler_frame):
        super().__init__(parent, padding=10)
        self.areas            = areas
        self.all_pokemon_data = all_pokemon_data
        self.battler_frame    = battler_frame
        self.current_pokemon  = None

        self._build_area_selector()
        self._build_action_buttons()
        self._build_preview_card()

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_area_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text="Choose an Area:").pack(anchor="w")

        self.area_var = tk.StringVar()
        ttk.Combobox(
            frame, textvariable=self.area_var,
            values=list(self.areas.keys()), state="readonly",
            width=24,
        ).pack(anchor="w", pady=(0, 5))

        self.randomize_btn = tk.Button(
            frame, text="🎲 Randomize Pokémon", command=self._randomize,
        )
        self.randomize_btn.pack(anchor="w")
        self.randomize_btn.bind("<Return>", lambda e: self._randomize())

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
    # Callbacks
    # -----------------------------------------------------------------------

    def _randomize(self):
        area_name = self.area_var.get()
        if not area_name:
            return

        pokemon = pick_random_pokemon(self.areas[area_name], self.all_pokemon_data)
        if not pokemon:
            return

        self.current_pokemon = pokemon
        self.add_btn.config(state="normal")
        self.view_btn.config(state="normal")
        self._update_preview(pokemon)
        self.randomize_btn.focus_set()

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
