import json
import os
import random
import copy
import re
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter import messagebox
import requests
from PIL import Image, ImageTk
from io import BytesIO


if getattr(sys, 'frozen', False):
    # Running as PyInstaller executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # Running as Python script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


AREA_FILE = os.path.join(SCRIPT_DIR, "areas.json")
POKEMON_FILE = os.path.join(SCRIPT_DIR, "pokemon.json")
TYPECHART_FILE = os.path.join(SCRIPT_DIR, "typechart.json")
ABILITIES_FILE = os.path.join(SCRIPT_DIR, "abilities.json")
MOVES_FILE = os.path.join(SCRIPT_DIR, "moves.json")
HELDITEMS_FILE = os.path.join(SCRIPT_DIR, "helditems.json")


# ---------------- NATURE TABLE ----------------
natures_table = [
    {"name": "Hardy", "increase": None,
        "decrease": None, "range": range(1, 5)},
    {"name": "Lonely", "increase": "str",
        "decrease": "con", "range": range(5, 9)},
    {"name": "Brave", "increase": "str",
        "decrease": "dex", "range": range(9, 13)},
    {"name": "Adamant", "increase": "str",
        "decrease": "wis", "range": range(13, 17)},
    {"name": "Naughty", "increase": "str",
        "decrease": "cha", "range": range(17, 21)},
    {"name": "Bold", "increase": "con",
        "decrease": "str", "range": range(21, 25)},
    {"name": "Docile", "increase": None,
        "decrease": None, "range": range(25, 29)},
    {"name": "Relaxed", "increase": "con",
        "decrease": "dex", "range": range(29, 33)},
    {"name": "Impish", "increase": "con",
        "decrease": "wis", "range": range(33, 37)},
    {"name": "Lax", "increase": "con",
        "decrease": "cha", "range": range(37, 41)},
    {"name": "Timid", "increase": "dex",
        "decrease": "str", "range": range(41, 45)},
    {"name": "Hasty", "increase": "dex",
        "decrease": "con", "range": range(45, 49)},
    {"name": "Serious", "increase": None,
        "decrease": None, "range": range(49, 53)},
    {"name": "Jolly", "increase": "dex",
        "decrease": "wis", "range": range(53, 57)},
    {"name": "Naive", "increase": "dex",
        "decrease": "cha", "range": range(57, 61)},
    {"name": "Modest", "increase": "wis",
        "decrease": "str", "range": range(61, 65)},
    {"name": "Mild", "increase": "wis",
        "decrease": "con", "range": range(65, 69)},
    {"name": "Quiet", "increase": "wis",
        "decrease": "dex", "range": range(69, 73)},
    {"name": "Bashful", "increase": None,
        "decrease": None, "range": range(73, 77)},
    {"name": "Rash", "increase": "wis",
        "decrease": "cha", "range": range(77, 81)},
    {"name": "Calm", "increase": "cha",
        "decrease": "str", "range": range(81, 85)},
    {"name": "Gentle", "increase": "cha",
        "decrease": "con", "range": range(85, 89)},
    {"name": "Sassy", "increase": "cha",
        "decrease": "dex", "range": range(89, 93)},
    {"name": "Careful", "increase": "cha",
        "decrease": "wis", "range": range(93, 97)},
    {"name": "Quirky", "increase": None,
        "decrease": None, "range": range(97, 101)},
]

# ---------------- JSON LOAD ----------------


def load_json(file_path):
    if not os.path.exists(file_path):
        print(f"❌ {file_path} not found!")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------- TYPE CLASS ----------------
POKEMON_TYPE_CHART = load_json(TYPECHART_FILE)
POKEMON_TYPES = list(POKEMON_TYPE_CHART.keys())

# ---------------- ABILITIES LOAD ----------------
ABILITIES_DATA = load_json(ABILITIES_FILE).get("items", [])
ABILITY_LOOKUP = {a["id"]: a for a in ABILITIES_DATA}

# ---------------- MOVES LOAD ----------------
MOVES_DATA = load_json(MOVES_FILE).get("moves", [])
MOVE_LOOKUP = {m["id"]: m for m in MOVES_DATA}


def roll_dice(dice_str):
    match = re.match(r"(\d+)d(\d+)", dice_str)
    if not match:
        return int(dice_str)  # fallback if just a number
    n, m = map(int, match.groups())
    return sum(random.randint(1, m) for _ in range(n))


def parse_damage_from_description(description_text, move_data):
    """Extract damage dice and type from move description"""
    # Patterns for moves WITH ability modifier (+ MOVE)
    move_modifier_patterns = [
        r'(\d+d\d+(?:\s*\+\s*\d+)?)\s*\+?\s*MOVE\s+(\w+)\s+damage',
        r'(\d+d\d+)\s*\+?\s*MOVE\s+(\w+)\s+damage',
        r'takes\s+(\d+d\d+(?:\s*\+\s*\d+)?)\s*\+?\s*MOVE\s+(\w+)\s+damage',
        r'deals?\s+(\d+d\d+(?:\s*\+\s*\d+)?)\s*\+?\s*MOVE\s+(\w+)\s+damage'
    ]

    # First, try to match patterns with MOVE modifier
    for pattern in move_modifier_patterns:
        match = re.search(pattern, description_text, re.IGNORECASE)
        if match:
            dice_str = match.group(1).strip()
            damage_type = match.group(2).strip().lower()
            return dice_str, damage_type  # Will include ability mod

    # If no MOVE found, try patterns for flat damage (no ability modifier)
    flat_damage_patterns = [
        r'doing\s+(\d+d\d+)\s+(\w+)\s+damage',
        r'takes\s+(\d+d\d+)\s+(\w+)\s+damage',
        r'deals?\s+(\d+d\d+)\s+(\w+)\s+damage',
        r'(\d+d\d+)\s+(\w+)\s+damage'
    ]

    for pattern in flat_damage_patterns:
        match = re.search(pattern, description_text, re.IGNORECASE)
        if match:
            dice_str = match.group(1).strip()
            damage_type = match.group(2).strip().lower()
            return dice_str, damage_type  # Will NOT include ability mod

    return None, None


def get_scaled_damage_dice(move_data, pokemon_level):
    """Apply higher level damage scaling if applicable"""
    higher_levels = move_data.get("higherLevels", "")
    if not higher_levels:
        return None

    # Parse higher levels text for damage scaling
    # Example: "The damage dice roll for this move changes to 2d4 at level 5, 1d12 at level 10, and 4d4 at level 17."
    level_patterns = [
        (r'(\d+d\d+) at level (\d+)', lambda m: (m.group(1), int(m.group(2))))
    ]

    scalings = []
    for pattern, parser in level_patterns:
        for match in re.finditer(pattern, higher_levels):
            dice, level = parser(match)
            scalings.append((level, dice))

    # Sort by level and find the highest applicable scaling
    scalings.sort(reverse=True)  # Highest level first
    for level_req, dice in scalings:
        if pokemon_level >= level_req:
            return dice

    return None


def calculate_move_damage(pokemon, move_data, ability_mod=0, is_crit=False):
    """Calculate damage for a move including ability modifier, level scaling, critical hits, and STAB"""
    # Get description text
    description_text = ""
    for d in move_data.get("description", []):
        if isinstance(d, str):
            description_text += d.lower() + " "

    has_move_modifier = bool(
        re.search(r'\+?\s*MOVE\s+\w+\s+damage', description_text, re.IGNORECASE))

    # Parse base damage from description
    base_dice_str, damage_type = parse_damage_from_description(
        description_text, move_data)

    if not base_dice_str:
        return None, None, None, None, False, 0

    # Check for level-based scaling and use the best available dice
    pokemon_level = pokemon.get("level", 1)
    scaled_dice = get_scaled_damage_dice(move_data, pokemon_level)

    # Use scaled dice if available, otherwise use base dice
    dice_str = scaled_dice if scaled_dice else base_dice_str

    # Roll the damage dice
    base_damage = roll_dice(dice_str)

    # Handle critical hits - roll damage dice again and add
    crit_damage = 0
    if is_crit:
        crit_damage = roll_dice(dice_str)
        total_dice_damage = base_damage + crit_damage
    else:
        total_dice_damage = base_damage

    # Calculate STAB bonus - ALWAYS check for type matching
    stab_bonus = 0
    move_type = move_data.get("type", "").lower()
    pokemon_types = pokemon.get("types", "").lower().split("/")
    pokemon_types = [t.strip() for t in pokemon_types]

    if move_type in pokemon_types:
        # STAB applies differently based on whether move uses modifiers
        if has_move_modifier:
            stab_bonus = ability_mod  # STAB doubles the Move Power Mod
        else:
            # For flat damage moves, STAB still adds the ability modifier once
            stab_bonus = ability_mod

    # Add ability modifier and STAB bonus
    if has_move_modifier:
        total_damage = total_dice_damage + ability_mod + stab_bonus
    else:
        total_damage = total_dice_damage + stab_bonus  # Only STAB, no base modifier

    # Return all components including crit info and STAB
    return base_damage, total_damage, damage_type, dice_str, crit_damage, stab_bonus


