"""
data/area_store.py
All read/write logic for areas.json.
"""

import json
import os

from config import AREA_FILE


def _load_raw() -> dict:
    if not os.path.exists(AREA_FILE):
        return {}
    with open(AREA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_raw(data: dict):
    with open(AREA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_areas() -> dict:
    return _load_raw()


def get_area_names() -> list[str]:
    return sorted(_load_raw().keys())


def get_area(name: str) -> dict | None:
    return _load_raw().get(name)


def create_area(name: str):
    """Create a new empty area. Raises ValueError if name already exists."""
    name = name.strip()
    if not name:
        raise ValueError("Area name cannot be blank.")
    data = _load_raw()
    if name in data:
        raise ValueError(f"An area named '{name}' already exists.")
    data[name] = {"name": name, "pokemon": []}
    _save_raw(data)


def rename_area(old_name: str, new_name: str):
    """Rename an area. Raises ValueError if new name already exists."""
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Area name cannot be blank.")
    data = _load_raw()
    if new_name in data and new_name != old_name:
        raise ValueError(f"An area named '{new_name}' already exists.")
    area = data.pop(old_name)
    area["name"] = new_name
    data[new_name] = area
    _save_raw(data)


def add_pokemon_to_area(area_name: str, pokemon_name: str, min_level: int, max_level: int):
    data = _load_raw()
    if area_name not in data:
        raise ValueError(f"Area '{area_name}' not found.")
    data[area_name]["pokemon"].append({
        "name":      pokemon_name,
        "min_level": min_level,
        "max_level": max_level,
    })
    _save_raw(data)


def remove_pokemon_from_area(area_name: str, index: int):
    data = _load_raw()
    if area_name not in data:
        raise ValueError(f"Area '{area_name}' not found.")
    pokemon = data[area_name]["pokemon"]
    if not 0 <= index < len(pokemon):
        raise ValueError(f"Invalid index {index}.")
    pokemon.pop(index)
    _save_raw(data)


def delete_area(name: str):
    data = _load_raw()
    if name in data:
        del data[name]
        _save_raw(data)
