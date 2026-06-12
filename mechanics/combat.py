"""
mechanics/combat.py
All combat logic: parsing move descriptions, calculating damage,
resolving attack rolls, and formatting battle-log messages.

Key improvement over the original:
  - AttackResult dataclass replaces parallel string-returning functions,
    eliminating the need for format_message() to re-parse with regex.
  - _build_damage_breakdown() replaces 3 near-identical copy-pasted blocks.
  - _detect_save_type() replaces a manual if/elif chain with a dict lookup.
"""

import re
import random
from dataclasses import dataclass, field

from config import SAVE_ABBREV
from data_loader import MOVE_LOOKUP
from mechanics.dice import roll_dice, ability_modifier


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DamageResult:
    total:      int
    dice_str:   str
    base_roll:  int
    crit_roll:  int        # 0 if not a crit
    ability_mod: int
    ability_name: str      # e.g. "STR"
    stab_bonus: int
    damage_type: str
    is_crit:    bool
    has_move_modifier: bool  # True → ability mod is added to damage
    context:    str          # "on hit" or "on failed save"

    @property
    def breakdown(self) -> str:
        """Human-readable breakdown string for the battle log."""
        parts = []
        if self.is_crit:
            parts.append(f"{self.dice_str}: {self.base_roll}")
            parts.append(f"{self.dice_str}: {self.crit_roll}")
        else:
            parts.append(f"{self.dice_str}: {self.base_roll}")
        if self.has_move_modifier:
            parts.append(f"{self.ability_mod} {self.ability_name}")
        if self.stab_bonus:
            parts.append(f"{self.stab_bonus} STAB")
        return " + ".join(parts)


@dataclass
class AttackResult:
    pokemon_name: str
    move_name:    str

    # Attack roll (None for save-only moves)
    attack_total:   int | None = None
    d20_roll:       int | None = None
    ability_mod:    int = 0
    ability_name:   str = "N/A"
    prof:           int = 0
    is_crit:        bool = False
    is_crit_fail:   bool = False

    # Saving throw (None for attack-only moves)
    save_dc:   int | None = None
    save_type: str | None = None

    # Damage (None for status moves)
    damage: DamageResult | None = None

    # Fallback text for moves with no parseable mechanic
    fallback_text: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _description_text(move_data: dict) -> str:
    """Concatenate all string entries in a move's description list."""
    return " ".join(
        d.lower() for d in move_data.get("description", []) if isinstance(d, str)
    )


def _has_move_modifier(description: str) -> bool:
    return bool(re.search(r'\+?\s*MOVE\s+\w+\s+damage', description, re.IGNORECASE))


def _detect_save_type(description: str) -> str | None:
    """Return the canonical save abbreviation (e.g. 'DEX') or None."""
    pattern = r'\b(str|strength|dex|dexterity|con|constitution|int|intelligence|wis|wisdom|cha|charisma)\s+save'
    match = re.search(pattern, description, re.IGNORECASE)
    if match:
        return SAVE_ABBREV.get(match.group(1).lower())
    return None