def attack_roll(pokemon, move_id):
    move_data = MOVE_LOOKUP.get(move_id)
    if not move_data:
        return "Move not found", None

    # Parse ability scores
    ability_scores = {}
    for line in pokemon["ability_scores"].split("\n"):
        parts = line.split(":")
        if len(parts) >= 2:
            ab = parts[0].strip().lower()
            val_match = re.search(r"\d+", parts[1])
            val = int(val_match.group()) if val_match else 10
            ability_scores[ab] = val

    # Determine best ability modifier - handle status moves properly
    chosen_ability = None
    highest_mod = 0
    power_abilities = move_data.get("power")

    # Handle different power types
    if power_abilities == "none" or power_abilities is None:
        # Status move - no ability modifier needed
        highest_mod = 0
        chosen_ability = None
    elif isinstance(power_abilities, list) and power_abilities:
        # Attack move - find best ability modifier
        best_mod = float('-inf')  # Start with very low value
        for ability in power_abilities:
            score = ability_scores.get(ability, 10)
            mod = ability_modifier(score)
            if mod > best_mod:
                best_mod = mod
                chosen_ability = ability

        # Set the highest modifier (could be negative)
        highest_mod = best_mod if best_mod != float('-inf') else 0
    else:
        # Fallback for other power types
        highest_mod = 0
        chosen_ability = None

    prof = pokemon.get("proficiency_bonus", 0)

    # Get description for save detection
    description_text = ""
    for d in move_data.get("description", []):
        if isinstance(d, str):
            description_text += d.lower() + " "

    # Check if move uses MOVE modifier
    has_move_modifier = bool(
        re.search(r'\+?\s*MOVE\s+\w+\s+damage', description_text, re.IGNORECASE))

    # Detect saving throw type from description
    save_type = None
    if "save" in description_text:
        # Look for patterns like "STR save", "DEX save", etc.
        save_patterns = [
            r'\b(str|strength)\s+save',
            r'\b(dex|dexterity)\s+save',
            r'\b(con|constitution)\s+save',
            r'\b(int|intelligence)\s+save',
            r'\b(wis|wisdom)\s+save',
            r'\b(cha|charisma)\s+save'
        ]

        for pattern in save_patterns:
            match = re.search(pattern, description_text, re.IGNORECASE)
            if match:
                save_ability = match.group(1).lower()
                if save_ability in ['str', 'strength']:
                    save_type = 'STR'
                elif save_ability in ['dex', 'dexterity']:
                    save_type = 'DEX'
                elif save_ability in ['con', 'constitution']:
                    save_type = 'CON'
                elif save_ability in ['int', 'intelligence']:
                    save_type = 'INT'
                elif save_ability in ['wis', 'wisdom']:
                    save_type = 'WIS'
                elif save_ability in ['cha', 'charisma']:
                    save_type = 'CHA'
                break

    # Check if move has both attack roll and save (like Vice Grip)
    has_save = "save" in description_text
    has_attack = isinstance(
        power_abilities, list) and power_abilities and ("make a melee attack" in description_text or "make a ranged attack" in description_text or "make an attack" in description_text)

# Only roll d20 and check for crit if the move involves an attack roll
    d20_roll = None
    is_crit = False
    if has_attack:
        d20_roll = random.randint(1, 20)
        is_crit = (d20_roll == 20)
    else:
        # For non-attack moves, set d20_roll to 0 so math works
        d20_roll = 0

    # Calculate damage
    damage_calc = calculate_move_damage(
        pokemon, move_data, highest_mod, is_crit
    )

    if damage_calc[0] is not None:
        base_damage, total_damage, damage_type, dice_str, crit_damage, stab_bonus = damage_calc
    else:
        base_damage = total_damage = damage_type = dice_str = crit_damage = stab_bonus = None

    # Format results - handle moves with both mechanics
    if has_attack and has_save:
        # Moves like Vice Grip that have both attack and save
        total = d20_roll + highest_mod + prof
        ability_name = chosen_ability.upper() if chosen_ability else "N/A"

        if is_crit:
            attack_result = f"{total} [d20: {d20_roll} + {highest_mod} {ability_name} + {prof} prof] CRITICAL HIT!"
        else:
            attack_result = f"{total} [d20: {d20_roll} + {highest_mod} {ability_name} + {prof} prof]"

        # Add save DC info
        save_dc = 8 + highest_mod + prof
        if save_type:
            attack_result += f" | Save DC: {save_dc} ({save_type})"
        else:
            attack_result += f" | Save DC: {save_dc}"

        if base_damage is not None:
            if is_crit and crit_damage > 0:
                if has_move_modifier and stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage} + {highest_mod} {ability_name} + {stab_bonus} STAB]"
                elif has_move_modifier:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage} + {highest_mod} {ability_name}]"
                elif stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage} + {stab_bonus} STAB]"
                else:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage}]"
            else:
                if has_move_modifier and stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage} + {highest_mod} {ability_name} + {stab_bonus} STAB]"
                elif has_move_modifier:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage} + {highest_mod} {ability_name}]"
                elif stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage} + {stab_bonus} STAB]"
                else:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage}]"
        else:
            damage_result = None

    elif has_save and not has_attack:
        # Save-only moves - no attack roll, no crit
        total = 8 + highest_mod + prof
        ability_name = chosen_ability.upper() if chosen_ability else "N/A"

        if save_type:
            attack_result = f"Saving Throw DC: {total} ({save_type}) [8 + {highest_mod} {ability_name} + {prof} prof]"
        else:
            attack_result = f"Saving Throw DC: {total} [8 + {highest_mod} {ability_name} + {prof} prof]"

        # Damage for save-only moves - no crit possible
        if base_damage is not None:
            if has_move_modifier and stab_bonus > 0:
                damage_result = f"Damage on failed save: {total_damage} {damage_type} [{dice_str}: {base_damage} + {highest_mod} {ability_name} + {stab_bonus} STAB]"
            elif has_move_modifier:
                damage_result = f"Damage on failed save: {total_damage} {damage_type} [{dice_str}: {base_damage} + {highest_mod} {ability_name}]"
            elif stab_bonus > 0:
                damage_result = f"Damage on failed save: {total_damage} {damage_type} [{dice_str}: {base_damage} + {stab_bonus} STAB]"
            else:
                damage_result = f"Damage on failed save: {total_damage} {damage_type} [{dice_str}: {base_damage}]"
        else:
            damage_result = None

    elif isinstance(power_abilities, list) and power_abilities:
        # Attack-only moves
        total = d20_roll + highest_mod + prof
        ability_name = chosen_ability.upper() if chosen_ability else "N/A"

        if is_crit:
            attack_result = f"{total} [d20: {d20_roll} + {highest_mod} {ability_name} + {prof} prof] CRITICAL HIT!"
        else:
            attack_result = f"{total} [d20: {d20_roll} + {highest_mod} {ability_name} + {prof} prof]"

        if base_damage is not None:
            if is_crit and crit_damage > 0:
                if has_move_modifier and stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage} + {highest_mod} {ability_name} + {stab_bonus} STAB]"
                elif has_move_modifier:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage} + {highest_mod} {ability_name}]"
                elif stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage} + {stab_bonus} STAB]"
                else:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [CRITICAL! {dice_str}: {base_damage} + {dice_str}: {crit_damage}]"
            else:
                if has_move_modifier and stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage} + {highest_mod} {ability_name} + {stab_bonus} STAB]"
                elif has_move_modifier:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage} + {highest_mod} {ability_name}]"
                elif stab_bonus > 0:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage} + {stab_bonus} STAB]"
                else:
                    damage_result = f"Damage on hit: {total_damage} {damage_type} [{dice_str}: {base_damage}]"
        else:
            damage_result = None
    else:
        attack_result = "See move description"
        damage_result = None

    return attack_result, damage_result


def format_message(pokemon_name, move_name, attack_result, damage_result=None):
    """Format battle log messages in Roll20 style"""

    # Start with the move announcement
    message_parts = [f"{pokemon_name} uses {move_name}!"]
    message_parts.append("")  # Empty line for spacing

    # Parse attack roll information
    if "Saving Throw DC:" in attack_result:
        # Extract DC, save type, and breakdown - updated regex to handle save type
        dc_match = re.search(
            r"Saving Throw DC: (\d+)(?: \((\w+)\))? \[(.*?)\]", attack_result)
        if dc_match:
            dc_value = dc_match.group(1)
            save_type = dc_match.group(2)  # This could be None if no save type
            breakdown = dc_match.group(3)

            if save_type:
                message_parts.append(
                    f"Spell Save DC: {dc_value} ({save_type})")
            else:
                message_parts.append(f"Spell Save DC: {dc_value}")
            message_parts.append(f"  └ {breakdown}")
    elif "CRITICAL HIT!" in attack_result:
        # Extract attack roll with crit
        attack_match = re.search(
            r"(\d+) \[(.*?)\] CRITICAL HIT!", attack_result)
        if attack_match:
            total = attack_match.group(1)
            breakdown = attack_match.group(2)
            message_parts.append(f"Attack Roll: {total} (CRITICAL HIT!)")
            message_parts.append(f"  └ {breakdown}")
    elif re.search(r"^\d+", attack_result):
        # Regular attack roll
        attack_match = re.search(r"(\d+) \[(.*?)\]", attack_result)
        if attack_match:
            total = attack_match.group(1)
            breakdown = attack_match.group(2)
            message_parts.append(f"Attack Roll: {total}")
            message_parts.append(f"  └ {breakdown}")
    else:
        # Other cases (like "See move description")
        message_parts.append(f"Result: {attack_result}")

    # Parse damage information if present
    if damage_result:
        if "CRITICAL!" in damage_result:
            # Critical damage parsing
            damage_match = re.search(
                r"Damage on (?:hit|failed save): (\d+) (\w+) \[CRITICAL! (.*?)\]", damage_result)
            if damage_match:
                total_damage = damage_match.group(1)
                damage_type = damage_match.group(2)
                breakdown = damage_match.group(3)
                message_parts.append(
                    f"Damage: {total_damage} {damage_type} (CRITICAL!)")
                message_parts.append(f"  └ {breakdown}")
        else:
            # Regular damage parsing
            damage_match = re.search(
                r"Damage on (?:hit|failed save): (\d+) (\w+) \[(.*?)\]", damage_result)
            if damage_match:
                total_damage = damage_match.group(1)
                damage_type = damage_match.group(2)
                breakdown = damage_match.group(3)
                message_parts.append(f"Damage: {total_damage} {damage_type}")
                message_parts.append(f"  └ {breakdown}")

    return "\n".join(message_parts)


