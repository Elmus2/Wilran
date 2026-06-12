"""
mechanics/pokemon.py
Pokémon instance generation: nature rolling, ASI application,
held-item selection, and the main pick_random_pokemon() factory.
"""

import random

from config import (
    NATURES, ASI_BREAKPOINTS, HIT_DICE_BONUS,
    MAX_MOVES, MAX_STAT_VALUE, SHINY_ODDS, HELD_ITEM_CHANCE, LEVEL_KEYS,
)
from data_loader import ABILITY_LOOKUP, load_held_items
from mechanics.dice import ability_modifier, proficiency_bonus
from mechanics.types import PokemonType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_speed_senses(lst: list) -> str:
    """Format a list of speed/sense dicts as a readable string."""
    parts = []
    for item in lst:
        if isinstance(item, dict):
            parts.append(f"{item['type'].capitalize()} {item['value']}ft")
        else:
            parts.append(str(item))
    return ", ".join(parts)


def _ability_text(ability_id: str) -> str:
    info = ABILITY_LOOKUP.get(ability_id)
    if info:
        return f"Ability: {info['name']} - {info['description']}\n"
    return ability_id


def format_ability_scores(attrs: dict) -> str:
    """Format an attribute dict into the multi-line ability scores string."""
    return "\n".join(
        f"{k.upper()}: {v} ({'+' if (mod := ability_modifier(v)) >= 0 else ''}{mod})"
        for k, v in attrs.items()
    )


def calculate_hp(full_pokemon: dict, attrs: dict, level: int) -> int:
    """Calculate total HP for a Pokémon at the given level and attributes."""
    base_hp   = full_pokemon["hp"]
    hit_dice  = full_pokemon["hitDice"]
    min_level = full_pokemon.get("minLevel", 1)
    con_mod   = ability_modifier(attrs["con"])
    extra_hp  = max(0, level - min_level) * (HIT_DICE_BONUS[hit_dice] + con_mod)
    return base_hp + extra_hp


def asi_per_breakpoint(full_pokemon: dict) -> int:
    """Return the number of ASI points granted per breakpoint for this species."""
    evo = full_pokemon.get("evolution")
    max_stage = int(evo["maxStage"]) if evo and "maxStage" in evo else 1
    return 4 if max_stage == 1 else 3 if max_stage == 2 else 2


def get_grouped_moves(full_pokemon: dict, level: int) -> dict:
    """
    Return moves grouped by category for the leveler dropdown.
    Keys: 'start', 'level' (dict of level→list), 'egg', 'tm'
    Each move is a display-formatted string.
    TM numbers are resolved to "TM01 - Work Up" style names via TM_LOOKUP.
    If a TM number has no entry in TM_LOOKUP it falls back to "TM{n}".
    """
    from data_loader import TM_LOOKUP

    moves_data = full_pokemon.get("moves", {})

    start = [m.replace("-", " ").title() for m in moves_data.get("start", [])]

    level_groups = {}
    for key, min_lvl in LEVEL_KEYS:
        moves = moves_data.get(key, [])
        if moves:
            level_groups[min_lvl] = [m.replace("-", " ").title() for m in moves]

    egg = [m.replace("-", " ").title() for m in moves_data.get("egg", [])]

    tm = []
    for n in moves_data.get("tm", []):
        tm_entry = TM_LOOKUP.get(int(n))
        if tm_entry:
            tm.append(tm_entry["display"])
        else:
            tm.append(f"TM{int(n):02d}")

    return {
        "start":         start,
        "level":         level_groups,
        "egg":           egg,
        "tm":            tm,
        "current_level": level,
    }


def get_available_moves(full_pokemon: dict, level: int) -> list[str]:
    """
    Return all moves available at the given level as a flat list.
    Used by the wild tab. TM numbers resolved to display names.
    Order: start → level moves → egg moves → TMs.
    """
    from data_loader import TM_LOOKUP

    moves_data  = full_pokemon.get("moves", {})
    start_moves = list(moves_data.get("start", []))

    level_moves = []
    for key, min_lvl in LEVEL_KEYS:
        if level >= min_lvl:
            level_moves.extend(moves_data.get(key, []))

    egg_moves = moves_data.get("egg", [])

    tm_moves = []
    for n in moves_data.get("tm", []):
        tm_entry = TM_LOOKUP.get(int(n))
        tm_moves.append(tm_entry["display"] if tm_entry else f"TM{int(n):02d}")

    all_moves = start_moves + level_moves + egg_moves + tm_moves

    # Deduplicate while preserving order
    seen, unique = set(), []
    for m in all_moves:
        if m not in seen:
            seen.add(m)
            unique.append(m)

    return [m.replace("-", " ").title() for m in unique]


