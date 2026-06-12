"""
gui/leveler_tab.py
LevelerTab: the user picks species, nature, ability, gender, and moves,
generates a Pokémon at minLevel, then levels it up one step at a time.
ASI points are distributed manually when a breakpoint is reached.
"""

import re
import tkinter as tk
from tkinter import ttk

from config import NATURES, MAX_LEVEL, LEVEL_KEYS
from data_loader import ABILITY_LOOKUP, HELD_ITEM_NAMES
from mechanics.pokemon import (
    generate_leveler_pokemon,
    level_up_pokemon,
    apply_asi_point,
    apply_nature,
    get_grouped_moves,
    get_gender_options,
    build_ability_text,
    change_nature,
    change_gender,
    get_evolution_options,
    evolve_pokemon,
    needs_ability_swap,
    get_new_form_abilities,
)
from gui.info_panel import PokemonInfoPanel


def _nature_display(nature: dict) -> str:
    """Format a nature entry for the dropdown, e.g. 'Lonely (+1 STR, -1 CON)'."""
    inc = nature["increase"]
    dec = nature["decrease"]
    if inc and dec:
        return f"{nature['name']} (+1 {inc.upper()}, -1 {dec.upper()})"
    return f"{nature['name']} (none)"


NATURE_DISPLAY_NAMES    = [_nature_display(n) for n in NATURES]
NATURE_DISPLAY_TO_NAME  = {_nature_display(n): n["name"] for n in NATURES}

# Header sentinel — entries with this prefix are section headers, not selectable
HEADER_PREFIX = "── "

MOVE_SLOTS = 4
STAT_LABELS = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}


def build_move_list(grouped: dict) -> list[str]:
    """
    Build a flat list for a Combobox from grouped move data.
    Section headers use HEADER_PREFIX and are blocked from selection.
    Moves are indented with two spaces.
    """
    items  = ["---"]
    level_keys_map = {min_lvl: key for key, min_lvl in LEVEL_KEYS}

    if grouped.get("start"):
        items.append(f"{HEADER_PREFIX}Starting Moves")
        items.extend(f"  {m}" for m in grouped["start"])

    current_level = grouped.get("current_level", 1)
    for min_lvl in sorted(grouped.get("level", {}).keys()):
        if min_lvl <= current_level:
            moves = grouped["level"][min_lvl]
            items.append(f"{HEADER_PREFIX}Level {min_lvl} Moves")
            items.extend(f"  {m}" for m in moves)

    if grouped.get("egg"):
        items.append(f"{HEADER_PREFIX}Egg Moves")
        items.extend(f"  {m}" for m in grouped["egg"])

    if grouped.get("tm"):
        items.append(f"{HEADER_PREFIX}TMs")
        items.extend(f"  {m}" for m in grouped["tm"])

    return items