class PokemonType:
    def __init__(self, types: list[str]):
        if not types or len(types) > 2:
            raise ValueError("PokemonType must have 1 or 2 types")
        for t in types:
            if t not in POKEMON_TYPE_CHART:
                raise ValueError(f"Invalid Pokémon type: {t}")
        self.types = types

    def defensive_multipliers(self) -> dict[str, float]:
        multipliers = {}
        for attack_type in POKEMON_TYPES:
            multiplier = 1.0
            for t in self.types:
                multiplier *= POKEMON_TYPE_CHART[t][attack_type]
            multipliers[attack_type] = multiplier
        return multipliers

    def vulnerabilities(self) -> list[str]:
        return sorted([t for t, m in self.defensive_multipliers().items() if m > 1])

    def resistances(self) -> list[str]:
        return sorted([t for t, m in self.defensive_multipliers().items() if 0 < m < 1])

    def immunities(self) -> list[str]:
        imm = sorted(
            [t for t, m in self.defensive_multipliers().items() if m == 0])
        return imm if imm else ["None"]

# ---------------- AREA CHOICE ----------------


def choose_area(areas):
    if not areas:
        print("❌ No areas available.")
        return None
    print("\nAvailable areas:")
    for area_name in areas.keys():
        print(f"- {area_name}")
    while True:
        choice = input("Type the area name: ").strip()
        area_key = next(
            (name for name in areas if name.lower() == choice.lower()), None)
        if area_key:
            return areas[area_key]
        else:
            print("❌ Area not found. Try again.")

# ---------------- NATURE APPLY ----------------


def apply_nature(attributes):
    nature_roll = random.randint(1, 100)
    nature = next(nt for nt in natures_table if nature_roll in nt["range"])
    modified_attributes = attributes.copy()
    incr_text = decr_text = ""
    if nature["increase"]:
        modified_attributes[nature["increase"]] += 1
        incr_text = f"+1 {nature['increase'].capitalize()}"
    if nature["decrease"]:
        modified_attributes[nature["decrease"]] -= 1
        decr_text = f"-1 {nature['decrease'].capitalize()}"
    if incr_text or decr_text:
        nature_text = f"{nature['name']} ({incr_text}{', ' if incr_text and decr_text else ''}{decr_text})"
    else:
        nature_text = nature['name']
    return nature["name"], modified_attributes, nature_text

# ---------------- ABILITY MODIFIER ----------------


def ability_modifier(score):
    return (score - 10) // 2

# ---------------- PROFICIENCY BONUS ----------------


def proficiency_bonus(level):
    if 1 <= level <= 4:
        return 2
    elif 5 <= level <= 8:
        return 3
    elif 9 <= level <= 12:
        return 4
    elif 13 <= level <= 16:
        return 5
    else:  # 17+
        return 6


# ---------------- HIT DICE ----------------
hit_dice_bonus = {
    "d4": 3,
    "d6": 4,
    "d8": 5,
    "d10": 6,
    "d12": 7,
    "d20": 11
}

# ---------------- ASI LOGIC ----------------
ASI_BREAKPOINTS = [4, 8, 12, 16]


def apply_asi(full_pokemon, attributes: dict, level: int) -> dict:
    import random

    modified_attributes = attributes.copy()

    # Determine ASIs per breakpoint
    evo = full_pokemon.get("evolution")
    max_stage = int(evo.get("maxStage")) if evo and "maxStage" in evo else 1
    asi_per_bp = 4 if max_stage == 1 else 3 if max_stage == 2 else 2

    pokemon_min_level = full_pokemon.get("minLevel", 1)
    # Breakpoints strictly above minLevel and <= current level
    valid_bps = [bp for bp in ASI_BREAKPOINTS if bp >
                 pokemon_min_level and bp <= level]
    total_asi = asi_per_bp * len(valid_bps)

    stats = list(modified_attributes.keys())

    for _ in range(total_asi):
        # pick a random stat that is not capped at 20
        uncapped_stats = [s for s in stats if modified_attributes[s] < 20]
        if not uncapped_stats:
            break  # all stats capped
        choice = random.choice(uncapped_stats)
        modified_attributes[choice] += 1

    return modified_attributes


# ---------------- FORMAT LIST ----------------


def format_list(lst):
    return ", ".join(f"{i['type'].capitalize()} {i['value']}ft" if isinstance(i, dict) else str(i) for i in lst)

# ---------------- PICK RANDOM POKEMON ----------------


def pick_random_pokemon(area, all_pokemon_data):
    if not area.get("pokemon"):
        print("❌ This area has no Pokémon!")
        return None

    p = random.choice(area["pokemon"])
    level = random.randint(p["min_level"], p["max_level"])
    full_pokemon = next(
        (pk for pk in all_pokemon_data if pk["name"].lower() == p["name"].lower()), None)

    # ------------------ SHINY CHECK ------------------
    is_shiny = random.randint(1, 100) == 1
    display_name = p['name'].upper()

    image_url = ""
    if full_pokemon:
        if is_shiny:
            image_url = full_pokemon["media"].get("mainShiny", "")
        else:
            image_url = full_pokemon["media"].get("main", "")

    # Defaults
    gender_text = types_text = size_text = ac_text = speed_text = senses_text = hp_text = ability_scores_text = nature_text = "Unknown"
    skills_text = saving_throws_text = ""
    prof_bonus = proficiency_bonus(level)
    vulnerabilities = resistances = immunities = []