# ---------------------------------------------------------------------------
# Nature
# ---------------------------------------------------------------------------

def roll_nature(attributes: dict) -> tuple[str, dict, str]:
    """
    Roll a random nature and apply its stat modifiers.
    Returns (nature_name, modified_attributes, display_text).
    """
    nature = random.choice(NATURES)
    return apply_nature(nature["name"], attributes)


def apply_nature(nature_name: str, attributes: dict) -> tuple[str, dict, str]:
    """
    Apply a named nature to attributes.
    Returns (nature_name, modified_attributes, display_text).
    """
    nature   = next(n for n in NATURES if n["name"] == nature_name)
    modified = attributes.copy()
    incr_text = decr_text = ""

    if nature["increase"]:
        modified[nature["increase"]] += 1
        incr_text = f"+1 {nature['increase'].capitalize()}"
    if nature["decrease"]:
        modified[nature["decrease"]] -= 1
        decr_text = f"-1 {nature['decrease'].capitalize()}"

    if incr_text or decr_text:
        sep = ", " if incr_text and decr_text else ""
        display = f"{nature['name']} ({incr_text}{sep}{decr_text})"
    else:
        display = nature["name"]

    return nature["name"], modified, display


# ---------------------------------------------------------------------------
# ASI
# ---------------------------------------------------------------------------

def apply_asi(full_pokemon: dict, attributes: dict, level: int) -> dict:
    """
    Randomly distribute Ability Score Increases for the given level.
    Used by the randomizer and wild tab.
    """
    modified  = attributes.copy()
    per_bp    = asi_per_breakpoint(full_pokemon)
    min_level = full_pokemon.get("minLevel", 1)
    valid_bps = [bp for bp in ASI_BREAKPOINTS if min_level < bp <= level]
    total_asi = per_bp * len(valid_bps)

    stats = list(modified.keys())
    for _ in range(total_asi):
        uncapped = [s for s in stats if modified[s] < MAX_STAT_VALUE]
        if not uncapped:
            break
        modified[random.choice(uncapped)] += 1

    return modified


# ---------------------------------------------------------------------------
# Ability selection
# ---------------------------------------------------------------------------

def select_ability(full_pokemon: dict) -> str:
    """Return formatted ability text (normal + hidden) for display."""
    abilities_data = full_pokemon.get("abilities", [])
    normal = [a["id"] for a in abilities_data if not a.get("hidden")]
    hidden = [a["id"] for a in abilities_data if a.get("hidden")]

    chosen = random.choice(normal) if normal else "None"
    text = _ability_text(chosen)

    if hidden:
        text += "\nHidden " + "\n".join(_ability_text(h) for h in hidden)

    return text


def build_ability_text(ability_id: str, full_pokemon: dict) -> str:
    """
    Build the abilities display text for a specific chosen ability,
    always including the hidden ability if the species has one.
    """
    abilities_data = full_pokemon.get("abilities", [])
    hidden = [a["id"] for a in abilities_data if a.get("hidden")]

    text = _ability_text(ability_id)
    if hidden:
        text += "\nHidden " + "\n".join(_ability_text(h) for h in hidden)
    return text


# ---------------------------------------------------------------------------
# Gender
# ---------------------------------------------------------------------------

def roll_gender(gender_info: str) -> str:
    if not gender_info or gender_info.lower() == "genderless" or gender_info == "0:0":
        return "Genderless"
    if ":" in gender_info:
        female, male = map(int, gender_info.split(":"))
        total = female + male
        if total == 0:
            return "Genderless"
        return random.choices(["Female", "Male"], weights=[female, male], k=1)[0]
    return "Unknown"


def get_gender_options(gender_info: str) -> list[str]:
    """Return the valid gender choices for a species."""
    if not gender_info or gender_info.lower() == "genderless" or gender_info == "0:0":
        return ["Genderless"]
    if ":" in gender_info:
        female, male = map(int, gender_info.split(":"))
        if female == 0:
            return ["Male"]
        if male == 0:
            return ["Female"]
        return ["Male", "Female"]
    return ["Male", "Female"]


# ---------------------------------------------------------------------------
# Leveler factory
# ---------------------------------------------------------------------------

