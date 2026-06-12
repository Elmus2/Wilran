"""gui/info_panel.py — scrollable Pokémon stat display panel."""

import tkinter as tk
from tkinter import ttk

from gui.tooltip import ToolTip

WRAP = 450


class PokemonInfoPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.all_pokemon_data = []  # injected by owner after construction
        self._current_pokemon = None

        self.canvas = tk.Canvas(self, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def display_pokemon(
        self,
        pokemon: dict,
        show_save_button: bool = False,
        on_open_leveler=None,
    ):
        self._current_pokemon = pokemon
        self._show_save       = show_save_button
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not pokemon.get("name"):
            return

        self._render_header(pokemon, on_open_leveler=on_open_leveler)

        if any(pokemon.get(f) for f in ["size", "nature", "held_item", "sr"]):
            self._render_basics(pokemon)

        if any(pokemon.get(f) for f in ["ac", "hp", "speed", "ability_scores"]):
            self._render_stats(pokemon)

        if any(pokemon.get(f) for f in ["proficiency_bonus", "skills", "saving_throws"]):
            self._render_skills(pokemon)

        if any(pokemon.get(f) for f in ["vulnerabilities", "resistances", "immunities"]):
            self._render_defenses(pokemon)

        if any(pokemon.get(f) for f in ["moves", "abilities"]):
            self._render_moves(pokemon)

    # ------------------------------------------------------------------
    # Private render helpers
    # ------------------------------------------------------------------

    def _label(self, parent, text, **kwargs):
        kwargs.setdefault("wraplength", WRAP)
        kwargs.setdefault("justify", "left")
        lbl = tk.Label(parent, text=text, **kwargs)
        lbl.pack(anchor="w")
        return lbl

    def _section(self, title: str) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self.scrollable_frame, text=title)
        frame.pack(fill="x", pady=5)
        return frame

    def _render_header(self, pokemon: dict, on_open_leveler=None):
        shiny  = " 🌟 Shiny! 🌟" if pokemon.get("shiny") else ""
        level  = f" (Lv {pokemon['level']})" if pokemon.get("level") else ""
        gender = f" - {pokemon['gender']}" if pokemon.get("gender") else ""

        # Outer row: left side has name/type, right side has buttons
        header_row = tk.Frame(self.scrollable_frame)
        header_row.pack(fill="x", pady=(0, 2))

        # Left: name and type stacked
        left = tk.Frame(header_row)
        left.pack(side="left", fill="x", expand=True)

        name_lbl = tk.Label(
            left,
            text=f"{pokemon['name']}{level}{gender}{shiny}",
            font=("Arial", 14, "bold"),
            wraplength=WRAP - 120,
            justify="left",
            anchor="w",
        )
        name_lbl.pack(anchor="w")
        self._add_description_tooltip(name_lbl, pokemon["name"])

        if pokemon.get("types"):
            tk.Label(
                left, text=f"Type: {pokemon['types']}",
                font=("Arial", 12), justify="left", anchor="w",
            ).pack(anchor="w")

        # Right: action buttons stacked vertically in top-right corner
        if self._show_save or on_open_leveler:
            right = tk.Frame(header_row)
            right.pack(side="right", anchor="n", padx=(5, 0))
            if self._show_save:
                from gui.save_to_trainer_dialog import open_save_dialog
                ttk.Button(
                    right, text="💾 Save to Trainer",
                    command=lambda: open_save_dialog(self, pokemon),
                ).pack(anchor="e", pady=(0, 3))
            if on_open_leveler:
                ttk.Button(
                    right, text="📈 Open in Leveler",
                    command=on_open_leveler,
                ).pack(anchor="e")

    def _render_basics(self, pokemon: dict):
        frame = self._section("📌 Basics")
        for field, label in [("size", "Size"), ("nature", "Nature"), ("held_item", "Held Item")]:
            if pokemon.get(field):
                self._label(frame, f"{label}: {pokemon[field]}")
        if pokemon.get("sr") is not None:
            self._label(frame, f"SR: {pokemon['sr']}")
        if pokemon.get("level") and pokemon.get("sr") is not None:
            xp = int(200 * pokemon["level"] * pokemon["sr"])
            self._label(frame, f"Exp: {xp}")

    def _render_stats(self, pokemon: dict):
        frame = self._section("📊 Stats")
        for field, label in [("ac", "Armor Class"), ("hp", "HP"), ("speed", "Speed")]:
            if pokemon.get(field):
                self._label(frame, f"{label}: {pokemon[field]}")
        if pokemon.get("ability_scores"):
            indented = "\n".join(f"    {l}" for l in pokemon["ability_scores"].split("\n"))
            tk.Label(frame, text=indented, font=("Courier", 10), justify="left").pack(anchor="w", pady=2)

    def _render_skills(self, pokemon: dict):
        frame = self._section("🛡️ Skills & Proficiencies")
        if pokemon.get("proficiency_bonus"):
            self._label(frame, f"Proficiency Bonus: +{pokemon['proficiency_bonus']}")
        if pokemon.get("skills"):
            self._label(frame, f"Skills: {pokemon['skills']}")
        if pokemon.get("saving_throws"):
            self._label(frame, f"Saving Throws: {pokemon['saving_throws']}")

    def _render_defenses(self, pokemon: dict):
        frame = self._section("🧪 Defenses")
        for field, label in [("vulnerabilities", "Vulnerabilities"), ("resistances", "Resistances"), ("immunities", "Immunities")]:
            val = pokemon.get(field, [])
            if val:
                self._label(frame, f"{label}: {', '.join(val)}")

    def _render_moves(self, pokemon: dict):
        frame = self._section("⚔️ Moves & Abilities")
        moves = pokemon.get("moves", [])
        if moves:
            self._label(frame, f"Moves: {', '.join(moves)}", pady=2)
        if pokemon.get("abilities"):
            self._label(frame, pokemon["abilities"], pady=2)

    def _add_description_tooltip(self, widget: tk.Widget, pokemon_name: str):
        desc = next(
            (pk.get("description", "") for pk in self.all_pokemon_data
             if pk["name"].lower() == pokemon_name.lower()),
            f"No description available for {pokemon_name}",
        )
        ToolTip(widget, desc)