# ---------------- Held Item Check ----------------
    if random.randint(1, 4) == 1:  # 25% chance
        held_items = load_json(HELDITEMS_FILE).get("items", [])
        if held_items:
            held_item_text = random.choice(held_items)
        else:
            held_item_text = "None"
    else:
        held_item_text = "None"

    if full_pokemon:
        # Gender
        gender_info = full_pokemon.get("gender", "Unknown")
        if gender_info.lower() == "genderless" or gender_info == "0:0":
            gender_text = "Genderless"
        elif ":" in gender_info:
            female_ratio, male_ratio = map(int, gender_info.split(":"))
            gender_text = random.choices(
                ["Female", "Male"], weights=[female_ratio, male_ratio], k=1
            )[0] if female_ratio + male_ratio > 0 else "Genderless"

        # Types, size, AC, HP, speed, senses
        types_list = full_pokemon.get("type", [])
        types_text = "/".join([t.capitalize()
                              for t in types_list]) or "Unknown"
        size_text = full_pokemon.get("size", "Unknown").capitalize()
        ac_text = full_pokemon.get("ac", "Unknown")
        hp_text = full_pokemon.get("hp", "Unknown")
        speed_text = format_list(full_pokemon.get("speed", []))
        senses_text = format_list(full_pokemon.get("senses", []))

        # Type calculations
        pokemon_type = PokemonType(types_list)
        vulnerabilities = pokemon_type.vulnerabilities()
        resistances = pokemon_type.resistances()
        immunities = pokemon_type.immunities()

        # ---------------- Ability Scores ----------------
        base_attributes = full_pokemon.get("attributes", {}).copy()

        # Apply nature first
        _, nature_modified_attributes, nature_text = apply_nature(
            base_attributes)

        # Then apply ASIs on top of nature-modified stats
        modified_attributes = apply_asi(
            full_pokemon, nature_modified_attributes, level)

        # Format ability scores text
        ability_scores_text = "\n".join(
            f"{k.upper()}: {v} ({'+' if (mod := ability_modifier(v)) >= 0 else ''}{mod})"
            for k, v in modified_attributes.items()
        )

        # ---------------- Skills & Saving Throws ----------------
        skills_list = full_pokemon.get("skills", [])
        saving_throws_list = full_pokemon.get("savingThrows", [])
        skills_text = ", ".join(s.capitalize()
                                for s in skills_list) if skills_list else "None"
        saving_throws_text = ", ".join(
            s.upper() for s in saving_throws_list) if saving_throws_list else "None"

        # ---------------- Moves selection ----------------
        moves_data = full_pokemon.get("moves", {})
        available_moves = []
        available_moves.extend(moves_data.get("start", []))
        for lvl_key in ["level2", "level6", "level10", "level14", "level18"]:
            lvl_num = int(lvl_key.replace("level", ""))
            if level >= lvl_num:
                available_moves.extend(moves_data.get(lvl_key, []))
        moves_chosen = random.sample(available_moves, min(
            4, len(available_moves))) if available_moves else ["None"]
        moves_chosen = [m.replace("-", " ").title() for m in moves_chosen]

        # ---------------- Abilities ----------------
        abilities_data = full_pokemon.get("abilities", [])
        normal_abilities = [a["id"]
                            for a in abilities_data if not a.get("hidden", False)]
        hidden_abilities = [a["id"]
                            for a in abilities_data if a.get("hidden", False)]
        chosen_ability = random.choice(
            normal_abilities) if normal_abilities else "None"

        def ability_with_desc(ability_id):
            ability_info = ABILITY_LOOKUP.get(ability_id)
            if ability_info:
                return f"Ability: {ability_info['name']} - {ability_info['description']}\n"
            return ability_id

        abilities_text = ability_with_desc(chosen_ability)
        if hidden_abilities:
            hidden_texts = [ability_with_desc(h) for h in hidden_abilities]
            abilities_text += "\nHidden " + "\n".join(hidden_texts)

        # ---------------- HP based on level ----------------
        base_hp = full_pokemon["hp"]
        hit_dice = full_pokemon["hitDice"]
        pokemon_min_level = full_pokemon["minLevel"]
        con_mod = ability_modifier(modified_attributes["con"])
        levels_above_min = max(0, level - pokemon_min_level)
        additional_hp = levels_above_min * (hit_dice_bonus[hit_dice] + con_mod)
        hp_text = base_hp + additional_hp

    return {
        "name": display_name,
        "shiny": is_shiny,
        "level": level,
        "sr": full_pokemon.get("sr", 0),
        "proficiency_bonus": prof_bonus,
        "gender": gender_text,
        "types": types_text,
        "size": size_text,
        "nature": nature_text,
        "ac": ac_text,
        "hp": hp_text,
        "speed": speed_text,
        "senses": senses_text,
        "ability_scores": ability_scores_text,
        "skills": skills_text,
        "saving_throws": saving_throws_text,
        "vulnerabilities": vulnerabilities,
        "resistances": resistances,
        "immunities": immunities,
        "moves": moves_chosen,
        "abilities": abilities_text,
        "held_item": held_item_text,
        "image_url": image_url
    }


# ---------------- REUSABLE INFO PANEL ----------------

class PokemonInfoPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def add_description_tooltip(self, widget, pokemon_name):
        """Add a tooltip with the Pokemon's description"""
        # Find the full pokemon data to get the description
        full_pokemon = None
        if hasattr(self, 'all_pokemon_data'):
            for pokemon_data in self.all_pokemon_data:
                if pokemon_data["name"].lower() == pokemon_name.lower():
                    full_pokemon = pokemon_data
                    break

        if full_pokemon and full_pokemon.get("description"):
            description = full_pokemon["description"]
            ToolTip(widget, description)
        else:
            # Fallback if no description found
            ToolTip(widget, f"No description available for {pokemon_name}")

    def display_pokemon(self, pokemon):
        # Clear previous widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        wrap_len = 450

        # --- Header ---
        shiny_text = " 🌟 Shiny! 🌟" if pokemon.get("shiny", False) else ""
        name = pokemon.get("name", "Unknown")
        level = pokemon.get("level", "")
        gender = pokemon.get("gender", "")

        # Only show level and gender if they exist
        level_text = f" (Lv {level})" if level else ""
        gender_text = f" - {gender}" if gender else ""

        name_label = tk.Label(
            self.scrollable_frame,
            text=f"{name}{level_text}{gender_text}{shiny_text}",
            font=("Arial", 14, "bold"),
            wraplength=wrap_len,
            justify="left"
        )
        name_label.pack(anchor="w")

        # Add tooltip with description to the name label
        self.add_description_tooltip(name_label, name)

        tk.Label(
            self.scrollable_frame,
            text=f"Type: {pokemon.get('types', '')}",
            font=("Arial", 12),
            wraplength=wrap_len,
            justify="left"
        ).pack(anchor="w")

        # --- Basics ---
        basics_frame = ttk.LabelFrame(self.scrollable_frame, text="📌 Basics")
        basics_frame.pack(fill="x", pady=5)

        if pokemon.get("size"):
            tk.Label(basics_frame, text=f"Size: {pokemon['size']}",
                     wraplength=wrap_len, justify="left").pack(anchor="w")
        if pokemon.get("nature"):
            tk.Label(basics_frame, text=f"Nature: {pokemon['nature']}",
                     wraplength=wrap_len, justify="left").pack(anchor="w")
        if pokemon.get("held_item"):
            tk.Label(basics_frame, text=f"Held Item: {pokemon['held_item']}",
                     wraplength=wrap_len, justify="left").pack(anchor="w")

            # Display SR
        if pokemon.get("sr") is not None:
            tk.Label(basics_frame, text=f"SR: {pokemon['sr']}",
                     wraplength=wrap_len, justify="left").pack(anchor="w")

        # Calculate and display XP
        if pokemon.get("level") and pokemon.get("sr") is not None:
            xp_value = 200 * pokemon["level"] * pokemon["sr"]
            tk.Label(basics_frame, text=f"Exp: {int(xp_value)}",
                     wraplength=wrap_len, justify="left").pack(anchor="w")

        # --- Stats ---
        if any(pokemon.get(field) for field in ["ac", "hp", "speed", "ability_scores"]):
            stats_frame = ttk.LabelFrame(self.scrollable_frame, text="📊 Stats")
            stats_frame.pack(fill="x", pady=5)

            if pokemon.get("ac"):
                tk.Label(stats_frame, text=f"Armor Class: {pokemon['ac']}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")
            if pokemon.get("hp"):
                tk.Label(stats_frame, text=f"HP: {pokemon['hp']}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")
            if pokemon.get("speed"):
                tk.Label(stats_frame, text=f"Speed: {pokemon['speed']}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")

            # --- Ability Scores ---
            if pokemon.get("ability_scores"):
                abilities_text = ""
                for line in pokemon['ability_scores'].split("\n"):
                    abilities_text += f"    {line}\n"

                tk.Label(stats_frame, text=abilities_text.rstrip(),
                         font=("Courier", 10),
                         justify="left").pack(anchor="w", pady=2)

        # --- Skills & Proficiencies ---
        if any(pokemon.get(field) for field in ["proficiency_bonus", "skills", "saving_throws"]):
            skills_frame = ttk.LabelFrame(
                self.scrollable_frame, text="🛡️ Skills & Proficiencies")
            skills_frame.pack(fill="x", pady=5)

            if pokemon.get("proficiency_bonus"):
                tk.Label(
                    skills_frame, text=f"Proficiency Bonus: +{pokemon.get('proficiency_bonus', 0)}",
                    wraplength=wrap_len, justify="left").pack(anchor="w")

            if pokemon.get("skills"):
                tk.Label(skills_frame, text=f"Skills: {pokemon.get('skills', 'None')}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")

            if pokemon.get("saving_throws"):
                tk.Label(skills_frame, text=f"Saving Throws: {pokemon.get('saving_throws', 'None')}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")

        # --- Defenses ---
        if any(pokemon.get(field) for field in ["vulnerabilities", "resistances", "immunities"]):
            defenses_frame = ttk.LabelFrame(
                self.scrollable_frame, text="🧪 Defenses")
            defenses_frame.pack(fill="x", pady=5)

            vulnerabilities = pokemon.get('vulnerabilities', [])
            resistances = pokemon.get('resistances', [])
            immunities = pokemon.get('immunities', [])

            if vulnerabilities:
                tk.Label(defenses_frame, text=f"Vulnerabilities: {', '.join(vulnerabilities)}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")

            if resistances:
                tk.Label(defenses_frame, text=f"Resistances: {', '.join(resistances)}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")

            if immunities:
                tk.Label(defenses_frame, text=f"Immunities: {', '.join(immunities)}",
                         wraplength=wrap_len, justify="left").pack(anchor="w")

        # --- Moves & Abilities ---
        if any(pokemon.get(field) for field in ["moves", "abilities"]):
            moves_frame = ttk.LabelFrame(
                self.scrollable_frame, text="⚔️ Moves & Abilities")
            moves_frame.pack(fill="x", pady=5)

            moves = pokemon.get('moves', [])
            if moves:
                tk.Label(moves_frame, text=f"Moves: {', '.join(moves)}",
                         wraplength=wrap_len, justify="left").pack(anchor="w", pady=2)

            if pokemon.get("abilities"):
                tk.Label(moves_frame, text=f"{pokemon.get('abilities', '')}",
                         wraplength=wrap_len, justify="left").pack(anchor="w", pady=2)

# ---------------- GUI APP ----------------