def generate_leveler_pokemon(
    full_pokemon: dict,
    nature_name: str,
    ability_id: str,
    gender: str,
    moves: list[str],
) -> dict:
    """
    Build a Pokémon instance from explicit user choices at minLevel.
    Nature, ability, gender, and moves are all provided rather than random.
    Returns the same flat dict format used everywhere else.
    """
    level     = full_pokemon.get("minLevel", 1)
    prof      = proficiency_bonus(level)
    is_shiny  = False   # shiny added later

    types_list = full_pokemon.get("type", [])
    types_text = "/".join(t.capitalize() for t in types_list) or "Unknown"
    poke_type  = PokemonType(types_list)

    # Apply nature to base attributes — no ASI at minLevel
    base_attrs = full_pokemon.get("attributes", {}).copy()
    _, final_attrs, nature_text = apply_nature(nature_name, base_attrs)

    skills_list = full_pokemon.get("skills", [])
    saves_list  = full_pokemon.get("savingThrows", [])

    return {
        "name":             full_pokemon["name"].upper(),
        "shiny":            is_shiny,
        "level":            level,
        "sr":               full_pokemon.get("sr", 0),
        "proficiency_bonus": prof,
        "gender":           gender,
        "types":            types_text,
        "size":             full_pokemon.get("size", "Unknown").capitalize(),
        "nature":           nature_text,
        "ac":               full_pokemon.get("ac", "Unknown"),
        "hp":               calculate_hp(full_pokemon, final_attrs, level),
        "speed":            _format_speed_senses(full_pokemon.get("speed", [])),
        "senses":           _format_speed_senses(full_pokemon.get("senses", [])),
        "ability_scores":   format_ability_scores(final_attrs),
        "skills":           ", ".join(s.capitalize() for s in skills_list) or "None",
        "saving_throws":    ", ".join(s.upper() for s in saves_list) or "None",
        "vulnerabilities":  poke_type.vulnerabilities(),
        "resistances":      poke_type.resistances(),
        "immunities":       poke_type.immunities(),
        "moves":            moves,
        "abilities":        build_ability_text(ability_id, full_pokemon),
        "held_item":        "None",
        "image_url":        full_pokemon.get("media", {}).get("main", ""),
        # Leveler-specific fields — used by LevelerTab to track state
        "_full_pokemon":    full_pokemon,
        "_nature_name":     nature_name,
        "_ability_id":      ability_id,
        "_base_attrs":      base_attrs,   # untouched original stats
        "_attrs":           final_attrs,  # nature + any ASI applied
        "_pending_asi":     0,
    }


def change_nature(pokemon: dict, new_nature_name: str) -> dict:
    """
    Reapply a different nature to a leveler Pokémon.
    Starts from _base_attrs, reapplies the new nature, then reapplies
    any ASI points that were manually assigned above the base values.
    """
    updated      = pokemon.copy()
    base_attrs   = pokemon["_base_attrs"]
    old_attrs    = pokemon["_attrs"]
    full_pokemon = pokemon["_full_pokemon"]

    # Reapply new nature to base
    _, nature_attrs, nature_text = apply_nature(new_nature_name, base_attrs)

    # Carry over any ASI gains (difference between old attrs and old nature attrs)
    # We do this by finding how much each stat was manually raised above the
    # nature-modified base, and applying those same increases to the new base.
    _, old_nature_attrs, _ = apply_nature(pokemon["_nature_name"], base_attrs)
    for stat in base_attrs:
        asi_gained = old_attrs.get(stat, 0) - old_nature_attrs.get(stat, 0)
        if asi_gained > 0:
            nature_attrs[stat] = nature_attrs.get(stat, 0) + asi_gained

    updated["_nature_name"]   = new_nature_name
    updated["_attrs"]         = nature_attrs
    updated["nature"]         = nature_text
    updated["ability_scores"] = format_ability_scores(nature_attrs)
    updated["hp"]             = calculate_hp(full_pokemon, nature_attrs, pokemon["level"])
    return updated


def change_gender(pokemon: dict, new_gender: str) -> dict:
    """Update a leveler Pokémon's gender."""
    updated = pokemon.copy()
    updated["gender"] = new_gender
    return updated


