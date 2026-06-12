"""
gui/fakemon_tab.py
FakemonTab: build a custom Pokémon from scratch and save it to fakemon.json.
Existing entries can be loaded back, edited, and re-saved.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from data_loader import ABILITY_LOOKUP, MOVE_LOOKUP, TM_LOOKUP
from stores.fakemon_store import (
    load_fakemon, get_fakemon_names, save_fakemon,
    delete_fakemon, get_fakemon,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POKEMON_TYPES = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy",
]

SIZES = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]

HIT_DICE = ["d4", "d6", "d8", "d10", "d12", "d20"]

GENDER_RATIOS = {
    "Genderless":     "0:0",
    "Male only":      "0:1",
    "Female only":    "1:0",
    "50/50":          "1:1",
    "Mostly male (1:7)":   "1:7",
    "Mostly female (7:1)": "7:1",
    "3:1 male":       "1:3",
    "3:1 female":     "3:1",
}

EGG_GROUPS = [
    "amorphous", "bug", "dragon", "fairy", "field", "flying",
    "gender unknown", "grass", "human-like", "mineral", "monster",
    "undiscovered", "water 1", "water 2", "water 3",
]

SPEED_TYPES  = ["Walking", "Flying", "Swimming", "Burrowing", "Climbing"]
SENSE_TYPES  = ["Darkvision", "Blindsight", "Tremorsense", "Truesight"]

SKILLS_LIST  = [
    "acrobatics", "animal handling", "arcana", "athletics", "deception",
    "history", "insight", "intimidation", "investigation", "medicine",
    "nature", "perception", "performance", "persuasion", "religion",
    "sleight of hand", "stealth", "survival",
]

STAT_KEYS    = ["str", "dex", "con", "int", "wis", "cha"]
STAT_LABELS  = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

LEVEL_MOVE_KEYS = [
    ("start",   "Start"),
    ("level2",  "Level 2"),
    ("level6",  "Level 6"),
    ("level10", "Level 10"),
    ("level14", "Level 14"),
    ("level18", "Level 18"),
    ("egg",     "Egg Moves"),
]

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _ability_display(ability_id: str) -> str:
    info = ABILITY_LOOKUP.get(ability_id)
    return info["name"] if info else ability_id


def _move_display(move_id: str) -> str:
    info = MOVE_LOOKUP.get(move_id)
    return info["name"] if info else move_id.replace("-", " ").title()


# ---------------------------------------------------------------------------
# SearchableListEditor — reusable widget for building a list of moves
# ---------------------------------------------------------------------------

class SearchableListEditor(tk.Frame):
    """
    A compound widget with:
    - A listbox showing currently selected items
    - A searchable combobox + Add button to add new items
    - A Remove button to delete the selected item
    """
    def __init__(self, parent, all_items: list[str], **kwargs):
        super().__init__(parent, **kwargs)
        self._all_items = all_items
        self._items     = []   # currently selected items (display names)

        # Listbox
        list_frame = tk.Frame(self)
        list_frame.pack(fill="x")

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame, height=4, width=28,
            yscrollcommand=sb.set, exportselection=False,
        )
        sb.config(command=self.listbox.yview)
        self.listbox.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")

        # Search + Add row
        add_frame = tk.Frame(self)
        add_frame.pack(fill="x", pady=2)

        self._search_var = tk.StringVar()
        self._search_box = ttk.Combobox(
            add_frame, textvariable=self._search_var,
            values=all_items, state="normal", width=18,
        )
        self._search_box.pack(side="left", padx=(0, 4))
        self._search_var.trace_add("write", self._filter)
        self._search_box.bind("<Return>", lambda e: self._add())

        add_btn = tk.Button(add_frame, text="Add", command=self._add)
        add_btn.pack(side="left", padx=(0, 4))
        add_btn.bind("<Return>", lambda e: self._add())

        remove_btn = tk.Button(add_frame, text="Remove", command=self._remove)
        remove_btn.pack(side="left")
        remove_btn.bind("<Return>", lambda e: self._remove())

    def _filter(self, *args):
        typed    = self._search_var.get().strip().lower()
        filtered = self._all_items if not typed else [
            n for n in self._all_items if typed in n.lower()
        ]
        self._search_box.configure(values=filtered)

    def _add(self):
        val = self._search_var.get().strip()
        if not val or val not in self._all_items:
            return
        if val not in self._items:
            self._items.append(val)
            self.listbox.insert(tk.END, val)
        self._search_var.set("")

    def _remove(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.listbox.delete(idx)
        self._items.pop(idx)

    def get_items(self) -> list[str]:
        return list(self._items)

    def set_items(self, items: list[str]):
        self.listbox.delete(0, tk.END)
        self._items = []
        for item in items:
            if item in self._all_items:
                self._items.append(item)
                self.listbox.insert(tk.END, item)

    def clear(self):
        self.listbox.delete(0, tk.END)
        self._items = []


# ---------------------------------------------------------------------------
# Main tab
# ---------------------------------------------------------------------------

class FakemonTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=5)

        # Precompute display lists
        self._ability_display_names = sorted(
            _ability_display(a) for a in ABILITY_LOOKUP
        )
        self._move_display_names = sorted(
            _move_display(m) for m in MOVE_LOOKUP
        )
        self._tm_display_names = [
            v["display"] for v in sorted(TM_LOOKUP.values(), key=lambda x: x["display"])
        ]

        self._build_selector_bar()
        self._build_scrollable_form()

    # -----------------------------------------------------------------------
    # Top bar — select existing or new
    # -----------------------------------------------------------------------

    def _build_selector_bar(self):
        # Row 1: dropdown + New
        row1 = tk.Frame(self)
        row1.pack(fill="x", pady=(0, 2))

        self._select_var = tk.StringVar()
        self._select_box = ttk.Combobox(
            row1, textvariable=self._select_var,
            state="readonly", width=20,
        )
        self._select_box.pack(side="left", padx=(0, 4))
        self._select_box.bind("<<ComboboxSelected>>", self._on_load)

        new_btn = tk.Button(row1, text="＋ New", command=self._clear_form)
        new_btn.pack(side="left", padx=2)
        new_btn.bind("<Return>", lambda e: self._clear_form())

        # Row 2: Save + Delete
        row2 = tk.Frame(self)
        row2.pack(fill="x", pady=(0, 4))

        save_btn = ttk.Button(row2, text="💾 Save", command=self._save)
        save_btn.pack(side="left", padx=(0, 4))
        save_btn.bind("<Return>", lambda e: self._save())

        delete_btn = ttk.Button(row2, text="🗑️ Delete", command=self._delete)
        delete_btn.pack(side="left")
        delete_btn.bind("<Return>", lambda e: self._delete())

        self._refresh_selector()

    # -----------------------------------------------------------------------
    # Scrollable form
    # -----------------------------------------------------------------------

    def _build_scrollable_form(self):
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self._canvas  = tk.Canvas(container, borderwidth=0)
        scrollbar     = ttk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._form    = tk.Frame(self._canvas)

        self._form.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.create_window((0, 0), window=self._form, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel
        def _scroll(e):
            self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self._canvas.bind("<MouseWheel>", _scroll)
        self._form.bind("<MouseWheel>", _scroll)

        self._build_basic_section()
        self._build_stats_section()
        self._build_movement_section()
        self._build_proficiency_section()
        self._build_abilities_section()
        self._build_moves_section()

        # After all widgets are built, bind FocusIn to auto-scroll
        # and mousewheel to all widgets so scrolling works everywhere
        self._bind_scroll_on_focus(self._form)
        self._bind_mousewheel_to_form(self._form)

    def _bind_mousewheel_to_form(self, widget: tk.Widget):
        """Recursively bind mousewheel scrolling to all widgets in the form.
        For listboxes, scroll the listbox if it has overflow, otherwise scroll the canvas."""
        if isinstance(widget, tk.Listbox):
            def listbox_scroll(e, lb=widget):
                # If the listbox scrollbar is at both ends it doesn't need scrolling
                top, bottom = lb.yview()
                if top == 0.0 and bottom == 1.0:
                    # All items visible — scroll the canvas instead
                    self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
                else:
                    lb.yview_scroll(int(-1 * (e.delta / 120)), "units")
            widget.bind("<MouseWheel>", listbox_scroll)
        else:
            widget.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"), add="+")
        for child in widget.winfo_children():
            self._bind_mousewheel_to_form(child)

    def _bind_scroll_on_focus(self, widget: tk.Widget):
        """Recursively bind FocusIn to all widgets so the canvas scrolls to them."""
        widget.bind("<FocusIn>", self._scroll_to_widget, add="+")
        for child in widget.winfo_children():
            self._bind_scroll_on_focus(child)

    def _scroll_to_widget(self, event):
        """Scroll the canvas so the focused widget is visible."""
        widget = event.widget
        self._canvas.update_idletasks()

        # Get widget position relative to the form frame
        try:
            widget_y      = widget.winfo_rooty() - self._form.winfo_rooty()
            widget_height = widget.winfo_height()
            canvas_height = self._canvas.winfo_height()
            form_height   = self._form.winfo_height()

            if form_height == 0:
                return

            # Calculate the fraction to scroll to
            # Try to centre the widget in the visible area
            target_y = widget_y - (canvas_height // 2) + (widget_height // 2)
            target_y = max(0, min(target_y, form_height - canvas_height))
            fraction = target_y / form_height

            self._canvas.yview_moveto(fraction)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Section builders
    # -----------------------------------------------------------------------


    # -----------------------------------------------------------------------
    # Section helpers — all use padx=8 consistently
    # -----------------------------------------------------------------------

    def _section(self, title: str) -> ttk.LabelFrame:
        f = ttk.LabelFrame(self._form, text=title)
        f.pack(fill="x", padx=5, pady=4)
        return f

    def _row(self, parent, label: str, widget_factory, label_width=12):
        """
        Standard label+widget row.
        widget_factory is a callable that takes the frame as its parent
        and returns the widget. This ensures the widget is a child of the
        row frame, not the section, so tkinter places it correctly.
        """
        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=8, pady=2)
        tk.Label(frame, text=label, width=label_width, anchor="w").pack(side="left")
        widget = widget_factory(frame)
        widget.pack(side="left")
        return frame

    def _section_label(self, parent, text: str):
        """Sub-label inside a section — same left padding as _row."""
        tk.Label(parent, text=text, anchor="w").pack(anchor="w", padx=8, pady=(4, 0))

    @staticmethod
    def _filter_combo(var, box, all_items):
        typed    = var.get().strip().lower()
        filtered = all_items if not typed else [n for n in all_items if typed in n.lower()]
        box.configure(values=filtered)

    # -----------------------------------------------------------------------
    # Section builders
    # -----------------------------------------------------------------------

    def _build_basic_section(self):
        sec = self._section("📋 Basic Info")


    def _build_basic_section(self):
        sec = self._section("📋 Basic Info")

        self._name_var = tk.StringVar()
        self._row(sec, "Name:",
                  lambda f: tk.Entry(f, textvariable=self._name_var, width=22))

        self._type1_var = tk.StringVar()
        self._row(sec, "Type 1:",
                  lambda f: ttk.Combobox(f, textvariable=self._type1_var,
                  values=POKEMON_TYPES, state="readonly", width=14))

        self._type2_var = tk.StringVar(value="None")
        self._row(sec, "Type 2:",
                  lambda f: ttk.Combobox(f, textvariable=self._type2_var,
                  values=["None"] + POKEMON_TYPES, state="readonly", width=14))

        self._size_var = tk.StringVar()
        self._row(sec, "Size:",
                  lambda f: ttk.Combobox(f, textvariable=self._size_var,
                  values=SIZES, state="readonly", width=12))

        self._sr_var = tk.StringVar(value="1")
        self._row(sec, "SR:",
                  lambda f: tk.Spinbox(f, textvariable=self._sr_var,
                  from_=0, to=30, width=6))

        self._minlevel_var = tk.StringVar(value="1")
        self._row(sec, "Min Level:",
                  lambda f: tk.Spinbox(f, textvariable=self._minlevel_var,
                  from_=1, to=20, width=6))

        self._gender_var = tk.StringVar(value="50/50")
        self._row(sec, "Gender:",
                  lambda f: ttk.Combobox(f, textvariable=self._gender_var,
                  values=list(GENDER_RATIOS.keys()), state="readonly", width=20))

        self._section_label(sec, "Egg Groups:")
        eg_frame = tk.Frame(sec)
        eg_frame.pack(fill="x", padx=8, pady=(0, 4))
        eg_sb = ttk.Scrollbar(eg_frame, orient="vertical")
        self._egg_listbox = tk.Listbox(eg_frame, selectmode="multiple", height=5,
                                       width=24, yscrollcommand=eg_sb.set,
                                       exportselection=False, takefocus=1,
                                       activestyle="dotbox")
        eg_sb.config(command=self._egg_listbox.yview)
        for g in EGG_GROUPS:
            self._egg_listbox.insert(tk.END, g)
        self._egg_listbox.pack(side="left")
        eg_sb.pack(side="right", fill="y")
        self._egg_listbox.bind("<Return>", lambda e: self._toggle_listbox_item(self._egg_listbox))

        self._max_stage_var = tk.StringVar(value="1")
        self._cur_stage_var = tk.StringVar(value="1")

        def make_max_stage(f):
            box = ttk.Combobox(f, textvariable=self._max_stage_var,
                               values=["1","2","3"], state="readonly", width=6)
            box.bind("<<ComboboxSelected>>", self._update_stage_options)
            return box

        def make_cur_stage(f):
            self._cur_stage_box = ttk.Combobox(f, textvariable=self._cur_stage_var,
                                                values=["1"], state="readonly", width=6)
            return self._cur_stage_box

        self._row(sec, "Max Stage:", make_max_stage)
        self._row(sec, "Cur Stage:", make_cur_stage)

    def _update_stage_options(self, event=None):
        max_s = int(self._max_stage_var.get())
        options = [str(i) for i in range(1, max_s + 1)]
        self._cur_stage_box.configure(values=options)
        if self._cur_stage_var.get() not in options:
            self._cur_stage_var.set("1")

    def _build_stats_section(self):
        sec = self._section("📊 Combat Stats")

        self._stat_vars = {}
        grid = tk.Frame(sec)
        grid.pack(anchor="w", padx=8, pady=4)
        for i, (key, label) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            col = (i % 3) * 2
            row = i // 3
            tk.Label(grid, text=f"{label}:", width=5, anchor="w").grid(
                row=row, column=col, padx=(0, 2), pady=2)
            var = tk.StringVar(value="10")
            tk.Spinbox(grid, textvariable=var, from_=1, to=30,
                       width=4).grid(row=row, column=col+1, padx=(0, 10), pady=2)
            self._stat_vars[key] = var

        self._ac_var = tk.StringVar(value="12")
        self._row(sec, "AC:",
                  lambda f: tk.Spinbox(f, textvariable=self._ac_var, from_=1, to=30, width=6))

        self._hp_var = tk.StringVar(value="10")
        self._row(sec, "Base HP:",
                  lambda f: tk.Spinbox(f, textvariable=self._hp_var, from_=1, to=500, width=6))

        self._hitdice_var = tk.StringVar(value="d6")
        self._row(sec, "Hit Dice:",
                  lambda f: ttk.Combobox(f, textvariable=self._hitdice_var,
                  values=HIT_DICE, state="readonly", width=6))

    def _build_movement_section(self):
        sec = self._section("🏃 Movement & Senses")

        self._section_label(sec, "Speed:")
        self._speed_vars = {}
        for stype in SPEED_TYPES:
            row = tk.Frame(sec)
            row.pack(anchor="w", padx=8, pady=1)
            var_enabled = tk.BooleanVar()
            var_value   = tk.StringVar(value="30")
            cb = tk.Checkbutton(row, text=f"{stype}:", width=10, anchor="w",
                           variable=var_enabled)
            cb.pack(side="left")
            cb.bind("<Return>", lambda e, v=var_enabled: v.set(not v.get()))
            tk.Spinbox(row, textvariable=var_value, from_=5, to=300,
                       increment=5, width=5).pack(side="left")
            tk.Label(row, text="ft").pack(side="left", padx=(2, 0))
            self._speed_vars[stype] = (var_enabled, var_value)

        self._section_label(sec, "Senses:")
        self._sense_vars = {}
        for stype in SENSE_TYPES:
            row = tk.Frame(sec)
            row.pack(anchor="w", padx=8, pady=1)
            var_enabled = tk.BooleanVar()
            var_value   = tk.StringVar(value="60")
            cb = tk.Checkbutton(row, text=f"{stype}:", width=12, anchor="w",
                           variable=var_enabled)
            cb.pack(side="left")
            cb.bind("<Return>", lambda e, v=var_enabled: v.set(not v.get()))
            tk.Spinbox(row, textvariable=var_value, from_=5, to=300,
                       increment=5, width=5).pack(side="left")
            tk.Label(row, text="ft").pack(side="left", padx=(2, 0))
            self._sense_vars[stype] = (var_enabled, var_value)

    def _make_ability_row(self, parent, label: str) -> tk.StringVar:
        """Create a searchable ability row and return its StringVar."""
        var = tk.StringVar()
        items = self._ability_display_names

        def factory(f):
            box = ttk.Combobox(f, textvariable=var, values=items,
                               state="normal", width=20)
            var.trace_add("write", lambda *a: self._filter_combo(var, box, items))
            return box

        self._row(parent, label, factory)
        return var

    def _build_abilities_section(self):
        sec = self._section("⚡ Abilities")
        self._ability1_var      = self._make_ability_row(sec, "Ability 1 *:")
        self._ability2_var      = self._make_ability_row(sec, "Ability 2:")
        self._hidden_ability_var = self._make_ability_row(sec, "Hidden:")

    def _build_moves_section(self):
        sec = self._section("⚔️ Moves")

        self._move_editors: dict[str, SearchableListEditor] = {}
        for key, label in LEVEL_MOVE_KEYS:
            self._section_label(sec, f"{label}:")
            editor = SearchableListEditor(sec, self._move_display_names)
            editor.pack(fill="x", padx=8, pady=(0, 4))
            self._move_editors[key] = editor

        self._section_label(sec, "TMs:")
        tm_frame = tk.Frame(sec)
        tm_frame.pack(fill="x", padx=8, pady=(0, 4))
        tm_sb = ttk.Scrollbar(tm_frame, orient="vertical")
        self._tm_listbox = tk.Listbox(
            tm_frame, selectmode="multiple", height=6, width=30,
            yscrollcommand=tm_sb.set, exportselection=False,
        )
        tm_sb.config(command=self._tm_listbox.yview)
        for name in self._tm_display_names:
            self._tm_listbox.insert(tk.END, name)
        self._tm_listbox.pack(side="left", fill="x", expand=True)
        tm_sb.pack(side="right", fill="y")

    def _build_proficiency_section(self):
        sec = self._section("🛡️ Proficiencies")

        self._section_label(sec, "Saving Throws:")
        save_frame = tk.Frame(sec)
        save_frame.pack(anchor="w", padx=8, pady=(0, 4))
        self._save_vars = {}
        for i, key in enumerate(STAT_KEYS):
            var = tk.BooleanVar()
            cb = tk.Checkbutton(save_frame, text=key.upper(), variable=var)
            cb.grid(row=0, column=i, padx=(0, 4), pady=2)
            cb.bind("<Return>", lambda e, v=var: v.set(not v.get()))
            self._save_vars[key] = var

        self._section_label(sec, "Skills:")
        skill_frame = tk.Frame(sec)
        skill_frame.pack(fill="x", padx=8, pady=(0, 4))
        sk_sb = ttk.Scrollbar(skill_frame, orient="vertical")
        self._skill_listbox = tk.Listbox(
            skill_frame, selectmode="multiple", height=6, width=24,
            yscrollcommand=sk_sb.set, exportselection=False,
            takefocus=1, activestyle="dotbox",
        )
        sk_sb.config(command=self._skill_listbox.yview)
        for s in SKILLS_LIST:
            self._skill_listbox.insert(tk.END, s)
        self._skill_listbox.pack(side="left")
        sk_sb.pack(side="right", fill="y")
        self._skill_listbox.bind("<Return>", lambda e: self._toggle_listbox_item(self._skill_listbox))

    def _build_moves_section(self):
        sec = self._section("⚔️ Moves")

        self._move_editors: dict[str, SearchableListEditor] = {}
        for key, label in LEVEL_MOVE_KEYS:
            self._section_label(sec, f"{label}:")
            editor = SearchableListEditor(sec, self._move_display_names)
            editor.pack(fill="x", padx=8, pady=(0, 4))
            self._move_editors[key] = editor

        self._section_label(sec, "TMs:")
        tm_frame = tk.Frame(sec)
        tm_frame.pack(fill="x", padx=8, pady=(0, 4))
        tm_sb = ttk.Scrollbar(tm_frame, orient="vertical")
        self._tm_listbox = tk.Listbox(
            tm_frame, selectmode="multiple", height=6, width=30,
            yscrollcommand=tm_sb.set, exportselection=False,
        )
        tm_sb.config(command=self._tm_listbox.yview)
        for name in self._tm_display_names:
            self._tm_listbox.insert(tk.END, name)
        self._tm_listbox.pack(side="left", fill="x", expand=True)
        tm_sb.pack(side="right", fill="y")

    @staticmethod
    def _toggle_listbox_item(listbox: tk.Listbox):
        """Toggle selection of the active item in a multiselect listbox."""
        idx = listbox.index(tk.ACTIVE)
        if idx < 0:
            return
        if idx in listbox.curselection():
            listbox.selection_clear(idx)
        else:
            listbox.selection_set(idx)

    def _refresh_selector(self):
        names = get_fakemon_names()
        self._select_box.configure(values=names)
        if names and self._select_var.get() not in names:
            self._select_var.set("")

    def _on_load(self, event=None):
        name = self._select_var.get()
        if not name:
            return
        pokemon = get_fakemon(name)
        if pokemon:
            self._load_into_form(pokemon)

    def _clear_form(self):
        self._select_var.set("")
        self._name_var.set("")
        self._type1_var.set("")
        self._type2_var.set("None")
        self._size_var.set("")
        self._sr_var.set("1")
        self._minlevel_var.set("1")
        self._gender_var.set("50/50")
        self._max_stage_var.set("1")
        self._cur_stage_var.set("1")
        self._update_stage_options()
        self._egg_listbox.selection_clear(0, tk.END)
        for key in STAT_KEYS:
            self._stat_vars[key].set("10")
        self._ac_var.set("12")
        self._hp_var.set("10")
        self._hitdice_var.set("d6")
        for _, (en, _) in self._speed_vars.items():
            en.set(False)
        for _, (en, _) in self._sense_vars.items():
            en.set(False)
        for key in self._save_vars:
            self._save_vars[key].set(False)
        self._skill_listbox.selection_clear(0, tk.END)
        self._ability1_var.set("")
        self._ability2_var.set("")
        self._hidden_ability_var.set("")
        for editor in self._move_editors.values():
            editor.clear()
        self._tm_listbox.selection_clear(0, tk.END)
        # Scroll back to top so user sees the name field
        self._form.update_idletasks()
        self._canvas.yview_moveto(0)

    # -----------------------------------------------------------------------
    # Load existing pokemon into form
    # -----------------------------------------------------------------------

    def _load_into_form(self, p: dict):
        # Preserve the dropdown selection across _clear_form
        current_selection = self._select_var.get()
        self._clear_form()
        self._select_var.set(current_selection)

        self._name_var.set(p.get("name", ""))

        types = p.get("type", [])
        self._type1_var.set(types[0].capitalize() if len(types) > 0 else "")
        self._type2_var.set(types[1].capitalize() if len(types) > 1 else "None")

        self._size_var.set(p.get("size", "").capitalize())
        self._sr_var.set(str(p.get("sr", 1)))
        self._minlevel_var.set(str(p.get("minLevel", 1)))

        # Gender
        gender_raw = p.get("gender", "1:1")
        gender_label = next(
            (k for k, v in GENDER_RATIOS.items() if v == gender_raw),
            "50/50",
        )
        self._gender_var.set(gender_label)

        # Egg groups
        egg_groups = p.get("eggGroup", [])
        for i, g in enumerate(EGG_GROUPS):
            if g in egg_groups:
                self._egg_listbox.selection_set(i)

        # Evolution stage
        evo = p.get("evolution", {})
        max_stage = str(evo.get("maxStage", "1"))
        cur_stage = str(evo.get("stage", "1"))
        self._max_stage_var.set(max_stage)
        self._update_stage_options()
        self._cur_stage_var.set(cur_stage)

        # Stats
        attrs = p.get("attributes", {})
        for key in STAT_KEYS:
            self._stat_vars[key].set(str(attrs.get(key, 10)))

        self._ac_var.set(str(p.get("ac", 12)))
        self._hp_var.set(str(p.get("hp", 10)))
        self._hitdice_var.set(p.get("hitDice", "d6"))

        # Speed
        for entry in p.get("speed", []):
            stype = entry["type"].capitalize()
            if stype in self._speed_vars:
                en, val = self._speed_vars[stype]
                en.set(True)
                val.set(str(entry["value"]))

        # Senses
        for entry in p.get("senses", []):
            stype = entry["type"].capitalize()
            if stype in self._sense_vars:
                en, val = self._sense_vars[stype]
                en.set(True)
                val.set(str(entry["value"]))

        # Saving throws
        for st in p.get("savingThrows", []):
            if st in self._save_vars:
                self._save_vars[st].set(True)

        # Skills
        skills = p.get("skills", [])
        for i, s in enumerate(SKILLS_LIST):
            if s in skills:
                self._skill_listbox.selection_set(i)

        # Abilities
        abilities = p.get("abilities", [])
        normal = [a for a in abilities if not a.get("hidden")]
        hidden = [a for a in abilities if a.get("hidden")]
        if len(normal) > 0:
            self._ability1_var.set(_ability_display(normal[0]["id"]))
        if len(normal) > 1:
            self._ability2_var.set(_ability_display(normal[1]["id"]))
        if hidden:
            self._hidden_ability_var.set(_ability_display(hidden[0]["id"]))

        # Moves
        moves_data = p.get("moves", {})
        for key, _ in LEVEL_MOVE_KEYS:
            move_ids = moves_data.get(key, [])
            display  = [_move_display(m) for m in move_ids]
            self._move_editors[key].set_items(display)

        # TMs
        tm_ids = moves_data.get("tm", [])
        for i, name in enumerate(self._tm_display_names):
            tm_num = next(
                (k for k, v in TM_LOOKUP.items() if v["display"] == name), None
            )
            if tm_num in tm_ids:
                self._tm_listbox.selection_set(i)

    # -----------------------------------------------------------------------
    # Validation & save
    # -----------------------------------------------------------------------

    def _validate(self) -> str | None:
        """Return an error message if the form is invalid, else None."""
        if not self._name_var.get().strip():
            return "Name is required."
        if not self._type1_var.get():
            return "At least one type is required."
        if not self._size_var.get():
            return "Size is required."
        if not self._hitdice_var.get():
            return "Hit dice is required."
        if not self._gender_var.get():
            return "Gender ratio is required."
        if not self._egg_listbox.curselection():
            return "At least one egg group is required."
        if not self._ability1_var.get().strip():
            return "At least one ability is required."
        if not self._speed_vars:
            return "At least one speed type is required."
        speed_checked = any(en.get() for en, _ in self._speed_vars.values())
        if not speed_checked:
            return "At least one speed type must be checked."
        start_moves = self._move_editors["start"].get_items()
        if not start_moves:
            return "At least one starting move is required."
        return None

    def _resolve_ability_id(self, display_name: str) -> str | None:
        """Convert display name back to ability id."""
        if not display_name.strip():
            return None
        return next(
            (aid for aid, info in ABILITY_LOOKUP.items()
             if info.get("name") == display_name),
            None,
        )

    def _resolve_move_id(self, display_name: str) -> str | None:
        """Convert display name back to move id."""
        if not display_name.strip():
            return None
        return next(
            (mid for mid, info in MOVE_LOOKUP.items()
             if info.get("name") == display_name),
            None,
        )

    def _build_pokemon_dict(self) -> dict:
        """Assemble the full pokemon dict from form values."""
        name  = self._name_var.get().strip()
        types = [self._type1_var.get().lower()]
        if self._type2_var.get() != "None":
            types.append(self._type2_var.get().lower())

        # Egg groups
        egg_groups = [EGG_GROUPS[i] for i in self._egg_listbox.curselection()]

        # Evolution
        max_stage = self._max_stage_var.get()
        cur_stage = self._cur_stage_var.get()
        evolution = {
            "stage":    cur_stage,
            "maxStage": max_stage,
        }

        # Attributes
        attributes = {k: int(self._stat_vars[k].get()) for k in STAT_KEYS}

        # Speed
        speed = [
            {"type": stype.lower(), "value": int(val.get())}
            for stype, (en, val) in self._speed_vars.items()
            if en.get()
        ]

        # Senses
        senses = [
            {"type": stype.lower(), "value": int(val.get())}
            for stype, (en, val) in self._sense_vars.items()
            if en.get()
        ]

        # Saving throws
        saving_throws = [k for k, v in self._save_vars.items() if v.get()]

        # Skills
        skills = [SKILLS_LIST[i] for i in self._skill_listbox.curselection()]

        # Abilities
        abilities = []
        for display, hidden in [
            (self._ability1_var.get(), False),
            (self._ability2_var.get(), False),
            (self._hidden_ability_var.get(), True),
        ]:
            aid = self._resolve_ability_id(display)
            if aid:
                abilities.append({"id": aid, "hidden": hidden})

        # Moves
        moves = {}
        for key, _ in LEVEL_MOVE_KEYS:
            items = self._move_editors[key].get_items()
            ids   = [self._resolve_move_id(d) for d in items]
            moves[key] = [i for i in ids if i]

        # TMs — store as numbers matching tms.json ids
        selected_tm_names = [
            self._tm_display_names[i]
            for i in self._tm_listbox.curselection()
        ]
        tm_ids = [
            k for k, v in TM_LOOKUP.items()
            if v["display"] in selected_tm_names
        ]
        moves["tm"] = sorted(tm_ids)

        return {
            "id":           name.lower().replace(" ", "-"),
            "name":         name,
            "number":       0,
            "type":         types,
            "size":         self._size_var.get().lower(),
            "sr":           float(self._sr_var.get()),
            "minLevel":     int(self._minlevel_var.get()),
            "eggGroup":     egg_groups,
            "gender":       GENDER_RATIOS[self._gender_var.get()],
            "evolution":    evolution,
            "description":  f"A custom Pokémon named {name}.",
            "ac":           int(self._ac_var.get()),
            "hp":           int(self._hp_var.get()),
            "hitDice":      self._hitdice_var.get(),
            "speed":        speed,
            "senses":       senses,
            "attributes":   attributes,
            "skills":       skills,
            "savingThrows": saving_throws,
            "abilities":    abilities,
            "moves":        moves,
            "media": {
                "main":         "",
                "sprite":       "",
                "mainShiny":    "",
                "spriteShiny":  "",
            },
        }

    def _save(self):
        error = self._validate()
        if error:
            messagebox.showerror("Validation Error", error, parent=self)
            return

        pokemon = self._build_pokemon_dict()
        save_fakemon(pokemon)
        self._refresh_selector()
        self._select_var.set(pokemon["name"])
        messagebox.showinfo(
            "Saved", f"{pokemon['name']} saved to fakemon.json.", parent=self
        )

    def _delete(self):
        name = self._select_var.get()
        if not name:
            messagebox.showwarning("No Selection", "Select a Pokémon to delete.", parent=self)
            return
        if not messagebox.askyesno(
            "Delete", f"Delete {name} from fakemon.json?", parent=self
        ):
            return
        delete_fakemon(name)
        self._clear_form()
        self._refresh_selector()