class WilranApp(ttk.Frame):
    def __init__(self, parent, areas, all_pokemon_data, battler_frame):
        super().__init__(parent, padding=10)
        self.areas = areas
        self.all_pokemon_data = all_pokemon_data
        self.battler_frame = battler_frame
        self.current_pokemon = None

        # --- Area selection ---
        area_frame = tk.Frame(self)
        area_frame.pack(pady=5)

        tk.Label(area_frame, text="Choose an Area:").pack(
            anchor="w")  # label on top

        self.area_var = tk.StringVar()
        self.area_dropdown = ttk.Combobox(
            area_frame, textvariable=self.area_var, values=list(areas.keys()), state="readonly"
        )
        self.area_dropdown.pack(anchor="w", pady=(0, 5)
                                )  # dropdown below label

        self.randomize_button = tk.Button(
            area_frame, text="🎲 Randomize Pokémon", command=self.randomize_pokemon
        )
        self.randomize_button.pack(anchor="w")  # packs below dropdown

        # --- Action buttons: Add to Battler + View Pokémon ---
        action_frame = tk.Frame(self)
        action_frame.pack(pady=5)

        self.add_button = ttk.Button(
            action_frame, text="➕ Add to Tracker", command=self.add_to_battler, state="disabled"
        )
        self.add_button.pack(side="left", padx=5)

        self.view_button = ttk.Button(
            action_frame, text="👀 View Pokémon", command=self.view_pokemon, state="disabled"
        )
        self.view_button.pack(side="left", padx=5)

        # --- Compact Pokémon display ---
        self.pokemon_frame = ttk.Frame(
            self, relief="raised", padding=5, borderwidth=2)
        self.pokemon_frame.pack(fill="x", pady=10)

        # Image on the left
        self.pokemon_img_label = tk.Label(self.pokemon_frame)
        self.pokemon_img_label.pack(side="left", padx=5, pady=5)

        # Text on the right
        self.pokemon_text_frame = ttk.Frame(self.pokemon_frame)
        self.pokemon_text_frame.pack(side="left", padx=5, pady=5, anchor="n")

        self.name_label = tk.Label(
            self.pokemon_text_frame, font=("Arial", 14, "bold"))
        self.name_label.pack(anchor="w")
        self.level_label = tk.Label(
            self.pokemon_text_frame, font=("Arial", 12))
        self.level_label.pack(anchor="w")
        self.gender_label = tk.Label(
            self.pokemon_text_frame, font=("Arial", 12))
        self.gender_label.pack(anchor="w")
        self.shiny_label = tk.Label(
            self.pokemon_text_frame, font=("Arial", 12), fg="gold")
        self.shiny_label.pack(anchor="w")

    def randomize_pokemon(self):
        area_name = self.area_var.get()
        if not area_name:
            return

        area = self.areas[area_name]
        pokemon = pick_random_pokemon(area, self.all_pokemon_data)
        if not pokemon:
            return

        self.current_pokemon = pokemon
        self.add_button.config(state="normal")
        self.view_button.config(state="normal")

        # Display image
        if pokemon.get("image_url"):
            try:
                response = requests.get(pokemon["image_url"])
                pil_img = Image.open(BytesIO(response.content))
                pil_img = pil_img.resize((100, 100), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(pil_img)
                self.pokemon_img_label.configure(image=tk_img)
                self.pokemon_img_label.image = tk_img
            except:
                self.pokemon_img_label.configure(text="No Image")

        # Display text
        pokemon_name = pokemon["name"]

        self.name_label.config(text=pokemon_name)
        self.level_label.config(text=f"Level: {pokemon['level']}")
        self.gender_label.config(text=f"Gender: {pokemon['gender']}")
        self.shiny_label.config(
            text="🌟 Shiny! 🌟" if pokemon.get("shiny") else "")

    def add_to_battler(self):
        if self.current_pokemon:
            self.battler_frame.add_pokemon(self.current_pokemon)

    def view_pokemon(self):
        if not self.current_pokemon:
            return

        # --- New window ---
        view_window = tk.Toplevel(self)
        view_window.title(f"{self.current_pokemon['name']} Info")
        view_window.geometry("500x725")

        info_panel = PokemonInfoPanel(view_window)
        info_panel.pack(fill="both", expand=True, padx=10, pady=10)
        info_panel.display_pokemon(self.current_pokemon)


# ---------------- Battler ----------------

class BattlerFrame(ttk.Frame):
    def __init__(self, parent, battle_log=None, all_pokemon_data=None):
        super().__init__(parent)
        self.battle_log = battle_log  # reference to BattleLogFrame
        self.all_pokemon_data = all_pokemon_data or []

        # Main layout: sidebar + info panel
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True)

        # Left sidebar with scrollbar: Pokémon slots (compact version)
        sidebar_container = tk.Frame(main_frame)
        sidebar_container.pack(side="left", fill="y", padx=5, pady=5)

        # Create canvas and scrollbar for Pokemon list
        self.sidebar_canvas = tk.Canvas(
            sidebar_container, bg="#f0f0f0", width=120)  # Set canvas width directly
        sidebar_scrollbar = ttk.Scrollbar(
            sidebar_container, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar = tk.Frame(self.sidebar_canvas, bg="#f0f0f0")

        self.sidebar.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.configure(
                scrollregion=self.sidebar_canvas.bbox("all"))
        )

        self.sidebar_canvas.create_window(
            (0, 0), window=self.sidebar, anchor="nw")
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        # Pack canvas and scrollbar
        self.sidebar_canvas.pack(side="left", fill="y")  # Remove expand=True
        sidebar_scrollbar.pack(side="right", fill="y")

        # Bind mousewheel scrolling
        def _on_mousewheel(event):
            self.sidebar_canvas.yview_scroll(
                int(-1*(event.delta/120)), "units")

        self.sidebar_canvas.bind("<MouseWheel>", _on_mousewheel)

        # Right side container
        right_container = tk.Frame(main_frame)
        right_container.pack(side="left", fill="both", expand=True)

        # Info panel
        self.info_panel = PokemonInfoPanel(right_container)
        self.info_panel.all_pokemon_data = self.all_pokemon_data  # Add this line
        self.info_panel.pack(side="top", fill="both",
                             expand=True, padx=5, pady=5)

        # Health tracker frame (between info panel and moves)
        health_frame = tk.Frame(right_container)
        health_frame.pack(side="top", fill="x", padx=5, pady=5)

        # Health display
        self.health_label = tk.Label(health_frame, text="HP: --/--",
                                     font=("Arial", 12, "bold"))
        self.health_label.pack(side="left")

        # Health input
        tk.Label(health_frame, text="Adjust HP:").pack(
            side="left", padx=(20, 5))
        self.health_entry = tk.Entry(health_frame, width=10)
        self.health_entry.pack(side="left", padx=5)
        self.health_entry.bind("<Return>", self.process_health_change)

        health_apply_btn = tk.Button(health_frame, text="Apply",
                                     command=self.process_health_change)
        health_apply_btn.pack(side="left", padx=5)

        # Dice roll frame (between health and moves)
        dice_frame = tk.Frame(right_container)
        dice_frame.pack(side="top", fill="x", padx=5, pady=5)

        # Left dropdown for roll type
        tk.Label(dice_frame, text="Roll Type:").pack(side="left", padx=(0, 5))
        self.roll_type_var = tk.StringVar()
        self.roll_type_dropdown = ttk.Combobox(
            dice_frame,
            textvariable=self.roll_type_var,
            values=["Ability Check", "Skill Check", "Saving Throw"],
            state="readonly",
            width=12
        )
        self.roll_type_dropdown.pack(side="left", padx=5)
        self.roll_type_dropdown.bind(
            "<<ComboboxSelected>>", self.update_roll_options)

        # Right dropdown for specific roll
        tk.Label(dice_frame, text="Roll:").pack(side="left", padx=(10, 5))
        self.roll_option_var = tk.StringVar()
        self.roll_option_dropdown = ttk.Combobox(
            dice_frame,
            textvariable=self.roll_option_var,
            state="readonly",
            width=15
        )
        self.roll_option_dropdown.pack(side="left", padx=5)

        # Roll button
        roll_btn = tk.Button(dice_frame, text="🎲 Roll", command=self.make_roll)
        roll_btn.pack(side="left", padx=10)

        # Define skill-to-ability mapping
        self.skill_abilities = {
            'Athletics': 'str',
            'Acrobatics': 'dex',
            'Sleight of Hand': 'dex',
            'Stealth': 'dex',
            'Arcana': 'int',
            'History': 'int',
            'Investigation': 'int',
            'Nature': 'int',
            'Religion': 'int',
            'Animal Handling': 'wis',
            'Insight': 'wis',
            'Medicine': 'wis',
            'Perception': 'wis',
            'Survival': 'wis',
            'Deception': 'cha',
            'Intimidation': 'cha',
            'Performance': 'cha',
            'Persuasion': 'cha'
        }

        # Moves buttons frame below info panel
        moves_header_frame = tk.Frame(right_container)
        moves_header_frame.pack(side="top", fill="x", padx=5, pady=(5, 0))

        tk.Label(moves_header_frame, text="⚔️ Moves",
                 font=("Arial", 10, "bold")).pack(side="left")

        reset_pp_btn = tk.Button(moves_header_frame, text="🔄 Reset PP",
                                 command=lambda: self.reset_pp(self.selected_pokemon_id))
        reset_pp_btn.pack(side="left", padx=5)

        # Now create the actual moves button frame below header
        self.moves_frame = tk.Frame(right_container)
        self.moves_frame.pack(side="top", fill="x", padx=5, pady=5)
        self.move_buttons = []

        # Internal state
        self.pokemon_widgets = {}
        self.selected_pokemon_id = None
        self.next_id = 1  # counter for unique IDs
        self.default_bg = "#f0f0f0"
        self.selected_bg = "#cce5ff"

        # Drag and drop state
        self.drag_data = {"item": None, "y": 0}

        self.setup_mousewheel_scrolling()

    # ---------------- Drag and Drop Methods ----------------
    def on_drag_start(self, event, pokemon_id):
        """Start dragging a Pokemon container"""
        widget = event.widget
        # Find the container (might be clicking on a child widget)
        while widget and widget not in [w["container"] for w in self.pokemon_widgets.values()]:
            widget = widget.master

        if widget:
            self.drag_data["item"] = pokemon_id
            self.drag_data["y"] = event.y_root
            self.drag_data["start_y"] = event.y_root  # Track starting position
            self.drag_data["dragging"] = False  # Not dragging yet
            widget.config(cursor="hand2")  # Keep hand cursor initially

    def on_drag_motion(self, event, pokemon_id):
        """Handle dragging motion"""
        if self.drag_data["item"] is None:
            return

        # Check if we've moved enough to start dragging (threshold: 5 pixels)
        if not self.drag_data.get("dragging", False):
            distance = abs(
                event.y_root - self.drag_data.get("start_y", event.y_root))
            if distance < 5:
                return  # Not enough movement, don't start drag yet
            else:
                # Start dragging
                self.drag_data["dragging"] = True
                widget = self.pokemon_widgets[self.drag_data["item"]
                                              ]["container"]
                widget.config(cursor="fleur")

        # Get current y position
        current_y = event.y_root

        # Find all pokemon IDs in order
        pokemon_order = list(self.pokemon_widgets.keys())
        drag_index = pokemon_order.index(self.drag_data["item"])

        # Determine if we should swap
        for idx, pid in enumerate(pokemon_order):
            if pid == self.drag_data["item"]:
                continue

            container = self.pokemon_widgets[pid]["container"]
            container_y = container.winfo_rooty()
            container_height = container.winfo_height()

            # Check if dragged item is over this container
            if container_y <= current_y <= container_y + container_height:
                # Swap positions
                if idx < drag_index:
                    # Moving up
                    self.swap_pokemon_positions(
                        self.drag_data["item"], pid, "before")
                elif idx > drag_index:
                    # Moving down
                    self.swap_pokemon_positions(
                        self.drag_data["item"], pid, "after")
                break

    def on_drag_release(self, event, pokemon_id):
        """End dragging"""
        if self.drag_data["item"] is not None:
            widget = self.pokemon_widgets[self.drag_data["item"]]["container"]
            widget.config(cursor="hand2")

            # If we didn't actually drag (just clicked), select the Pokemon
            if not self.drag_data.get("dragging", False):
                self.select_pokemon(pokemon_id)

        self.drag_data = {"item": None, "y": 0,
                          "start_y": 0, "dragging": False}

    def swap_pokemon_positions(self, drag_id, target_id, position):
        """Swap the positions of two Pokemon in the sidebar"""
        # Get all widgets in current order
        all_widgets = list(self.pokemon_widgets.items())

        # Find indices
        drag_idx = next(i for i, (pid, _) in enumerate(
            all_widgets) if pid == drag_id)
        target_idx = next(i for i, (pid, _) in enumerate(
            all_widgets) if pid == target_id)

        # Don't swap if already in correct position
        if (position == "before" and drag_idx == target_idx - 1) or \
                (position == "after" and drag_idx == target_idx + 1):
            return

        # Unpack all containers
        for pid, widgets in all_widgets:
            widgets["container"].pack_forget()

        # Build new order
        new_order = []

        # Go through all items and build the correct order
        for i, (pid, widgets) in enumerate(all_widgets):
            if pid == drag_id:
                # Skip the dragged item, we'll add it in the right place
                continue

            if pid == target_id:
                # This is where we insert the dragged item
                if position == "before":
                    new_order.append((drag_id, self.pokemon_widgets[drag_id]))
                    new_order.append((pid, widgets))
                else:  # after
                    new_order.append((pid, widgets))
                    new_order.append((drag_id, self.pokemon_widgets[drag_id]))
            else:
                # Not the target or dragged item, just add normally
                new_order.append((pid, widgets))

        # Repack in new order
        for pid, widgets in new_order:
            widgets["container"].pack(pady=2, fill="x")

        # Update the internal dictionary order to match visual order
        self.pokemon_widgets = dict(new_order)

    # ---------------- Add Pokémon ----------------
    def add_pokemon(self, pokemon):
        pokemon_id = self.next_id
        self.next_id += 1

        # Make a deep copy so each instance is unique
        pokemon_instance = copy.deepcopy(pokemon)
        pokemon_instance["_id"] = pokemon_id

        container = tk.Frame(self.sidebar, relief="raised",
                             bd=2, bg=self.default_bg, cursor="hand2")
        container.pack(pady=2, fill="x")

        name_label = tk.Label(container, text=pokemon_instance["name"],
                              font=("Arial", 10, "bold"), bg=self.default_bg,
                              cursor="hand2")
        name_label.pack(anchor="w")

        img_label = None
        if pokemon_instance.get("image_url"):
            try:
                response = requests.get(pokemon_instance["image_url"])
                pil_img = Image.open(BytesIO(response.content))
                pil_img = pil_img.resize((80, 80), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(pil_img)
                img_label = tk.Label(container, image=tk_img, cursor="hand2",
                                     bg=self.default_bg)
                img_label.image = tk_img
                img_label.pack(pady=2)
                img_label.bind("<Button-1>",
                               lambda e, pid=pokemon_id: self.select_pokemon(pid))
            except:
                tk.Label(container, text="⚠️ Img error",
                         bg=self.default_bg).pack()

        trash_btn = tk.Button(container, text="🗑️", fg="red", borderwidth=0,
                              cursor="hand2", command=lambda pid=pokemon_id: self.confirm_remove(pid),
                              bg=self.default_bg)
        trash_btn.place_forget()

        # Bind drag events to container and children
        def bind_drag_events(widget):
            widget.bind("<ButtonPress-1>", lambda e,
                        pid=pokemon_id: self.on_drag_start(e, pid))
            widget.bind("<B1-Motion>", lambda e,
                        pid=pokemon_id: self.on_drag_motion(e, pid))
            widget.bind("<ButtonRelease-1>", lambda e,
                        pid=pokemon_id: self.on_drag_release(e, pid))
            for child in widget.winfo_children():
                if child != trash_btn:  # Don't bind to trash button
                    bind_drag_events(child)

        bind_drag_events(container)

        # Show/hide trash on hover
        def show_trash(e, offset_x=20, offset_y=-5):
            trash_btn.place(relx=1.0, rely=0.0, x=offset_x,
                            y=offset_y, anchor="ne")

        def hide_trash(e):
            trash_btn.place_forget()

        container.bind("<Enter>", show_trash)
        container.bind("<Leave>", hide_trash)
        for child in container.winfo_children():
            child.bind("<Enter>", show_trash)
            child.bind("<Leave>", hide_trash)

        self.pokemon_widgets[pokemon_id] = {
            "pokemon": pokemon_instance,
            "container": container,
            "name_label": name_label,
            "img_label": img_label,
            "trash_btn": trash_btn
        }

        self.select_pokemon(pokemon_id)
        # Bind mousewheel to the newly created container and its children
        self.bind_mousewheel_to_new_widgets(container)
        self.initialize_pokemon_health(pokemon_id)

    # ... rest of the methods remain the same ...

    def bind_mousewheel_to_new_widgets(self, widget):
        """Bind mousewheel to newly created widgets"""
        if hasattr(self, '_mousewheel_handler'):
            widget.bind("<MouseWheel>", self._mousewheel_handler)
            for child in widget.winfo_children():
                self.bind_mousewheel_to_new_widgets(child)

    # ---------------- Select Pokémon ----------------
    def select_pokemon(self, pokemon_id):
        if self.selected_pokemon_id:
            prev = self.pokemon_widgets.get(self.selected_pokemon_id)
            if prev:
                for widget_name in ("container", "name_label", "img_label", "trash_btn"):
                    w = prev.get(widget_name)
                    if w:
                        w.config(bg=self.default_bg)

        current = self.pokemon_widgets[pokemon_id]
        for widget_name in ("container", "name_label", "img_label", "trash_btn"):
            w = current.get(widget_name)
            if w:
                w.config(bg=self.selected_bg)

        self.selected_pokemon_id = pokemon_id
        self.info_panel.display_pokemon(current["pokemon"])
        self.display_moves(current["pokemon"], self.battle_log)

        if pokemon_id not in getattr(self, '_pokemon_health', {}):
            self.initialize_pokemon_health(pokemon_id)
        self.update_health_display()

    # ---------------- Display Moves ----------------

    def display_moves(self, pokemon, battle_log=None):
        for btn in getattr(self, "move_buttons", []):
            btn.destroy()
        self.move_buttons = []

        moves = pokemon.get("moves", [])
        if not moves:
            tk.Label(self.moves_frame, text="No moves available").pack()
            return

        # Use unique Pokémon instance ID
        if "_current_pp_instances" not in self.__dict__:
            self._current_pp_instances = {}  # store PP per _id

        pokemon_id = pokemon["_id"]
        if pokemon_id not in self._current_pp_instances:
            # Initialize PP for this instance
            self._current_pp_instances[pokemon_id] = {}
            for move_name in moves:
                move_id = move_name.lower().replace(" ", "-")
                move_data = MOVE_LOOKUP.get(move_id)
                self._current_pp_instances[pokemon_id][move_name] = move_data["pp"] if move_data else 0

        for move_name in moves:
            current_pp = self._current_pp_instances[pokemon_id][move_name]
            btn_text = f"{move_name} (PP: {current_pp})"
            btn = tk.Button(
                self.moves_frame,
                text=btn_text,
                width=20,
                command=lambda m=move_name, pid=pokemon_id: self.use_move_instance(
                    m, pid, battle_log)
            )
            if current_pp <= 0:
                btn.config(state="disabled")
            btn.pack(side="left", padx=2, pady=2)
            self.move_buttons.append(btn)

            # --- Tooltip with move info ---
            move_id = move_name.lower().replace(" ", "-")
            move_data = MOVE_LOOKUP.get(move_id)
            if move_data:
                # Build tooltip text with extra fields
                tooltip_parts = []
                tooltip_parts.append(
                    f"Type: {move_data.get('type', 'N/A').capitalize()}")

                power = move_data.get('power', 'N/A')
                if isinstance(power, list):
                    power = "/".join([p.upper() for p in power])
                tooltip_parts.append(f"Power: {power}")

                tooltip_parts.append(f"Time: {move_data.get('time', 'N/A')}")
                tooltip_parts.append(
                    f"Duration: {move_data.get('duration', 'N/A')}")
                tooltip_parts.append(f"Range: {move_data.get('range', 'N/A')}")

                # Add description text (skip tables)
                desc_text = "\n".join(str(d) for d in move_data.get(
                    "description", []) if isinstance(d, str))
                if "higherLevels" in move_data:
                    desc_text += f"\n\n{move_data['higherLevels']}"
                tooltip_parts.append("\n" + desc_text)

                full_tooltip = "\n".join(tooltip_parts)
                ToolTip(btn, full_tooltip)

    # ---------------- Remove Pokémon ----------------

    def confirm_remove(self, pokemon_id):
        pokemon = self.pokemon_widgets[pokemon_id]["pokemon"]
        result = tk.messagebox.askyesno(
            "Remove Pokémon",
            f"Are you sure you want to remove {pokemon['name']} from the battler?"
        )
        if result:
            self.remove_pokemon(pokemon_id)

    def remove_pokemon(self, pokemon_id):
        widgets = self.pokemon_widgets.pop(pokemon_id, None)
        if widgets:
            widgets["container"].destroy()
        if self.selected_pokemon_id == pokemon_id:
            self.selected_pokemon_id = None
            self.info_panel.display_pokemon({"name": "No Pokémon selected"})
            # Clear moves frame
            for btn in getattr(self, "move_buttons", []):
                btn.destroy()
            self.move_buttons = []

    # ---------------- Reset PP ----------------

    def reset_pp(self, pokemon_id):
        if pokemon_id not in self._current_pp_instances:
            return

        # Reset all moves to their original PP
        pokemon = self.pokemon_widgets[pokemon_id]["pokemon"]
        moves = pokemon.get("moves", [])
        for move_name in moves:
            move_id = move_name.lower().replace(" ", "-")
            move_data = MOVE_LOOKUP.get(move_id)
            if move_data:
                self._current_pp_instances[pokemon_id][move_name] = move_data["pp"]

        # Refresh move buttons and **pass the battle log**
        self.display_moves(pokemon, self.battle_log)

    def use_move_instance(self, move_name, pokemon_id, battle_log=None):
        pp_dict = self._current_pp_instances.get(pokemon_id)
        if not pp_dict or move_name not in pp_dict:
            return

        if pp_dict[move_name] > 0:
            pp_dict[move_name] -= 1
            # Update button
            for btn in self.move_buttons:
                if btn.cget("text").startswith(move_name):
                    btn.config(text=f"{move_name} (PP: {pp_dict[move_name]})")
                    if pp_dict[move_name] <= 0:
                        btn.config(state="disabled")
                    break

        pokemon = self.pokemon_widgets[pokemon_id]["pokemon"]
        move_id = move_name.lower().replace(" ", "-")

        try:
            attack_result, damage_result = attack_roll(
                pokemon, move_id)

            # Format in Roll20 style
            formatted_message = format_message(
                pokemon['name'], move_name, attack_result, damage_result
            )

        except Exception as e:
            formatted_message = f"{pokemon['name']} uses {move_name}!\n\nError: {str(e)}"

        if battle_log:
            battle_log.log(formatted_message)
        else:
            print(formatted_message)

    def initialize_pokemon_health(self, pokemon_id):
        """Initialize health tracking for a Pokemon"""
        if not hasattr(self, '_pokemon_health'):
            self._pokemon_health = {}

        pokemon = self.pokemon_widgets[pokemon_id]["pokemon"]
        max_hp = pokemon.get("hp", 100)
        self._pokemon_health[pokemon_id] = {
            "current": max_hp,
            "max": max_hp
        }

    def update_health_display(self):
        """Update the health display for the selected Pokemon"""
        if not self.selected_pokemon_id or not hasattr(self, '_pokemon_health'):
            self.health_label.config(text="HP: --/--")
            return

        health_data = self._pokemon_health.get(self.selected_pokemon_id)
        if health_data:
            current = health_data["current"]
            max_hp = health_data["max"]
            self.health_label.config(text=f"HP: {current}/{max_hp}")
        else:
            self.health_label.config(text="HP: --/--")

    def process_health_change(self, event=None):
        """Process health change input"""
        if not self.selected_pokemon_id or not hasattr(self, '_pokemon_health'):
            return

        input_text = self.health_entry.get().strip()
        if not input_text:
            return

        pokemon = self.pokemon_widgets[self.selected_pokemon_id]["pokemon"]
        pokemon_name = pokemon["name"]

        # Clear the entry
        self.health_entry.delete(0, tk.END)

        # Ensure health tracking is initialized
        if self.selected_pokemon_id not in self._pokemon_health:
            self.initialize_pokemon_health(self.selected_pokemon_id)

        health_data = self._pokemon_health[self.selected_pokemon_id]
        old_hp = health_data["current"]
        max_hp = health_data["max"]

        try:
            if input_text.startswith('='):
                # Set health to specific value
                new_hp = int(input_text[1:])
                health_data["current"] = max(0, min(new_hp, max_hp))
                change = health_data["current"] - old_hp

                if change != 0:
                    log_msg = f"{pokemon_name} HP set to {health_data['current']}/{max_hp}"
                    if change > 0:
                        log_msg += f" (+{change})"
                    else:
                        log_msg += f" ({change})"
                else:
                    log_msg = f"{pokemon_name} HP remains {health_data['current']}/{max_hp}"

            elif input_text.startswith('+'):
                # Add health
                heal_amount = int(input_text[1:])
                old_current = health_data["current"]
                health_data["current"] = min(
                    health_data["current"] + heal_amount, max_hp)
                actual_heal = health_data["current"] - old_current

                if actual_heal > 0:
                    log_msg = f"{pokemon_name} heals {actual_heal} HP ({old_current} → {health_data['current']}/{max_hp})"
                else:
                    log_msg = f"{pokemon_name} is already at full health ({health_data['current']}/{max_hp})"

            elif input_text.startswith('-'):
                # Subtract health
                damage_amount = int(input_text[1:])
                old_current = health_data["current"]
                health_data["current"] = max(
                    health_data["current"] - damage_amount, 0)
                actual_damage = old_current - health_data["current"]

                if actual_damage > 0:
                    log_msg = f"{pokemon_name} takes {actual_damage} damage ({old_current} → {health_data['current']}/{max_hp})"
                    if health_data["current"] == 0:
                        log_msg += " and is knocked out!"
                else:
                    log_msg = f"{pokemon_name} is already at 0 HP"

            else:
                # Try to parse as a direct number (treat as set value)
                new_hp = int(input_text)
                health_data["current"] = max(0, min(new_hp, max_hp))
                change = health_data["current"] - old_hp

                if change != 0:
                    log_msg = f"{pokemon_name} HP set to {health_data['current']}/{max_hp}"
                    if change > 0:
                        log_msg += f" (+{change})"
                    else:
                        log_msg += f" ({change})"
                else:
                    log_msg = f"{pokemon_name} HP remains {health_data['current']}/{max_hp}"

            # Update display and log
            self.update_health_display()
            if self.battle_log:
                self.battle_log.log(log_msg)

        except ValueError:
            if self.battle_log:
                self.battle_log.log(
                    f"Invalid HP input: '{input_text}'. Use +X, -X, or =X format.")

    def update_roll_options(self, event=None):
        """Update the right dropdown based on the selected roll type"""
        roll_type = self.roll_type_var.get()

        if roll_type == "Ability Check":
            options = ["Strength", "Dexterity", "Constitution",
                       "Intelligence", "Wisdom", "Charisma"]
        elif roll_type == "Skill Check":
            options = ["Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception",
                       "History", "Insight", "Intimidation", "Investigation", "Medicine",
                       "Nature", "Perception", "Performance", "Persuasion", "Religion",
                       "Sleight of Hand", "Stealth", "Survival"]
        elif roll_type == "Saving Throw":
            options = ["Strength", "Dexterity", "Constitution",
                       "Intelligence", "Wisdom", "Charisma"]
        else:
            options = []

        self.roll_option_dropdown.configure(values=options)
        self.roll_option_var.set("")  # Clear selection

    def make_roll(self):
        """Execute the selected dice roll"""
        if not self.selected_pokemon_id:
            if self.battle_log:
                self.battle_log.log("No Pokemon selected for rolling!")
            return

        roll_type = self.roll_type_var.get()
        roll_option = self.roll_option_var.get()

        if not roll_type or not roll_option:
            if self.battle_log:
                self.battle_log.log(
                    "Please select both roll type and specific roll!")
            return

        pokemon = self.pokemon_widgets[self.selected_pokemon_id]["pokemon"]
        pokemon_name = pokemon["name"]

        # Parse ability scores from the pokemon
        ability_scores = {}
        for line in pokemon["ability_scores"].split("\n"):
            parts = line.split(":")
            if len(parts) >= 2:
                ability_name = parts[0].strip().lower()
                # Extract the score (number before the parentheses)
                score_text = parts[1].strip()
                score_match = re.search(r"(\d+)", score_text)
                if score_match:
                    ability_scores[ability_name] = int(
                        score_match.group(1))

        # Determine which ability to use
        if roll_type in ["Ability Check", "Saving Throw"]:
            # str, dex, con, int, wis, cha
            ability_name = roll_option.lower()[:3]
        elif roll_type == "Skill Check":
            ability_name = self.skill_abilities.get(
                roll_option, 'wis').lower()[:3]

        # Get ability score and modifier
        ability_score = ability_scores.get(ability_name, 10)
        ability_modifier = (ability_score - 10) // 2

        # Check for proficiency
        proficiency_bonus = pokemon.get("proficiency_bonus", 0)
        is_proficient = False

        if roll_type == "Saving Throw":
            # Check if proficient in this saving throw
            saving_throws = pokemon.get("saving_throws", "").lower()
            is_proficient = ability_name in saving_throws
        elif roll_type == "Skill Check":
            # Check if proficient in this skill
            skills = pokemon.get("skills", "").lower()
            skill_check = roll_option.lower().replace(" ", "")
            is_proficient = skill_check in skills.replace(" ", "")

        # Roll the d20
        d20_roll = random.randint(1, 20)

        # Calculate total
        total = d20_roll + ability_modifier
        if is_proficient:
            total += proficiency_bonus

        # Format the result message
        ability_display = ability_name.upper()
        prof_text = f" + {proficiency_bonus} prof" if is_proficient else ""

        if d20_roll == 20:
            result_text = f"NATURAL 20!"
        elif d20_roll == 1:
            result_text = f"NATURAL 1!"
        else:
            result_text = ""

        # Create the log message
        log_message = f"{pokemon_name} makes a {roll_option} {roll_type.lower()}:\n"
        log_message += f"Result: {total} [d20: {d20_roll} + {ability_modifier} {ability_display}{prof_text}]"

        if result_text:
            log_message += f"\n{result_text}"

        if self.battle_log:
            self.battle_log.log(log_message)

    def setup_mousewheel_scrolling(self):
        def _on_mousewheel(event):
            # Get the widget under the mouse
            x, y = event.x_root, event.y_root
            widget_under_mouse = self.winfo_containing(x, y)

            # Only proceed if mouse is over a widget that belongs to this battler frame
            if not widget_under_mouse:
                return

            # Check if the widget is a child of this battler frame
            parent = widget_under_mouse
            is_over_battler = False
            while parent:
                if parent == self:
                    is_over_battler = True
                    break
                parent = parent.winfo_parent()
                if parent:
                    parent = self.nametowidget(parent)
                else:
                    break

            if not is_over_battler:
                return

            # Check if mouse is specifically over sidebar area
            sidebar_parent = widget_under_mouse
            is_over_sidebar = False
            while sidebar_parent:
                if sidebar_parent == self.sidebar_canvas or sidebar_parent == self.sidebar:
                    is_over_sidebar = True
                    break
                try:
                    sidebar_parent = sidebar_parent.winfo_parent()
                    if sidebar_parent:
                        sidebar_parent = self.nametowidget(sidebar_parent)
                    else:
                        break
                except:
                    break

            # Scroll the appropriate area
            if is_over_sidebar:
                self.sidebar_canvas.yview_scroll(
                    int(-1*(event.delta/120)), "units")
            elif hasattr(self.info_panel, 'canvas'):
                self.info_panel.canvas.yview_scroll(
                    int(-1*(event.delta/120)), "units")

        # Bind to the root window but with conditions
        self.winfo_toplevel().bind_all("<MouseWheel>", _on_mousewheel)
        self._mousewheel_handler = _on_mousewheel
# ---------------- Battle Logs ----------------


class BattleLogFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        log_frame = ttk.LabelFrame(self, text="📜 Battle Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_widget = scrolledtext.ScrolledText(
            log_frame, width=40, height=30, wrap="word", state="disabled"
        )
        self.log_widget.pack(fill="both", expand=True)

        # Configure tags for styling
        self.log_widget.tag_configure("separator", foreground="gray")
        self.first_log = True  # Track if this is the first log entry

    def log(self, message: str):
        self.log_widget.configure(state="normal")

        # Add separator line before message (except for first entry)
        if not self.first_log:
            separator = "─" * 30 + "\n"
            self.log_widget.insert("end", separator, "separator")
        else:
            self.first_log = False

        # Add the main message
        self.log_widget.insert("end", f"{message}\n\n")
        self.log_widget.see("end")  # auto-scroll
        self.log_widget.configure(state="disabled")


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_window or not self.text:
            return
        # Create tooltip window
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)

        label = tk.Label(tw, text=self.text, justify="left",
                         background="#ffffe0", relief="solid", borderwidth=1,
                         font=("Arial", 10), wraplength=300)
        label.pack(ipadx=5, ipady=2)

        # Get pointer position
        x = self.widget.winfo_pointerx() + 20
        y = self.widget.winfo_pointery() + 10

        # Get screen width/height
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()

        # Update geometry to avoid going off screen
        tw.update_idletasks()
        tip_width = tw.winfo_width()
        tip_height = tw.winfo_height()

        if x + tip_width > screen_width:
            x = screen_width - tip_width - 10  # 10px padding
        if y + tip_height > screen_height:
            y = screen_height - tip_height - 10

        tw.wm_geometry(f"+{x}+{y}")

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ---------------- Main ----------------