def level_up_pokemon(pokemon: dict) -> dict:
    """
    Increment a leveler Pokémon by one level.
    Returns an updated copy of the pokemon dict.
    If the new level is an ASI breakpoint, _pending_asi is incremented
    by the species' ASI-per-breakpoint value so the UI can prompt the user.
    """
    updated       = pokemon.copy()
    full_pokemon  = pokemon["_full_pokemon"]
    new_level     = pokemon["level"] + 1
    prof          = proficiency_bonus(new_level)
    per_bp        = asi_per_breakpoint(full_pokemon)
    min_level     = full_pokemon.get("minLevel", 1)

    # Check if this level is an ASI breakpoint
    pending = pokemon.get("_pending_asi", 0)
    if new_level in ASI_BREAKPOINTS and new_level > min_level:
        pending += per_bp

    # Recalculate HP at new level with current attrs.
    # If the pokemon evolved this level, HP was already calculated in
    # evolve_pokemon (including the hit dice gain), so we skip it here.
    attrs = pokemon["_attrs"]

    updated["level"]             = new_level
    updated["proficiency_bonus"] = prof
    updated["_pending_asi"]      = pending

    if pokemon.get("_evolved_this_level"):
        updated["hp"]                  = pokemon["hp"]
        updated["_evolved_this_level"] = False   # clear the flag
    else:
        updated["hp"] = calculate_hp(full_pokemon, attrs, new_level)

    return updated


def apply_asi_point(pokemon: dict, stat: str) -> dict:
    """
    Apply one ASI point to the chosen stat.
    Decrements _pending_asi by 1 and recalculates HP and ability scores.
    """
    updated  = pokemon.copy()
    attrs    = pokemon["_attrs"].copy()
    attrs[stat] += 1

    full_pokemon = pokemon["_full_pokemon"]

    updated["_attrs"]          = attrs
    updated["_pending_asi"]    = max(0, pokemon.get("_pending_asi", 0) - 1)
    updated["ability_scores"]  = format_ability_scores(attrs)
    updated["hp"]              = calculate_hp(full_pokemon, attrs, pokemon["level"])
    return updated


# ---------------------------------------------------------------------------
# Move selection
# ---------------------------------------------------------------------------

def select_moves(full_pokemon: dict, level: int) -> list[str]:
    """Return up to MAX_MOVES randomly selected moves available at this level."""
    moves_data = full_pokemon.get("moves", {})
    available = list(moves_data.get("start", []))
    for key, min_lvl in LEVEL_KEYS:
        if level >= min_lvl:
            available.extend(moves_data.get(key, []))

    chosen = random.sample(available, min(MAX_MOVES, len(available))) if available else []
    return [m.replace("-", " ").title() for m in chosen]


# ---------------------------------------------------------------------------
# Main factory
# ---------------------------------------------------------------------------

def pick_random_pokemon(area: dict, all_pokemon_data: list[dict]) -> dict | None:
    """
    Pick and fully generate a random wild Pokémon for the given area.
    Returns a flat dict suitable for display and combat.
    """
    if not area.get("pokemon"):
        print("❌ This area has no Pokémon!")
        return None

    entry        = random.choice(area["pokemon"])
    level        = random.randint(entry["min_level"], entry["max_level"])
    full_pokemon = next(
        (pk for pk in all_pokemon_data if pk["name"].lower() == entry["name"].lower()),
        None,
    )

    is_shiny     = random.randint(1, SHINY_ODDS) == 1
    display_name = entry["name"].upper()
    prof         = proficiency_bonus(level)

    # Early return if we have no data for this Pokémon
    if not full_pokemon:
        return {
            "name": display_name, "shiny": is_shiny, "level": level,
            "sr": 0, "proficiency_bonus": prof,
            "gender": "Unknown", "types": "Unknown", "size": "Unknown",
            "nature": "Unknown", "ac": "Unknown", "hp": "Unknown",
            "speed": "", "senses": "", "ability_scores": "",
            "skills": "None", "saving_throws": "None",
            "vulnerabilities": [], "resistances": [], "immunities": [],
            "moves": [], "abilities": "", "held_item": "None", "image_url": "",
        }

    # Image
    media     = full_pokemon.get("media", {})
    image_url = media.get("mainShiny" if is_shiny else "main", "")

    # Held item (25% chance)
    if random.randint(1, HELD_ITEM_CHANCE) == 1:
        items     = load_held_items()
        held_item = random.choice(items) if items else "None"
    else:
        held_item = "None"

    # Types
    types_list = full_pokemon.get("type", [])
    types_text = "/".join(t.capitalize() for t in types_list) or "Unknown"
    poke_type  = PokemonType(types_list)

    # Ability scores → nature → ASI
    base_attrs  = full_pokemon.get("attributes", {}).copy()
    _, nature_attrs, nature_text = roll_nature(base_attrs)
    final_attrs = apply_asi(full_pokemon, nature_attrs, level)

    # Skills and saving throws
    skills_list = full_pokemon.get("skills", [])
    saves_list  = full_pokemon.get("savingThrows", [])

    return {
        "name":              display_name,
        "shiny":             is_shiny,
        "level":             level,
        "sr":                full_pokemon.get("sr", 0),
        "proficiency_bonus": prof,
        "gender":            roll_gender(full_pokemon.get("gender", "")),
        "types":             types_text,
        "size":              full_pokemon.get("size", "Unknown").capitalize(),
        "nature":            nature_text,
        "ac":                full_pokemon.get("ac", "Unknown"),
        "hp":                calculate_hp(full_pokemon, final_attrs, level),
        "speed":             _format_speed_senses(full_pokemon.get("speed", [])),
        "senses":            _format_speed_senses(full_pokemon.get("senses", [])),
        "ability_scores":    format_ability_scores(final_attrs),
        "skills":            ", ".join(s.capitalize() for s in skills_list) or "None",
        "saving_throws":     ", ".join(s.upper() for s in saves_list) or "None",
        "vulnerabilities":   poke_type.vulnerabilities(),
        "resistances":       poke_type.resistances(),
        "immunities":        poke_type.immunities(),
        "moves":             select_moves(full_pokemon, level),
        "abilities":         select_ability(full_pokemon),
        "held_item":         held_item,
        "image_url":         image_url,
    }


