"""
data_loader.py
Centralises all JSON file loading and exposes pre-built lookup tables.
Import the lookup dicts (MOVE_LOOKUP, ABILITY_LOOKUP, etc.) rather than
calling load_json() directly in other modules.
"""

import json
import os

from config import (
    AREA_FILE, POKEMON_FILE, TYPECHART_FILE,
    ABILITIES_FILE, MOVES_FILE, HELDITEMS_FILE, TMS_FILE, ITEMS_FILE,
)


def load_json(file_path: str) -> dict | list:
    """Load a JSON file and return its contents, or an empty dict on failure."""
    if not os.path.exists(file_path):
        print(f"❌ {file_path} not found!")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Pre-built lookups — imported by other modules
# ---------------------------------------------------------------------------

TYPE_CHART: dict[str, dict[str, float]] = load_json(TYPECHART_FILE)
ALL_TYPES: list[str] = list(TYPE_CHART.keys())

_abilities_raw: list[dict] = load_json(ABILITIES_FILE).get("items", [])
ABILITY_LOOKUP: dict[str, dict] = {a["id"]: a for a in _abilities_raw}

_moves_raw: list[dict] = load_json(MOVES_FILE).get("moves", [])
MOVE_LOOKUP: dict[str, dict] = {m["id"]: m for m in _moves_raw}

_tms_raw: list[dict] = load_json(TMS_FILE).get("tms", [])
# TM_LOOKUP: tm_number (int) → {"move_id": str, "cost": int, "display": str}
# display is formatted as "TM01 - Work Up" for use in dropdowns
TM_LOOKUP: dict[int, dict] = {
    t["id"]: {
        "move_id": t["move"],
        "cost":    t["cost"],
        "display": f"TM{t['id']:02d} - {t['move'].replace('-', ' ').title()}",
    }
    for t in _tms_raw
}

# Reverse lookup: display string → move_id, covers both regular and TM moves
_TM_DISPLAY_TO_ID: dict[str, str] = {
    v["display"]: v["move_id"] for v in TM_LOOKUP.values()
}


def move_id_from_display(display_name: str) -> str:
    """
    Convert a move display name to its MOVE_LOOKUP id.
    Handles both regular moves ("Vine Whip" → "vine-whip") and
    TM display names ("TM01 - Work Up" → "work-up").
    """
    # Check TM display names first
    if display_name in _TM_DISPLAY_TO_ID:
        return _TM_DISPLAY_TO_ID[display_name]
    # Regular move — strip indent spaces and convert to id format
    return display_name.strip().lower().replace(" ", "-")


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

_items_raw: list[dict] = load_json(ITEMS_FILE).get("items", [])

# All items lookup by id
ITEM_LOOKUP: dict[str, dict] = {i["id"]: i for i in _items_raw}

# Sorted list of held item and berry names for dropdowns
HELD_ITEM_NAMES: list[str] = sorted(
    i["name"] for i in _items_raw if i.get("type") in ("held item", "berry")
)


def load_areas() -> dict:
    return load_json(AREA_FILE)


def load_pokemon() -> list[dict]:
    return load_json(POKEMON_FILE).get("items", [])


def load_held_items() -> list:
    return load_json(HELDITEMS_FILE).get("items", [])


def load_all_pokemon() -> list[dict]:
    """Load both pokemon.json and fakemon.json, merging into one list."""
    from config import FAKEMON_FILE
    standard = load_json(POKEMON_FILE).get("items", [])
    fakemon  = load_json(FAKEMON_FILE).get("items", []) if os.path.exists(FAKEMON_FILE) else []
    return standard + fakemon