def main_gui():
    print("🎲 Welcome to Wilran! Pokémon Randomizer 🎲")
    areas = load_json(AREA_FILE)
    if not areas:
        return
    all_pokemon_data = load_json(POKEMON_FILE).get("items", [])
    if not all_pokemon_data:
        print("❌ No Pokémon data found in pokemon.json!")
        return

    root = tk.Tk()
    root.title("Wilran")
    root.geometry("1400x900")
    root.minsize(800, 500)

    # ---- Add style for selected Pokémon ----
    style = ttk.Style(root)
    style.configure("Selected.TFrame", background="#cce5ff")

    # ---- Create side-by-side wrapper ----
    wrapper = tk.Frame(root)
    wrapper.pack(fill="both", expand=True)

    # Left: Randomizer (fixed width)
    randomizer_frame = tk.Frame(wrapper, width=300)
    randomizer_frame.pack(side="left", fill="y", padx=5, pady=5)
    randomizer_frame.pack_propagate(False)

    # Center: Battler (expandable)
    battler_frame_container = tk.Frame(wrapper)
    battler_frame_container.pack(
        side="left", fill="both", expand=True, padx=5, pady=5)

    # Right: Battle Log (fixed width)
    log_frame_container = tk.Frame(wrapper, width=300)
    log_frame_container.pack(side="right", fill="y", padx=5, pady=5)
    log_frame_container.pack_propagate(False)

    # ---- Instantiate panels in correct order ----
    battle_log = BattleLogFrame(log_frame_container)
    battle_log.pack(fill="both", expand=True)

    # Pass all_pokemon_data here
    battler_panel = BattlerFrame(
        battler_frame_container, battle_log, all_pokemon_data)
    battler_panel.pack(fill="both", expand=True)

    app_panel = WilranApp(randomizer_frame, areas,
                          all_pokemon_data, battler_panel)
    app_panel.pack(fill="both", expand=True)

    # Example log messages
    battle_log.log("⚔️ Battle log ready!")
    battle_log.log(
        "Tip: Choose and area, randomize Pokemon, and add to tracker.")

    root.mainloop()


if __name__ == "__main__":
    main_gui()
