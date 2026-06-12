"""
data/fakemon_store.py
All read/write logic for fakemon.json.
Format matches pokemon.json exactly so fakemon can be used
anywhere a regular Pokémon can.
"""

import json
import os

from config import FAKEMON_FILE

# Placeholder image used when no real image is provided
DEFAULT_IMAGE = ""


def _load_raw() -> dict:
    if not os.path.exists(FAKEMON_FILE):
        return {"items": []}
    with open(FAKEMON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_raw(data: dict):
    with open(FAKEMON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_fakemon() -> list[dict]:
    """Return all fakemon as a list."""
    return _load_raw().get("items", [])


def get_fakemon_names() -> list[str]:
    """Return sorted list of fakemon names."""
    return sorted(p["name"] for p in load_fakemon())


def save_fakemon(pokemon: dict):
    """
    Save or update a fakemon entry.
    Matches by name — if a pokemon with the same name exists it is overwritten,
    otherwise it is appended.
    """
    data  = _load_raw()
    items = data.get("items", [])

    existing_idx = next(
        (i for i, p in enumerate(items)
         if p["name"].lower() == pokemon["name"].lower()),
        None,
    )

    if existing_idx is not None:
        items[existing_idx] = pokemon
    else:
        items.append(pokemon)

    data["items"] = items
    _save_raw(data)


def delete_fakemon(name: str):
    """Remove a fakemon by name."""
    data  = _load_raw()
    items = [p for p in data.get("items", [])
             if p["name"].lower() != name.lower()]
    data["items"] = items
    _save_raw(data)


def get_fakemon(name: str) -> dict | None:
    """Return a single fakemon by name, or None."""
    return next(
        (p for p in load_fakemon() if p["name"].lower() == name.lower()),
        None,
    )