# ---------------------------------------------------------------------------
# Evolution
# ---------------------------------------------------------------------------

def get_evolution_options(full_pokemon: dict, level: int) -> list[dict]:
    """
    Return a list of evolution options available at the given level.
    Only returns level-based evolutions whose condition is met.
    Each entry is the raw 'to' dict from the JSON.
    """
    evo = full_pokemon.get("evolution", {})
    options = []
    for target in evo.get("to", []):
        for condition in target.get("conditions", []):
            if condition.get("type") == "level" and level >= condition.get("value", 999):
                options.append(target)
                break
    return options


def evolve_pokemon(
    pokemon: dict,
    evolution_target: dict,
    all_pokemon_data: list[dict],
    new_ability_id: str | None = None,
    new_level: int | None = None,
) -> dict:
    """
    Apply evolution rules to a leveler Pokémon.

    Rules applied:
    - Name, image, AC, types, size, speed, senses, skills, saving throws
      all update to the new form
    - HP = current HP + (level * 2), then switches to new form's hit dice
    - Ability scores kept as-is; evolution ASI bonus added to _pending_asi
    - If current ability not on new form, new_ability_id must be provided
    - Moves kept as currently selected; move list updates to new form
    - _full_pokemon, _base_attrs update to new form
    - _nature_name preserved
    """
    new_name = evolution_target["id"]
    new_full  = next(
        (p for p in all_pokemon_data if p["name"].lower() == new_name.lower()),
        None,
    )
    if not new_full:
        raise ValueError(f"Evolution target '{new_name}' not found in pokemon data.")

    updated      = pokemon.copy()
    level        = new_level if new_level is not None else pokemon["level"]
    attrs        = pokemon["_attrs"].copy()
    nature_name  = pokemon.get("_nature_name", "Hardy")

    # --- Types, size, AC, speed, senses, skills, saving throws ---
    types_list = new_full.get("type", [])
    types_text = "/".join(t.capitalize() for t in types_list) or "Unknown"
    poke_type  = PokemonType(types_list)

    updated["name"]           = new_full["name"].upper()
    updated["types"]          = types_text
    updated["size"]           = new_full.get("size", "Unknown").capitalize()
    updated["ac"]             = new_full.get("ac", "Unknown")
    updated["speed"]          = _format_speed_senses(new_full.get("speed", []))
    updated["senses"]         = _format_speed_senses(new_full.get("senses", []))
    updated["vulnerabilities"] = poke_type.vulnerabilities()
    updated["resistances"]    = poke_type.resistances()
    updated["immunities"]     = poke_type.immunities()

    skills_list = new_full.get("skills", [])
    saves_list  = new_full.get("savingThrows", [])
    updated["skills"]         = ", ".join(s.capitalize() for s in skills_list) or "None"
    updated["saving_throws"]  = ", ".join(s.upper() for s in saves_list) or "None"

    # --- HP: current HP + (level * 2) + new hit dice bonus ---
    # The level * 2 is the evolution bonus.
    # The hit dice gain is one level's worth using the NEW form's hit dice,
    # since level_up_pokemon will skip HP addition for this level.
    new_hit_dice = new_full.get("hitDice", "d6")
    con_mod      = ability_modifier(attrs.get("con", 10))
    evolved_hp   = pokemon["hp"] + (level * 2) + HIT_DICE_BONUS[new_hit_dice] + con_mod
    updated["hp"]                = evolved_hp
    updated["_evolved_this_level"] = True   # tells level_up_pokemon to skip HP this level

    # --- Ability scores: kept as-is ---
    updated["ability_scores"] = format_ability_scores(attrs)
    updated["_attrs"]         = attrs

    # Recalculate _base_attrs for the new form by reversing nature from new base
    new_base_attrs = new_full.get("attributes", {}).copy()
    _, new_nature_attrs, _ = apply_nature(nature_name, new_base_attrs)
    # Carry over any manual ASI gains from old form
    old_base = pokemon.get("_base_attrs", {})
    _, old_nature_attrs, _ = apply_nature(nature_name, old_base)
    for stat in old_base:
        asi_gained = attrs.get(stat, 0) - old_nature_attrs.get(stat, 0)
        if asi_gained > 0:
            new_nature_attrs[stat] = new_nature_attrs.get(stat, 0) + asi_gained
    updated["_base_attrs"]    = new_base_attrs
    updated["_attrs"]         = new_nature_attrs
    updated["ability_scores"] = format_ability_scores(new_nature_attrs)

    # --- Evolution ASI bonus ---
    evo_asi = 0
    for effect in evolution_target.get("effects", []):
        if effect.get("type") == "asi":
            evo_asi = int(effect.get("value", 0))
            break
    updated["_pending_asi"] = pokemon.get("_pending_asi", 0) + evo_asi

    # --- Ability: keep if still available, otherwise use provided ---
    current_ability_id = pokemon.get("_ability_id", "")
    new_abilities_data = new_full.get("abilities", [])
    new_normal_ids     = [a["id"] for a in new_abilities_data if not a.get("hidden")]
    new_hidden_ids     = [a["id"] for a in new_abilities_data if a.get("hidden")]

    if current_ability_id in new_normal_ids:
        chosen_ability = current_ability_id
    else:
        # Must swap — use provided choice or fall back to first available
        chosen_ability = new_ability_id or (new_normal_ids[0] if new_normal_ids else "none")

    updated["_ability_id"] = chosen_ability
    updated["abilities"]   = build_ability_text(chosen_ability, new_full)

    # --- Image ---
    media = new_full.get("media", {})
    updated["image_url"] = media.get(
        "mainShiny" if pokemon.get("shiny") else "main", ""
    )

    # --- Update internal full_pokemon reference ---
    updated["_full_pokemon"] = new_full
    updated["sr"]            = new_full.get("sr", 0)
    updated["nature"]        = pokemon.get("nature", "")

    return updated


def needs_ability_swap(pokemon: dict, evolution_target: dict, all_pokemon_data: list) -> bool:
    """Return True if the current ability won't carry over to the evolved form."""
    new_name    = evolution_target["id"]
    new_full    = next(
        (p for p in all_pokemon_data if p["name"].lower() == new_name.lower()),
        None,
    )
    if not new_full:
        return False
    current_id  = pokemon.get("_ability_id", "")
    new_normal  = [a["id"] for a in new_full.get("abilities", []) if not a.get("hidden")]
    return current_id not in new_normal


def get_new_form_abilities(evolution_target: dict, all_pokemon_data: list) -> list[dict]:
    """Return the normal abilities of the evolved form as a list of {id, name} dicts."""
    new_name = evolution_target["id"]
    new_full = next(
        (p for p in all_pokemon_data if p["name"].lower() == new_name.lower()),
        None,
    )
    if not new_full:
        return []
    from data_loader import ABILITY_LOOKUP
    result = []
    for a in new_full.get("abilities", []):
        if not a.get("hidden"):
            info = ABILITY_LOOKUP.get(a["id"])
            result.append({
                "id":   a["id"],
                "name": info["name"] if info else a["id"],
            })
    return result