class LevelerTab(ttk.Frame):
    def __init__(self, parent, all_pokemon_data: list, battler_frame):
        super().__init__(parent, padding=10)
        self.all_pokemon_data = all_pokemon_data
        self.battler_frame    = battler_frame
        self.current_pokemon  = None   # the live pokemon dict
        self.full_pokemon     = None   # raw JSON data for the species

        # Sorted name list and lookup
        self.pokemon_lookup = {p["name"]: p for p in all_pokemon_data}
        self.species_names  = sorted(self.pokemon_lookup.keys())

        self._build_species_selector()
        self._build_nature_selector()
        self._build_ability_selector()
        self._build_gender_selector()
        self._build_item_selector()
        self._build_move_selectors()
        self._build_buttons()
        self._build_stats_panel()

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_species_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 4))
        tk.Label(frame, text="Species:").pack(anchor="w")

        self.species_var = tk.StringVar()
        self.species_box = ttk.Combobox(
            frame, textvariable=self.species_var,
            values=self.species_names, state="normal", width=24,
        )
        self.species_box.pack(anchor="w")
        self.species_var.trace_add("write", self._on_species_typed)
        self.species_box.bind("<<ComboboxSelected>>", self._on_species_confirmed)
        self.species_box.bind("<FocusOut>",           self._on_species_confirmed)

    def _build_nature_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 4))
        tk.Label(frame, text="Nature:").pack(anchor="w")

        self.nature_var = tk.StringVar()
        self.nature_box = ttk.Combobox(
            frame, textvariable=self.nature_var,
            values=NATURE_DISPLAY_NAMES,
            state="readonly", width=28,
        )
        self.nature_box.pack(anchor="w")
        self.nature_box.bind("<<ComboboxSelected>>", self._on_nature_changed)

    def _build_ability_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 4))
        tk.Label(frame, text="Ability:").pack(anchor="w")

        self.ability_var = tk.StringVar()
        self.ability_box = ttk.Combobox(
            frame, textvariable=self.ability_var,
            state="readonly", width=24,
        )
        self.ability_box.pack(anchor="w")
        self.ability_box.bind("<<ComboboxSelected>>", self._on_option_changed)

    def _build_gender_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 4))
        tk.Label(frame, text="Gender:").pack(anchor="w")

        self.gender_var = tk.StringVar()
        self.gender_box = ttk.Combobox(
            frame, textvariable=self.gender_var,
            state="readonly", width=24,
        )
        self.gender_box.pack(anchor="w")
        self.gender_box.bind("<<ComboboxSelected>>", self._on_gender_changed)

    def _build_item_selector(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 4))
        tk.Label(frame, text="Held Item:").pack(anchor="w")

        self.item_var = tk.StringVar()
        self.item_box = ttk.Combobox(
            frame, textvariable=self.item_var,
            values=["None"] + HELD_ITEM_NAMES,
            state="normal", width=24,
        )
        self.item_box.set("None")
        self.item_box.pack(anchor="w")

        self.item_var.trace_add("write", self._on_item_typed)
        self.item_box.bind("<<ComboboxSelected>>", self._on_item_changed)
        self.item_box.bind("<FocusOut>",           self._on_item_changed)

    def _on_item_typed(self, *args):
        """Filter the item dropdown list as the user types."""
        typed    = self.item_var.get().strip().lower()
        filtered = ["None"] + (
            HELD_ITEM_NAMES if not typed else
            [n for n in HELD_ITEM_NAMES if typed in n.lower()]
        )
        self.item_box.configure(values=filtered)

    def _build_move_selectors(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=(0, 4))
        tk.Label(frame, text="Moves:").pack(anchor="w")

        self.move_vars  = []
        self.move_boxes = []
        for i in range(MOVE_SLOTS):
            var = tk.StringVar()
            box = ttk.Combobox(
                frame, textvariable=var,
                state="readonly", width=24,
            )
            box.pack(anchor="w", pady=1)
            self.move_vars.append(var)
            self.move_boxes.append(box)

    def _build_buttons(self):
        # Row 1 — generation controls
        row1 = tk.Frame(self)
        row1.pack(fill="x", pady=(5, 1))

        self.generate_btn = tk.Button(
            row1, text="⚙️ Generate",
            command=self._generate,
        )
        self.generate_btn.pack(side="left", padx=(0, 5))
        self.generate_btn.bind("<Return>", lambda e: self._generate())

        self.reset_btn = ttk.Button(
            row1, text="🔄 Reset",
            command=self._reset,
        )
        self.reset_btn.pack(side="left", padx=5)
        self.reset_btn.pack_forget()
        self.reset_btn.bind("<Return>", lambda e: self._reset())

        self.levelup_btn = ttk.Button(
            row1, text="⬆️ Level Up",
            command=self._level_up,
        )
        self.levelup_btn.pack(side="left", padx=5)
        self.levelup_btn.pack_forget()
        self.levelup_btn.bind("<Return>", lambda e: self._level_up())

        # Row 2 — output controls
        row2 = tk.Frame(self)
        row2.pack(fill="x", pady=(1, 5))

        self.add_btn = ttk.Button(
            row2, text="➕ Tracker",
            command=self._add_to_battler,
        )
        self.add_btn.pack(side="left", padx=(0, 5))
        self.add_btn.pack_forget()
        self.add_btn.bind("<Return>", lambda e: self._add_to_battler())

        self.save_trainer_btn = ttk.Button(
            row2, text="💾 Trainer",
            command=self._save_to_trainer,
        )
        self.save_trainer_btn.pack(side="left", padx=5)
        self.save_trainer_btn.pack_forget()
        self.save_trainer_btn.bind("<Return>", lambda e: self._save_to_trainer())

        self.view_btn = ttk.Button(
            row2, text="👀 View",
            command=self._view_pokemon,
        )
        self.view_btn.pack(side="left", padx=5)
        self.view_btn.pack_forget()
        self.view_btn.bind("<Return>", lambda e: self._view_pokemon())

        # Store both rows so _refresh_ui can target them
        self._btn_row2 = row2

    def _build_stats_panel(self):
        """Compact stats panel — always visible, ASI +1 buttons active when points pending."""
        outer = ttk.LabelFrame(self, text="📊 Stats")
        outer.pack(fill="x", pady=5)

        # Level and HP row
        top_row = tk.Frame(outer)
        top_row.pack(fill="x", padx=5, pady=(4, 2))

        self.level_label = tk.Label(
            top_row, text="Level: --", font=("Arial", 11, "bold"),
        )
        self.level_label.pack(side="left", padx=(0, 15))

        self.hp_label = tk.Label(
            top_row, text="HP: --", font=("Arial", 11),
        )
        self.hp_label.pack(side="left", padx=(0, 15))

        self.asi_remaining_label = tk.Label(
            top_row, text="", font=("Arial", 11), fg="blue",
        )
        self.asi_remaining_label.pack(side="left")

        # Six ability score rows with +1 buttons
        stats_frame = tk.Frame(outer)
        stats_frame.pack(fill="x", padx=5, pady=(0, 4))

        self._stat_labels  = {}   # stat_key → Label showing "STR: 14 (+2)"
        self._asi_buttons  = {}   # stat_key → Button for +1

        for stat_key, stat_label in STAT_LABELS.items():
            row = tk.Frame(stats_frame)
            row.pack(fill="x", pady=1)

            lbl = tk.Label(row, text=f"{stat_label[:3].upper()}: --", width=14, anchor="w")
            lbl.pack(side="left")
            self._stat_labels[stat_key] = lbl

            btn = tk.Button(
                row, text="+1", width=3,
                command=lambda s=stat_key: self._assign_asi_inline(s),
                state="disabled",
            )
            btn.pack(side="left", padx=2)
            self._asi_buttons[stat_key] = btn

    # -----------------------------------------------------------------------
    # Species selection and filtering
    # -----------------------------------------------------------------------

    def _on_species_typed(self, *args):
        typed    = self.species_var.get().strip().lower()
        filtered = self.species_names if not typed else [
            n for n in self.species_names if typed in n.lower()
        ]
        self.species_box.configure(values=filtered)

        exact = next((n for n in self.species_names if n.lower() == typed), None)
        if exact:
            self._populate_for_species(exact)

    def _on_species_confirmed(self, event=None):
        name = self.species_var.get().strip()
        if name in self.pokemon_lookup:
            self._populate_for_species(name)
        else:
            self._clear_selectors()

    def _populate_for_species(self, name: str):
        """Fill ability, gender, and move dropdowns for a species."""
        self.full_pokemon = self.pokemon_lookup[name]
        abilities_data    = self.full_pokemon.get("abilities", [])
        normal_abilities  = [a["id"] for a in abilities_data if not a.get("hidden")]

        ability_display = [
            ABILITY_LOOKUP[a]["name"] if a in ABILITY_LOOKUP else a
            for a in normal_abilities
        ]
        self.ability_box.configure(values=ability_display)
        self.ability_box.set(ability_display[0] if ability_display else "")
        self._ability_ids = normal_abilities

        # Gender
        gender_opts = get_gender_options(self.full_pokemon.get("gender", ""))
        self.gender_box.configure(
            values=gender_opts,
            state="disabled" if gender_opts == ["Genderless"] else "readonly",
        )
        self.gender_var.set(gender_opts[0])

        # Moves — grouped with section headers
        min_level = self.full_pokemon.get("minLevel", 1)
        grouped   = get_grouped_moves(self.full_pokemon, min_level)
        move_list = build_move_list(grouped)
        start_moves = [
            f"  {m.replace('-', ' ').title()}"
            for m in self.full_pokemon.get("moves", {}).get("start", [])
        ]

        for i, (var, box) in enumerate(zip(self.move_vars, self.move_boxes)):
            box.configure(values=move_list)
            box.bind("<<ComboboxSelected>>",
                     lambda e, b=box, v=var: self._on_move_selected(e, b, v))
            if i < len(start_moves):
                var.set(start_moves[i])
            else:
                var.set("---")

    def _on_move_selected(self, event, box: ttk.Combobox, var: tk.StringVar):
        """Prevent selecting a section header — revert to previous value."""
        val = var.get()
        if val.startswith(HEADER_PREFIX):
            var.set("---")

    def _clear_selectors(self):
        self.full_pokemon = None
        self.ability_box.configure(values=[])
        self.ability_var.set("")
        self.gender_box.configure(values=[])
        self.gender_var.set("")
        for var, box in zip(self.move_vars, self.move_boxes):
            box.configure(values=[])
            var.set("")

    def _on_nature_changed(self, event=None):
        """Auto-update nature if a Pokémon is already generated."""
        if not self.current_pokemon:
            return
        nature_display = self.nature_var.get()
        nature_name    = NATURE_DISPLAY_TO_NAME.get(nature_display)
        if not nature_name:
            return
        self.current_pokemon = change_nature(self.current_pokemon, nature_name)
        self._refresh_ui()

    def _on_gender_changed(self, event=None):
        """Auto-update gender if a Pokémon is already generated."""
        if not self.current_pokemon:
            return
        self.current_pokemon = change_gender(self.current_pokemon, self.gender_var.get())
        self._refresh_ui()

    def _on_item_changed(self, event=None):
        """Auto-update held item if a Pokémon is already generated."""
        val = self.item_var.get().strip()
        # Only apply if it's a valid item name or None
        if val not in (["None"] + HELD_ITEM_NAMES):
            return
        if not self.current_pokemon:
            return
        self.current_pokemon["held_item"] = val
        self._refresh_ui()

    def _on_option_changed(self, event=None):
        """Called when ability changes — no action needed until Generate."""
        pass

    # -----------------------------------------------------------------------
    # Generation
    # -----------------------------------------------------------------------

    def _generate(self):
        name = self.species_var.get().strip()
        if name not in self.pokemon_lookup:
            return

        nature_display = self.nature_var.get()
        if not nature_display:
            return
        nature_name = NATURE_DISPLAY_TO_NAME.get(nature_display, nature_display)

        ability_name = self.ability_var.get()
        ability_id   = self._resolve_ability_id(ability_name)
        gender       = self.gender_var.get()

        # Collect selected moves, filtering out blanks
        moves = [
            v.get() for v in self.move_vars if v.get() and v.get() != "---"
        ]

        self.current_pokemon = generate_leveler_pokemon(
            full_pokemon=self.full_pokemon,
            nature_name=nature_name,
            ability_id=ability_id,
            gender=gender,
            moves=moves,
        )

        # Apply held item selection
        self.current_pokemon["held_item"] = self.item_var.get()

        self._refresh_ui()

    def _resolve_ability_id(self, display_name: str) -> str:
        """Convert the displayed ability name back to its id."""
        for ability_id in self._ability_ids:
            info = ABILITY_LOOKUP.get(ability_id)
            if info and info["name"] == display_name:
                return ability_id
        # Fallback — return first available
        return self._ability_ids[0] if self._ability_ids else "none"

    # -----------------------------------------------------------------------
    # Level up
    # -----------------------------------------------------------------------

    def _level_up(self):
        if not self.current_pokemon:
            return

        self._sync_all_to_pokemon()
        new_level    = self.current_pokemon["level"] + 1
        full_pokemon = self.current_pokemon["_full_pokemon"]

        # --- Check for available evolution at the new level ---
        evo_options = get_evolution_options(full_pokemon, new_level)
        if evo_options:
            evolved = self._prompt_and_evolve(evo_options, new_level)
            if evolved:
                # Evolution happened — level_up_pokemon will now use new
                # form's hit dice for HP since _full_pokemon is updated
                pass

        # --- Level up (uses current _full_pokemon hit dice) ---
        grouped   = get_grouped_moves(self.current_pokemon["_full_pokemon"], new_level)
        move_list = build_move_list(grouped)

        for var, box in zip(self.move_vars, self.move_boxes):
            current = var.get()
            box.configure(values=move_list)
            box.bind("<<ComboboxSelected>>",
                     lambda e, b=box, v=var: self._on_move_selected(e, b, v))
            if current not in move_list:
                var.set("---")

        self.current_pokemon = level_up_pokemon(self.current_pokemon)

        # Update species display if evolved
        if evo_options and self.current_pokemon["_full_pokemon"] != full_pokemon:
            self.species_var.set(self.current_pokemon["_full_pokemon"]["name"])

        self._refresh_ui()

    def _prompt_and_evolve(self, evo_options: list, new_level: int) -> bool:
        """
        Prompt the user to evolve. Returns True if evolution was applied.
        Handles multi-evolution choice and ability swap internally.
        """
        from tkinter import messagebox

        # Build the prompt message
        if len(evo_options) == 1:
            evo_name = evo_options[0]["id"].replace("-", " ").title()
            msg = f"{self.current_pokemon['name']} can evolve into {evo_name}!\nEvolve now?"
        else:
            names = ", ".join(t["id"].replace("-", " ").title() for t in evo_options)
            msg   = f"{self.current_pokemon['name']} can evolve!\nOptions: {names}\nEvolve now?"

        if not messagebox.askyesno("Evolution Available!", msg, parent=self):
            return False

        # Pick target if multiple
        if len(evo_options) == 1:
            target = evo_options[0]
        else:
            target = self._prompt_evolution_choice(evo_options)
            if target is None:
                return False

        # Handle ability swap if needed
        new_ability_id = None
        if needs_ability_swap(self.current_pokemon, target, self.all_pokemon_data):
            new_ability_id = self._prompt_ability_swap(target)
            if new_ability_id is None:
                return False

        # Apply evolution — pass new_level so bonus uses the correct level
        try:
            self.current_pokemon = evolve_pokemon(
                self.current_pokemon,
                target,
                self.all_pokemon_data,
                new_ability_id=new_ability_id,
                new_level=new_level,
            )
            self.full_pokemon = self.current_pokemon["_full_pokemon"]
        except ValueError as e:
            messagebox.showerror("Evolution Error", str(e), parent=self)
            return False

        return True

    def _prompt_evolution_choice(self, evo_options: list) -> dict | None:
        """Show a dialog to pick which evolution to take. Returns the chosen target or None."""
        win = tk.Toplevel(self)
        win.title("Choose Evolution")
        win.geometry("260x140")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Evolve into:", font=("Arial", 10)).pack(pady=(12, 4))

        choice_var = tk.StringVar()
        names = [t["id"].replace("-", " ").title() for t in evo_options]
        box   = ttk.Combobox(win, textvariable=choice_var, values=names,
                              state="readonly", width=22)
        box.pack()
        box.set(names[0])

        result = {"target": None}

        def confirm():
            idx = names.index(choice_var.get())
            result["target"] = evo_options[idx]
            win.destroy()

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Evolve", width=9, command=confirm).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=9, command=win.destroy).pack(side="left", padx=4)

        win.wait_window()
        return result["target"]

    def _prompt_ability_swap(self, evolution_target: dict) -> str | None:
        """Prompt the user to pick a new ability since the current one doesn't carry over."""
        abilities = get_new_form_abilities(evolution_target, self.all_pokemon_data)
        if not abilities:
            return None

        win = tk.Toplevel(self)
        win.title("Choose New Ability")
        win.geometry("300x160")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(
            win,
            text="Your current ability isn't available\non the evolved form. Pick a new one:",
            font=("Arial", 10), justify="center",
        ).pack(pady=(12, 4))

        choice_var = tk.StringVar()
        names = [a["name"] for a in abilities]
        box   = ttk.Combobox(win, textvariable=choice_var, values=names,
                              state="readonly", width=26)
        box.pack()
        box.set(names[0])

        result = {"id": None}

        def confirm():
            idx = names.index(choice_var.get())
            result["id"] = abilities[idx]["id"]
            win.destroy()

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Confirm", width=9, command=confirm).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Cancel", width=9, command=win.destroy).pack(side="left", padx=4)

        win.wait_window()
        return result["id"]

    def _sync_all_to_pokemon(self):
        """
        Write every dropdown's current value back to current_pokemon.
        Call this before any save, add-to-tracker, or view operation.
        """
        if not self.current_pokemon:
            return

        # Moves — strip display indent
        moves = []
        for v in self.move_vars:
            val = v.get().strip()
            if val and val != "---" and not val.startswith(HEADER_PREFIX):
                moves.append(val)
        self.current_pokemon["moves"] = moves

        # Nature
        nature_display = self.nature_var.get()
        nature_name    = NATURE_DISPLAY_TO_NAME.get(nature_display)
        if nature_name and nature_name != self.current_pokemon.get("_nature_name"):
            self.current_pokemon = change_nature(self.current_pokemon, nature_name)

        # Gender
        gender = self.gender_var.get()
        if gender:
            self.current_pokemon["gender"] = gender

        # Held item
        item = self.item_var.get().strip()
        if item:
            self.current_pokemon["held_item"] = item

    def _refresh_ui(self):
        """Update all UI elements to reflect current_pokemon state."""
        if not self.current_pokemon:
            return

        level   = self.current_pokemon["level"]
        max_hit = level >= MAX_LEVEL
        pending = self.current_pokemon.get("_pending_asi", 0)
        attrs   = self.current_pokemon.get("_attrs", {})

        # Level and HP
        self.level_label.config(text=f"Level: {level}")
        self.hp_label.config(text=f"HP: {self.current_pokemon.get('hp', '--')}")
        self.asi_remaining_label.config(
            text=f"ASI: {pending} remaining" if pending > 0 else ""
        )

        # Ability score labels and +1 buttons
        for stat_key in STAT_LABELS:
            val = attrs.get(stat_key, 10)
            mod = (val - 10) // 2
            sign = "+" if mod >= 0 else ""
            self._stat_labels[stat_key].config(
                text=f"{stat_key.upper()}: {val} ({sign}{mod})"
            )
            self._asi_buttons[stat_key].config(
                state="normal" if pending > 0 else "disabled"
            )

        # Swap Generate out, show row 1 post-generate buttons
        self.generate_btn.pack_forget()
        self.reset_btn.pack(side="left", padx=5)
        self.levelup_btn.pack(side="left", padx=5)

        # Show row 2 buttons
        self.add_btn.pack(side="left", padx=(0, 5))
        self.save_trainer_btn.pack(side="left", padx=5)
        self.view_btn.pack(side="left", padx=5)

        self.levelup_btn.config(state="disabled" if max_hit else "normal")

    def _assign_asi_inline(self, stat: str):
        """Apply one ASI point to the chosen stat directly from the stats panel."""
        if not self.current_pokemon:
            return
        if self.current_pokemon.get("_pending_asi", 0) <= 0:
            return
        self.current_pokemon = apply_asi_point(self.current_pokemon, stat)
        self._refresh_ui()

    def _save_to_trainer(self):
        if not self.current_pokemon:
            return
        self._sync_all_to_pokemon()
        from gui.save_to_trainer_dialog import open_save_dialog
        open_save_dialog(self, self.current_pokemon)

    def _reset(self):
        """Confirm then clear the current Pokémon and return to Generate state."""
        from tkinter import messagebox
        if self.current_pokemon:
            confirmed = messagebox.askyesno(
                "Reset",
                "Are you sure you want to reset? All unsaved progress will be lost.",
                parent=self,
            )
            if not confirmed:
                return

        self.current_pokemon = None
        self.full_pokemon    = None

        # Clear dropdowns
        self.species_var.set("")
        self.nature_var.set("")
        self.ability_box.configure(values=[])
        self.ability_var.set("")
        self.gender_box.configure(values=[], state="readonly")
        self.gender_var.set("")
        self.item_var.set("None")
        for var, box in zip(self.move_vars, self.move_boxes):
            box.configure(values=[])
            var.set("")

        # Reset stat panel
        self.level_label.config(text="Level: --")
        self.hp_label.config(text="HP: --")
        self.asi_remaining_label.config(text="")
        for stat_key in STAT_LABELS:
            self._stat_labels[stat_key].config(text=f"{stat_key.upper()}: --")
            self._asi_buttons[stat_key].config(state="disabled")

        # Swap buttons back
        self.reset_btn.pack_forget()
        self.levelup_btn.pack_forget()
        self.add_btn.pack_forget()
        self.save_trainer_btn.pack_forget()
        self.view_btn.pack_forget()
        self.generate_btn.pack(side="left", padx=(0, 5))

    # -----------------------------------------------------------------------
    # Tracker / view
    # -----------------------------------------------------------------------

    def _add_to_battler(self):
        if not self.current_pokemon:
            return
        self._sync_all_to_pokemon()
        # Strip leveler-only private fields before handing to tracker
        tracker_pokemon = {
            k: v for k, v in self.current_pokemon.items()
            if not k.startswith("_")
        }
        self.battler_frame.add_pokemon(tracker_pokemon)

    def _view_pokemon(self):
        if not self.current_pokemon:
            return
        self._sync_all_to_pokemon()

        win = tk.Toplevel(self)
        win.title(f"{self.current_pokemon['name']} Info")
        win.geometry("500x725")

        panel = PokemonInfoPanel(win)
        panel.all_pokemon_data = self.all_pokemon_data
        panel.pack(fill="both", expand=True, padx=10, pady=10)
        panel.display_pokemon(self.current_pokemon, show_save_button=True)

    # -----------------------------------------------------------------------
    # External entry point — called by battler "Open in Leveler"
    # -----------------------------------------------------------------------

    def load_pokemon(self, pokemon: dict):
        """
        Load an existing Pokémon into the leveler.
        Reconstructs leveler state (_base_attrs, _nature_name, etc.)
        for Pokémon that didn't originate from the leveler.
        """
        full_pokemon = self._find_full_pokemon(pokemon.get("name", ""))
        if not full_pokemon:
            return

        # If leveler fields are already present, use them directly
        if "_base_attrs" in pokemon and "_nature_name" in pokemon:
            reconstructed = dict(pokemon)
            reconstructed["_full_pokemon"] = full_pokemon
        else:
            reconstructed = self._reconstruct_leveler_state(pokemon, full_pokemon)

        self.current_pokemon = reconstructed
        self.full_pokemon    = full_pokemon

        # Sync UI dropdowns to match the loaded Pokémon
        self.species_var.set(full_pokemon["name"])
        self._populate_for_species(full_pokemon["name"])

        # Set nature dropdown
        nature_name    = reconstructed.get("_nature_name", "Hardy")
        nature_display = next(
            (d for d in NATURE_DISPLAY_NAMES
             if NATURE_DISPLAY_TO_NAME.get(d) == nature_name),
            NATURE_DISPLAY_NAMES[0],
        )
        self.nature_var.set(nature_display)

        # Set gender dropdown
        self.gender_var.set(reconstructed.get("gender", ""))

        # Set item dropdown
        held_item = reconstructed.get("held_item", "None") or "None"
        if held_item in HELD_ITEM_NAMES:
            self.item_var.set(held_item)
        else:
            self.item_var.set("None")

        # Set move dropdowns
        level     = reconstructed.get("level", 1)
        grouped   = get_grouped_moves(full_pokemon, level)
        move_list = build_move_list(grouped)
        moves     = reconstructed.get("moves", [])
        for i, (var, box) in enumerate(zip(self.move_vars, self.move_boxes)):
            box.configure(values=move_list)
            box.bind("<<ComboboxSelected>>",
                     lambda e, b=box, v=var: self._on_move_selected(e, b, v))
            if i < len(moves):
                display = f"  {moves[i]}"
                var.set(display if display in move_list else moves[i])
            else:
                var.set("---")

        self._refresh_ui()

    def _find_full_pokemon(self, display_name: str) -> dict | None:
        """Find raw JSON data for a Pokémon by its display name (upper case)."""
        return next(
            (p for p in self.all_pokemon_data
             if p["name"].upper() == display_name.upper()),
            None,
        )

    def _reconstruct_leveler_state(
        self, pokemon: dict, full_pokemon: dict
    ) -> dict:
        """
        Build leveler private fields for a Pokémon that didn't come
        from the leveler (e.g. from Areas, Wild, or Trainer tab).
        We reverse-engineer _base_attrs by stripping the nature modifier
        from the current ability scores.
        """
        # Parse current ability scores from the text block
        attrs = {}
        for line in pokemon.get("ability_scores", "").split("\n"):
            parts = line.split(":")
            if len(parts) >= 2:
                key = parts[0].strip().lower()
                m   = re.search(r"\d+", parts[1])
                attrs[key] = int(m.group()) if m else 10

        # Use Hardy (neutral) as the default nature if we can't determine it
        nature_name = pokemon.get("_nature_name", "Hardy")

        # Reverse the nature to get approximate base attrs
        nature_entry = next(
            (n for n in NATURES if n["name"] == nature_name), None
        )
        base_attrs = attrs.copy()
        if nature_entry:
            if nature_entry["increase"]:
                base_attrs[nature_entry["increase"]] = max(
                    1, base_attrs.get(nature_entry["increase"], 10) - 1
                )
            if nature_entry["decrease"]:
                base_attrs[nature_entry["decrease"]] = (
                    base_attrs.get(nature_entry["decrease"], 10) + 1
                )

        reconstructed = dict(pokemon)
        reconstructed["_full_pokemon"] = full_pokemon
        reconstructed["_nature_name"]  = nature_name
        reconstructed["_base_attrs"]   = base_attrs
        reconstructed["_attrs"]        = attrs
        reconstructed["_pending_asi"]  = pokemon.get("_pending_asi", 0)
        return reconstructed
