"""
gui/battler.py
BattlerFrame: the central panel containing the Pokémon sidebar,
info panel, health tracker, dice roller, and move buttons.
"""

import copy
import re
import random
import tkinter as tk
from tkinter import ttk, messagebox

import requests
from PIL import Image, ImageTk
from io import BytesIO

from config import SKILL_ABILITIES, DEFAULT_IMAGE_URL
from data_loader import MOVE_LOOKUP, move_id_from_display
from mechanics.combat import resolve_attack, format_battle_log
from mechanics.dice import ability_modifier
from gui.save_to_trainer_dialog import open_save_dialog
from gui.info_panel import PokemonInfoPanel
from gui.tooltip import ToolTip

BG_DEFAULT  = "#f0f0f0"
BG_SELECTED = "#cce5ff"
DRAG_THRESHOLD = 5       # pixels of movement before drag starts


class BattlerFrame(ttk.Frame):
    def __init__(self, parent, battle_log=None, all_pokemon_data=None):
        super().__init__(parent)
        self.battle_log      = battle_log
        self.all_pokemon_data = all_pokemon_data or []

        # Combat state
        self.pokemon_widgets      = {}   # id → {pokemon, container, ...}
        self.selected_pokemon_id  = None
        self._next_id             = 1
        self._pp                  = {}   # id → {move_name: pp}
        self._health              = {}   # id → {current, max}
        self._drag                = {"item": None, "y": 0, "start_y": 0, "dragging": False}
        self.move_buttons         = []

        self._build_layout()
        self._setup_mousewheel()

    # -----------------------------------------------------------------------
    # Layout construction
    # -----------------------------------------------------------------------

    def _build_layout(self):
        main = tk.Frame(self)
        main.pack(fill="both", expand=True)

        self._build_sidebar(main)

        right = tk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        self.info_panel = PokemonInfoPanel(right)
        self.info_panel.all_pokemon_data = self.all_pokemon_data
        self.info_panel.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Constrained container for bottom controls — matches info panel width
        bottom = tk.Frame(right)
        bottom.pack(side="top", anchor="w", padx=5, pady=0)

        self._build_health_bar(bottom)
        self._build_dice_roller(bottom)
        self._build_moves_area(bottom)

    def _build_sidebar(self, parent):
        container = tk.Frame(parent)
        container.pack(side="left", fill="y", padx=5, pady=5)

        self.sidebar_canvas = tk.Canvas(container, bg=BG_DEFAULT, width=120)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar = tk.Frame(self.sidebar_canvas, bg=BG_DEFAULT)

        self.sidebar.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")),
        )
        self.sidebar_canvas.create_window((0, 0), window=self.sidebar, anchor="nw")
        self.sidebar_canvas.configure(yscrollcommand=scrollbar.set)

        self.sidebar_canvas.pack(side="left", fill="y")
        scrollbar.pack(side="right", fill="y")
        self.sidebar_canvas.bind(
            "<MouseWheel>",
            lambda e: self.sidebar_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

    def _build_health_bar(self, parent):
        frame = tk.Frame(parent)
        frame.pack(side="top", anchor="w", pady=3)

        self.health_label = tk.Label(frame, text="HP: --/--", font=("Arial", 12, "bold"))
        self.health_label.pack(side="left")

        tk.Label(frame, text="Adjust HP:").pack(side="left", padx=(10, 2))
        self.health_entry = tk.Entry(frame, width=8)
        self.health_entry.pack(side="left", padx=(0, 4))
        self.health_entry.bind("<Return>", self._process_health_change)

        apply_btn = tk.Button(frame, text="Apply", command=self._process_health_change)
        apply_btn.pack(side="left")
        apply_btn.bind("<Return>", lambda e: self._process_health_change())

        # Dice roller
        tk.Label(frame, text="Dice:").pack(side="left", padx=(12, 2))
        self.dice_var = tk.StringVar(value="d20")
        dice_box = ttk.Combobox(
            frame, textvariable=self.dice_var,
            values=["d4", "d6", "d8", "d10", "d12", "d20", "d100"],
            state="readonly", width=5,
        )
        dice_box.pack(side="left", padx=(0, 4))

        roll_dice_btn = tk.Button(frame, text="🎲 Roll", command=self._roll_dice)
        roll_dice_btn.pack(side="left")
        roll_dice_btn.bind("<Return>", lambda e: self._roll_dice())
        dice_box.bind("<Return>", lambda e: self._roll_dice())

    def _build_dice_roller(self, parent):
        frame = tk.Frame(parent)
        frame.pack(side="top", anchor="w", pady=3)

        tk.Label(frame, text="Roll Type:").pack(side="left", padx=(0, 2))
        self.roll_type_var = tk.StringVar()
        self.roll_type_dropdown = ttk.Combobox(
            frame, textvariable=self.roll_type_var,
            values=["Ability Check", "Skill Check", "Saving Throw"],
            state="readonly", width=11,
        )
        self.roll_type_dropdown.pack(side="left", padx=(0, 4))
        self.roll_type_dropdown.bind("<<ComboboxSelected>>", self._update_roll_options)
        self.roll_type_dropdown.bind("<Return>", lambda e: self._update_roll_options())

        tk.Label(frame, text="Roll:").pack(side="left", padx=(0, 2))
        self.roll_option_var = tk.StringVar()
        self.roll_option_dropdown = ttk.Combobox(
            frame, textvariable=self.roll_option_var, state="readonly", width=13,
        )
        self.roll_option_dropdown.pack(side="left", padx=(0, 4))
        self.roll_option_dropdown.bind("<Return>", lambda e: self._make_roll())

        roll_btn = tk.Button(frame, text="🎲 Roll", command=self._make_roll)
        roll_btn.pack(side="left", padx=(0, 4))
        roll_btn.bind("<Return>", lambda e: self._make_roll())

        init_btn = tk.Button(frame, text="⚡ Init", command=self._roll_initiative)
        init_btn.pack(side="left")
        init_btn.bind("<Return>", lambda e: self._roll_initiative())

    def _build_moves_area(self, parent):
        header = tk.Frame(parent)
        header.pack(side="top", anchor="w", pady=(5, 0))
        tk.Label(header, text="⚔️ Moves", font=("Arial", 10, "bold")).pack(side="left")
        reset_pp_btn = tk.Button(
            header, text="🔄 Reset PP",
            command=lambda: self._reset_pp(self.selected_pokemon_id),
        )
        reset_pp_btn.pack(side="left", padx=5)
        reset_pp_btn.bind("<Return>", lambda e: self._reset_pp(self.selected_pokemon_id))

        self.moves_frame = tk.Frame(parent)
        self.moves_frame.pack(side="top", anchor="w", pady=3)

    # -----------------------------------------------------------------------
    # Adding / removing Pokémon
    # -----------------------------------------------------------------------

    def add_pokemon(self, pokemon: dict):
        pid = self._next_id
        self._next_id += 1

        instance = copy.deepcopy(pokemon)
        instance["_id"] = pid

        container = tk.Frame(self.sidebar, relief="raised", bd=2, bg=BG_DEFAULT, cursor="hand2")
        container.pack(pady=2, fill="x")

        name_label = tk.Label(
            container, text=instance["name"],
            font=("Arial", 10, "bold"), bg=BG_DEFAULT, cursor="hand2",
        )
        name_label.pack(anchor="w")

        img_label = self._load_sprite(container, instance.get("image_url", ""), pid)

        trash_btn = tk.Button(
            container, text="🗑️", fg="red", borderwidth=0, cursor="hand2",
            bg=BG_DEFAULT, command=lambda p=pid: self._confirm_remove(p),
        )
        trash_btn.place_forget()

        self._bind_drag(container, pid, trash_btn)
        self._bind_hover_trash(container, trash_btn)

        self.pokemon_widgets[pid] = {
            "pokemon":    instance,
            "container":  container,
            "name_label": name_label,
            "img_label":  img_label,
            "trash_btn":  trash_btn,
        }

        self._init_health(pid)
        self._bind_mousewheel_recursive(container)
        self.select_pokemon(pid)

    def _load_sprite(self, container, url: str, pid: int) -> tk.Label | None:
        if not url or not url.strip().startswith("http"):
            url = DEFAULT_IMAGE_URL
        try:
            img = Image.open(BytesIO(requests.get(url, timeout=5).content))
            img = img.resize((80, 80), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            label = tk.Label(container, image=tk_img, cursor="hand2", bg=BG_DEFAULT)
            label.image = tk_img
            label.pack(pady=2)
            label.bind("<Button-1>", lambda e, p=pid: self.select_pokemon(p))
            return label
        except Exception:
            return None

    def _confirm_remove(self, pid: int):
        name = self.pokemon_widgets[pid]["pokemon"]["name"]
        if messagebox.askyesno("Remove Pokémon", f"Remove {name} from the tracker?"):
            self._remove_pokemon(pid)

    def _remove_pokemon(self, pid: int):
        widgets = self.pokemon_widgets.pop(pid, None)
        if widgets:
            widgets["container"].destroy()
        if self.selected_pokemon_id == pid:
            self.selected_pokemon_id = None
            self.info_panel.display_pokemon({"name": "No Pokémon selected"})
            for btn in self.move_buttons:
                btn.destroy()
            self.move_buttons = []
            self.health_label.config(text="HP: --/--")

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------

    def select_pokemon(self, pid: int):
        # Deselect previous
        if self.selected_pokemon_id and self.selected_pokemon_id in self.pokemon_widgets:
            for key in ("container", "name_label", "img_label", "trash_btn"):
                w = self.pokemon_widgets[self.selected_pokemon_id].get(key)
                if w:
                    w.config(bg=BG_DEFAULT)

        # Select new
        widgets = self.pokemon_widgets[pid]
        for key in ("container", "name_label", "img_label", "trash_btn"):
            w = widgets.get(key)
            if w:
                w.config(bg=BG_SELECTED)

        self.selected_pokemon_id = pid
        self.info_panel.display_pokemon(
            widgets["pokemon"],
            show_save_button=True,
            on_open_leveler=self._open_in_leveler,
        )
        self._display_moves(widgets["pokemon"])

        if pid not in self._health:
            self._init_health(pid)
        self._update_health_display()

        # No separate action buttons needed — they're in the info panel now

    def _save_to_trainer(self):
        if not self.selected_pokemon_id:
            return
        pokemon = self.pokemon_widgets[self.selected_pokemon_id]["pokemon"]
        open_save_dialog(self, pokemon)
        # Refresh the trainer tab if app reference is available
        if hasattr(self, "app"):
            self.app.refresh_trainer_tab()

    def _open_in_leveler(self):
        if not self.selected_pokemon_id:
            return
        pokemon = self.pokemon_widgets[self.selected_pokemon_id]["pokemon"]
        if hasattr(self, "app"):
            self.app.leveler_tab.load_pokemon(pokemon)
            self.app.switch_to_leveler()

    # -----------------------------------------------------------------------
    # Moves
    # -----------------------------------------------------------------------

    def _display_moves(self, pokemon: dict):
        for btn in self.move_buttons:
            btn.destroy()
        self.move_buttons = []
        for frame in getattr(self, "_move_row_frames", []):
            frame.destroy()
        self._move_row_frames = []
        # Clear any leftover labels (e.g. "No moves available")
        for widget in self.moves_frame.winfo_children():
            widget.destroy()

        moves = pokemon.get("moves", [])
        if not moves:
            tk.Label(self.moves_frame, text="No moves available").pack()
            return

        pid = pokemon["_id"]
        if pid not in self._pp:
            self._pp[pid] = {
                m: (MOVE_LOOKUP.get(move_id_from_display(m), {}).get("pp") or 0)
                for m in moves
            }

        for i, move_name in enumerate(moves):
            pp  = self._pp[pid][move_name]
            row = i // 2
            col = i % 2

            # Create a row frame on first column of each row
            if col == 0:
                row_frame = tk.Frame(self.moves_frame)
                row_frame.pack(anchor="w", pady=1)
                self._move_row_frames = getattr(self, "_move_row_frames", [])
                self._move_row_frames.append(row_frame)
            else:
                row_frame = self._move_row_frames[row]

            btn = tk.Button(
                row_frame,
                text=f"{move_name} (PP: {pp})",
                width=18,
                state="disabled" if pp <= 0 else "normal",
                command=lambda m=move_name, p=pid: self._use_move(m, p),
            )
            btn.pack(side="left", padx=(0, 4))
            btn.bind("<Return>", lambda e, m=move_name, p=pid: self._use_move(m, p))
            self.move_buttons.append(btn)
            self._add_move_tooltip(btn, move_name)

    def _add_move_tooltip(self, btn: tk.Button, move_name: str):
        move_id   = move_id_from_display(move_name)
        move_data = MOVE_LOOKUP.get(move_id)
        if not move_data:
            return
        power = move_data.get("power", "N/A")
        if isinstance(power, list):
            power = "/".join(p.upper() for p in power)
        desc = "\n".join(str(d) for d in move_data.get("description", []) if isinstance(d, str))
        if move_data.get("higherLevels"):
            desc += f"\n\n{move_data['higherLevels']}"
        text = "\n".join([
            f"Type: {move_data.get('type', 'N/A').capitalize()}",
            f"Power: {power}",
            f"Time: {move_data.get('time', 'N/A')}",
            f"Duration: {move_data.get('duration', 'N/A')}",
            f"Range: {move_data.get('range', 'N/A')}",
            "", desc,
        ])
        ToolTip(btn, text)

    def _use_move(self, move_name: str, pid: int):
        pp_dict = self._pp.get(pid)
        if not pp_dict or move_name not in pp_dict:
            return

        if pp_dict[move_name] > 0:
            pp_dict[move_name] -= 1
            for btn in self.move_buttons:
                if btn.cget("text").startswith(move_name):
                    btn.config(text=f"{move_name} (PP: {pp_dict[move_name]})")
                    if pp_dict[move_name] <= 0:
                        btn.config(state="disabled")
                    break

        pokemon  = self.pokemon_widgets[pid]["pokemon"]
        move_id  = move_id_from_display(move_name)

        try:
            result  = resolve_attack(pokemon, move_id)
            message = format_battle_log(result)
        except Exception as e:
            message = f"{pokemon['name']} uses {move_name}!\n\nError: {e}"

        if self.battle_log:
            tag = None
            if "(CRITICAL HIT!)" in message:
                tag = "crit"
            elif "(CRITICAL MISS!)" in message:
                tag = "miss"
            self.battle_log.log(message, tag=tag)

    def _reset_pp(self, pid: int):
        if pid is None or pid not in self._pp:
            return
        pokemon = self.pokemon_widgets[pid]["pokemon"]
        for move_name in pokemon.get("moves", []):
            move_data = MOVE_LOOKUP.get(move_id_from_display(move_name))
            if move_data:
                self._pp[pid][move_name] = move_data["pp"]
        self._display_moves(pokemon)

    # -----------------------------------------------------------------------
    # Health tracking
    # -----------------------------------------------------------------------

    def _init_health(self, pid: int):
        max_hp = self.pokemon_widgets[pid]["pokemon"].get("hp", 100)
        self._health[pid] = {"current": max_hp, "max": max_hp}

    def _update_health_display(self):
        if not self.selected_pokemon_id or self.selected_pokemon_id not in self._health:
            self.health_label.config(text="HP: --/--", fg="black")
            return
        h       = self._health[self.selected_pokemon_id]
        current = h["current"]
        max_hp  = h["max"]
        pct     = current / max_hp if max_hp > 0 else 0

        if pct < 0.10:
            color = "red"
        elif pct < 0.50:
            color = "orange"
        else:
            color = "black"

        self.health_label.config(text=f"HP: {current}/{max_hp}", fg=color)

    def _process_health_change(self, event=None):
        pid = self.selected_pokemon_id
        if pid is None or pid not in self._health:
            return

        raw = self.health_entry.get().strip()
        self.health_entry.delete(0, tk.END)
        if not raw:
            return

        h    = self._health[pid]
        name = self.pokemon_widgets[pid]["pokemon"]["name"]
        old  = h["current"]
        cap  = h["max"]

        try:
            if raw.startswith("="):
                h["current"] = max(0, min(int(raw[1:]), cap))
                diff = h["current"] - old
                msg = f"{name} HP set to {h['current']}/{cap}"
                if diff:
                    msg += f" ({'+' if diff > 0 else ''}{diff})"
            elif raw.startswith("+"):
                heal = int(raw[1:])
                h["current"] = min(h["current"] + heal, cap)
                actual = h["current"] - old
                msg = (
                    f"{name} heals {actual} HP ({old} → {h['current']}/{cap})"
                    if actual > 0 else f"{name} is already at full HP."
                )
            elif raw.startswith("-"):
                dmg = int(raw[1:])
                h["current"] = max(h["current"] - dmg, 0)
                actual = old - h["current"]
                msg = f"{name} takes {actual} damage ({old} → {h['current']}/{cap})"
                if h["current"] == 0:
                    msg += " and is knocked out!"
            else:
                h["current"] = max(0, min(int(raw), cap))
                diff = h["current"] - old
                msg = f"{name} HP set to {h['current']}/{cap}"
                if diff:
                    msg += f" ({'+' if diff > 0 else ''}{diff})"
        except ValueError:
            msg = f"Invalid HP input: '{raw}'. Use +X, -X, =X, or a plain number."

        self._update_health_display()
        if self.battle_log:
            self.battle_log.log(msg)

    # -----------------------------------------------------------------------
    # Dice rolling
    # -----------------------------------------------------------------------

    def _update_roll_options(self, event=None):
        roll_type = self.roll_type_var.get()
        if roll_type == "Ability Check":
            options = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        elif roll_type == "Skill Check":
            options = list(SKILL_ABILITIES.keys())
        elif roll_type == "Saving Throw":
            options = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        else:
            options = []
        self.roll_option_dropdown.configure(values=options)
        self.roll_option_var.set("")

    def _make_roll(self):
        pid = self.selected_pokemon_id
        if pid is None:
            self._log("No Pokémon selected.")
            return

        roll_type   = self.roll_type_var.get()
        roll_option = self.roll_option_var.get()
        if not roll_type or not roll_option:
            self._log("Please select a roll type and option.")
            return

        pokemon = self.pokemon_widgets[pid]["pokemon"]
        scores  = self._parse_scores(pokemon)

        if roll_type == "Skill Check":
            ability_key = SKILL_ABILITIES.get(roll_option, "wis")
        else:
            ability_key = roll_option.lower()[:3]

        score = scores.get(ability_key, 10)
        mod   = ability_modifier(score)
        prof  = pokemon.get("proficiency_bonus", 0)

        is_prof = False
        if roll_type == "Saving Throw":
            is_prof = ability_key in pokemon.get("saving_throws", "").lower()
        elif roll_type == "Skill Check":
            is_prof = roll_option.lower().replace(" ", "") in pokemon.get("skills", "").lower().replace(" ", "")

        d20   = random.randint(1, 20)
        total = d20 + mod + (prof if is_prof else 0)
        prof_text = f" + {prof} prof" if is_prof else ""

        note = ""
        if d20 == 20:
            note = "\nNATURAL 20!"
        elif d20 == 1:
            note = "\nNATURAL 1!"

        self._log(
            f"{pokemon['name']} makes a {roll_option} {roll_type.lower()}:\n"
            f"Result: {total} [d20: {d20} + {mod} {ability_key.upper()}{prof_text}]{note}"
        )

    def _roll_dice(self):
        """Roll the selected die and log the result."""
        import random
        die = self.dice_var.get()
        sides = int(die[1:])
        result = random.randint(1, sides)
        self.battle_log.log(f"🎲 {die} roll: {result}")

    def _roll_initiative(self):
        pid = self.selected_pokemon_id
        if pid is None:
            self._log("No Pokémon selected.")
            return

        pokemon = self.pokemon_widgets[pid]["pokemon"]
        scores  = self._parse_scores(pokemon)
        dex_mod = ability_modifier(scores.get("dex", 10))
        d20     = random.randint(1, 20)
        total   = d20 + dex_mod

        self._log(
            f"{pokemon['name']} rolls Initiative:\n"
            f"Result: {total} [d20: {d20} + {dex_mod} DEX]"
        )

    def _log(self, message: str):
        if self.battle_log:
            self.battle_log.log(message)

    @staticmethod
    def _parse_scores(pokemon: dict) -> dict[str, int]:
        scores = {}
        for line in pokemon.get("ability_scores", "").split("\n"):
            parts = line.split(":")
            if len(parts) >= 2:
                key = parts[0].strip().lower()
                m = re.search(r"\d+", parts[1])
                scores[key] = int(m.group()) if m else 10
        return scores

    # -----------------------------------------------------------------------
    # Drag and drop
    # -----------------------------------------------------------------------

    def _bind_drag(self, container: tk.Frame, pid: int, trash_btn: tk.Button):
        def bind_recursive(widget):
            widget.bind("<ButtonPress-1>",   lambda e, p=pid: self._drag_start(e, p))
            widget.bind("<B1-Motion>",       lambda e, p=pid: self._drag_motion(e, p))
            widget.bind("<ButtonRelease-1>", lambda e, p=pid: self._drag_release(e, p))
            for child in widget.winfo_children():
                if child != trash_btn:
                    bind_recursive(child)
        bind_recursive(container)

    def _bind_hover_trash(self, container: tk.Frame, trash_btn: tk.Button):
        show = lambda e: trash_btn.place(relx=1.0, rely=0.0, x=20, y=-5, anchor="ne")
        hide = lambda e: trash_btn.place_forget()
        container.bind("<Enter>", show)
        container.bind("<Leave>", hide)
        for child in container.winfo_children():
            child.bind("<Enter>", show)
            child.bind("<Leave>", hide)

    def _drag_start(self, event, pid: int):
        self._drag = {"item": pid, "y": event.y_root, "start_y": event.y_root, "dragging": False}

    def _drag_motion(self, event, pid: int):
        if self._drag["item"] is None:
            return
        if not self._drag["dragging"]:
            if abs(event.y_root - self._drag["start_y"]) < DRAG_THRESHOLD:
                return
            self._drag["dragging"] = True
            self.pokemon_widgets[pid]["container"].config(cursor="fleur")

        current_y   = event.y_root
        order       = list(self.pokemon_widgets.keys())
        drag_index  = order.index(pid)

        for idx, other_pid in enumerate(order):
            if other_pid == pid:
                continue
            c = self.pokemon_widgets[other_pid]["container"]
            if c.winfo_rooty() <= current_y <= c.winfo_rooty() + c.winfo_height():
                pos = "before" if idx < drag_index else "after"
                self._swap_positions(pid, other_pid, pos)
                break

    def _drag_release(self, event, pid: int):
        if self._drag["item"] is not None:
            self.pokemon_widgets[pid]["container"].config(cursor="hand2")
            if not self._drag["dragging"]:
                self.select_pokemon(pid)
        self._drag = {"item": None, "y": 0, "start_y": 0, "dragging": False}

    def _swap_positions(self, drag_id: int, target_id: int, position: str):
        items = list(self.pokemon_widgets.items())
        drag_idx   = next(i for i, (p, _) in enumerate(items) if p == drag_id)
        target_idx = next(i for i, (p, _) in enumerate(items) if p == target_id)

        # Already adjacent in the right direction — nothing to do
        if (position == "before" and drag_idx == target_idx - 1) or \
           (position == "after"  and drag_idx == target_idx + 1):
            return

        for _, widgets in items:
            widgets["container"].pack_forget()

        new_order = []
        for pid, widgets in items:
            if pid == drag_id:
                continue
            if pid == target_id:
                if position == "before":
                    new_order.append((drag_id, self.pokemon_widgets[drag_id]))
                new_order.append((pid, widgets))
                if position == "after":
                    new_order.append((drag_id, self.pokemon_widgets[drag_id]))
            else:
                new_order.append((pid, widgets))

        for _, widgets in new_order:
            widgets["container"].pack(pady=2, fill="x")

        self.pokemon_widgets = dict(new_order)

    # -----------------------------------------------------------------------
    # Mousewheel
    # -----------------------------------------------------------------------

    def _setup_mousewheel(self):
        def handler(event):
            try:
                widget = self.winfo_containing(event.x_root, event.y_root)
            except Exception:
                return  # catches 'popdown' and other internal tkinter widgets
            if not widget:
                return
            # Walk up to check ancestry
            w = widget
            while w:
                if w == self:
                    break
                parent = w.winfo_parent()
                try:
                    w = self.nametowidget(parent) if parent else None
                except Exception:
                    return  # widget not in normal tree (e.g. combobox popdown)
            else:
                return  # not a child of this frame

            # Route to appropriate scrollable area
            w = widget
            while w:
                if w in (self.sidebar_canvas, self.sidebar):
                    self.sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return
                try:
                    w = self.nametowidget(w.winfo_parent()) if w.winfo_parent() else None
                except Exception:
                    break

            if hasattr(self.info_panel, "canvas"):
                self.info_panel.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.winfo_toplevel().bind_all("<MouseWheel>", handler)
        self._mousewheel_handler = handler

    def _bind_mousewheel_recursive(self, widget: tk.Widget):
        if hasattr(self, "_mousewheel_handler"):
            widget.bind("<MouseWheel>", self._mousewheel_handler)
            for child in widget.winfo_children():
                self._bind_mousewheel_recursive(child)