def _parse_damage_dice(description: str) -> tuple[str | None, str | None]:
    """
    Return (dice_str, damage_type) from a move description.
    Tries MOVE-modifier patterns first, then flat-damage patterns.
    Returns (None, None) if no damage is found.
    """
    move_modifier_patterns = [
        r'(\d+d\d+(?:\s*\+\s*\d+)?)\s*\+?\s*MOVE\s+(\w+)\s+damage',
        r'takes\s+(\d+d\d+(?:\s*\+\s*\d+)?)\s*\+?\s*MOVE\s+(\w+)\s+damage',
        r'deals?\s+(\d+d\d+(?:\s*\+\s*\d+)?)\s*\+?\s*MOVE\s+(\w+)\s+damage',
    ]
    flat_damage_patterns = [
        r'doing\s+(\d+d\d+)\s+(\w+)\s+damage',
        r'takes\s+(\d+d\d+)\s+(\w+)\s+damage',
        r'deals?\s+(\d+d\d+)\s+(\w+)\s+damage',
        r'(\d+d\d+)\s+(\w+)\s+damage',
    ]

    for pattern in move_modifier_patterns + flat_damage_patterns:
        m = re.search(pattern, description, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip().lower()
    return None, None


def _scaled_dice(move_data: dict, pokemon_level: int) -> str | None:
    """Return the best applicable scaled damage dice string, or None."""
    higher = move_data.get("higherLevels", "")
    if not higher:
        return None

    scalings = [
        (int(lvl), dice)
        for dice, lvl in re.findall(r'(\d+d\d+) at level (\d+)', higher)
    ]
    for level_req, dice in sorted(scalings, reverse=True):
        if pokemon_level >= level_req:
            return dice
    return None


def _parse_ability_scores(pokemon: dict) -> dict[str, int]:
    """Parse the ability_scores text block into a {abbrev: score} dict."""
    scores = {}
    for line in pokemon.get("ability_scores", "").split("\n"):
        parts = line.split(":")
        if len(parts) >= 2:
            key = parts[0].strip().lower()
            m = re.search(r"\d+", parts[1])
            scores[key] = int(m.group()) if m else 10
    return scores


def _best_ability_mod(
    power_abilities: list[str] | str | None,
    ability_scores: dict[str, int],
) -> tuple[int, str | None]:
    """
    Return (highest_modifier, chosen_ability_abbrev).
    Returns (0, None) for status moves.
    """
    if not isinstance(power_abilities, list) or not power_abilities:
        return 0, None

    best_mod = float("-inf")
    chosen = None
    for ability in power_abilities:
        score = ability_scores.get(ability, 10)
        mod = ability_modifier(score)
        if mod > best_mod:
            best_mod = mod
            chosen = ability

    return (best_mod if best_mod != float("-inf") else 0), chosen


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_damage(
    pokemon: dict,
    move_data: dict,
    ability_mod: int = 0,
    ability_name: str = "N/A",
    is_crit: bool = False,
    prof: int = 0,
    context: str = "on hit",
) -> DamageResult | None:
    """
    Calculate damage for a move.
    Returns a DamageResult, or None if the move has no parseable damage.
    """
    description = _description_text(move_data)
    uses_move_mod = _has_move_modifier(description)

    base_dice_str, damage_type = _parse_damage_dice(description)
    if not base_dice_str:
        return None

    dice_str = _scaled_dice(move_data, pokemon.get("level", 1)) or base_dice_str

    base_roll = roll_dice(dice_str)
    crit_roll = roll_dice(dice_str) if is_crit else 0
    total_dice = base_roll + crit_roll

    # STAB — applies regardless of move modifier
    move_type = move_data.get("type", "").lower()
    pokemon_types = [t.strip() for t in pokemon.get("types", "").lower().split("/")]
    stab_bonus = prof if move_type in pokemon_types else 0

    total = total_dice + stab_bonus
    if uses_move_mod:
        total += ability_mod

    return DamageResult(
        total=total,
        dice_str=dice_str,
        base_roll=base_roll,
        crit_roll=crit_roll,
        ability_mod=ability_mod,
        ability_name=ability_name,
        stab_bonus=stab_bonus,
        damage_type=damage_type,
        is_crit=is_crit,
        has_move_modifier=uses_move_mod,
        context=context,
    )


def resolve_attack(pokemon: dict, move_id: str) -> AttackResult:
    """
    Full combat resolution for one move use.
    Returns an AttackResult with all relevant fields populated.
    """
    move_data = MOVE_LOOKUP.get(move_id)
    if not move_data:
        return AttackResult(
            pokemon_name=pokemon.get("name", "?"),
            move_name=move_id,
            fallback_text="Move not found.",
        )

    ability_scores   = _parse_ability_scores(pokemon)
    power_abilities  = move_data.get("power")
    prof             = pokemon.get("proficiency_bonus", 0)
    highest_mod, chosen_ability = _best_ability_mod(power_abilities, ability_scores)
    ability_name     = chosen_ability.upper() if chosen_ability else "N/A"

    description      = _description_text(move_data)
    has_save         = "save" in description
    has_attack       = (
        isinstance(power_abilities, list)
        and power_abilities
        and any(p in description for p in ("make a melee attack", "make a ranged attack", "make an attack"))
    )

    save_type  = _detect_save_type(description) if has_save else None
    save_dc    = (8 + highest_mod + prof) if has_save else None

    # Roll d20 only for attack moves
    d20_roll    = random.randint(1, 20) if has_attack else None
    is_crit     = d20_roll == 20 if d20_roll is not None else False
    is_crit_fail = d20_roll == 1 if d20_roll is not None else False
    attack_total = (d20_roll + highest_mod + prof) if has_attack else None

    damage_context = "on failed save" if (has_save and not has_attack) else "on hit"
    damage = calculate_damage(
        pokemon, move_data,
        ability_mod=highest_mod,
        ability_name=ability_name,
        is_crit=is_crit,
        prof=prof,
        context=damage_context,
    )

    # Status / fallback moves
    if not has_attack and not has_save:
        return AttackResult(
            pokemon_name=pokemon.get("name", "?"),
            move_name=move_data.get("name", move_id),
            fallback_text="See move description.",
        )

    return AttackResult(
        pokemon_name=pokemon.get("name", "?"),
        move_name=move_data.get("name", move_id),
        attack_total=attack_total,
        d20_roll=d20_roll,
        ability_mod=highest_mod,
        ability_name=ability_name,
        prof=prof,
        is_crit=is_crit,
        is_crit_fail=is_crit_fail,
        save_dc=save_dc,
        save_type=save_type,
        damage=damage,
    )


def format_battle_log(result: AttackResult) -> str:
    """
    Build the complete multi-line battle log entry for a move use.
    Reads directly from the AttackResult dataclass — no regex re-parsing.
    """
    lines = [f"{result.pokemon_name} uses {result.move_name}!", ""]

    if result.fallback_text:
        lines.append(f"Result: {result.fallback_text}")
        return "\n".join(lines)

    # --- Attack roll line ---
    if result.attack_total is not None:
        breakdown = (
            f"d20: {result.d20_roll} + {result.ability_mod} {result.ability_name}"
            f" + {result.prof} prof"
        )
        if result.is_crit:
            lines.append(f"Attack Roll: {result.attack_total} (CRITICAL HIT!)")
        elif result.is_crit_fail:
            lines.append(f"Attack Roll: {result.attack_total} (CRITICAL MISS!)")
        else:
            lines.append(f"Attack Roll: {result.attack_total}")
        lines.append(f"  └ {breakdown}")

    # --- Save DC line ---
    if result.save_dc is not None:
        save_label = f" ({result.save_type})" if result.save_type else ""
        if result.attack_total is not None:
            # Combined attack + save move (e.g. Vice Grip)
            lines.append(f"Save DC: {result.save_dc}{save_label}")
        else:
            dc_breakdown = (
                f"8 + {result.ability_mod} {result.ability_name} + {result.prof} prof"
            )
            lines.append(f"Spell Save DC: {result.save_dc}{save_label}")
            lines.append(f"  └ {dc_breakdown}")

    # --- Damage line ---
    dmg = result.damage
    if dmg is not None:
        crit_label = "CRITICAL! " if dmg.is_crit else ""
        lines.append(f"Damage: {dmg.total} {dmg.damage_type}")
        lines.append(f"  └ {crit_label}{dmg.breakdown}")

    return "\n".join(lines)
