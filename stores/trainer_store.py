"""
data/trainer_store.py
All read/write logic for trainers.json.
Keeps every file-system operation in one place so the rest of the app
never touches the file directly.

File format:
{
    "trainers": [
        {
            "id":      "trainer_001",
            "name":    "Ash",
            "pokemon": [ { ... pokemon dict ... }, ... ]
        }
    ]
}
"""

import json
import os
import uuid

from config import TRAINERS_FILE

# Fields that are internal to the leveler and should NOT be saved
# (they contain raw Python objects like full_pokemon dicts that
#  can't be serialised to JSON)
_SKIP_FIELDS = {"_full_pokemon"}


def _clean_for_save(pokemon: dict) -> dict:
    """Strip unserialisable fields before writing to JSON."""
    return {k: v for k, v in pokemon.items() if k not in _SKIP_FIELDS}


def _load_raw() -> dict:
    """Load trainers.json, creating it if it doesn't exist."""
    if not os.path.exists(TRAINERS_FILE):
        return {"trainers": []}
    with open(TRAINERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_raw(data: dict):
    """Write the full data structure back to trainers.json."""
    with open(TRAINERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_trainers() -> list[dict]:
    """Return the list of all trainer dicts."""
    return _load_raw().get("trainers", [])


def get_trainer_names() -> list[str]:
    """Return a sorted list of trainer names."""
    return sorted(t["name"] for t in load_trainers())


def create_trainer(name: str) -> dict:
    """
    Create a new trainer with the given name and save it.
    Returns the new trainer dict.
    Raises ValueError if the name is blank or already taken.
    """
    name = name.strip()
    if not name:
        raise ValueError("Trainer name cannot be blank.")

    data = _load_raw()
    existing = [t["name"].lower() for t in data["trainers"]]
    if name.lower() in existing:
        raise ValueError(f"A trainer named '{name}' already exists.")

    trainer = {
        "id":      str(uuid.uuid4()),
        "name":    name,
        "pokemon": [],
    }
    data["trainers"].append(trainer)
    _save_raw(data)
    return trainer


def add_pokemon_to_trainer(trainer_name: str, pokemon: dict):
    """
    Append a Pokémon to the named trainer's list and save.
    Raises ValueError if the trainer doesn't exist.
    """
    data = _load_raw()
    trainer = next(
        (t for t in data["trainers"] if t["name"] == trainer_name), None
    )
    if trainer is None:
        raise ValueError(f"Trainer '{trainer_name}' not found.")

    trainer["pokemon"].append(_clean_for_save(pokemon))
    _save_raw(data)


def remove_pokemon_from_trainer(trainer_name: str, pokemon_index: int):
    """
    Remove the Pokémon at the given index from the trainer's list and save.
    Raises ValueError if trainer not found or index out of range.
    """
    data = _load_raw()
    trainer = next(
        (t for t in data["trainers"] if t["name"] == trainer_name), None
    )
    if trainer is None:
        raise ValueError(f"Trainer '{trainer_name}' not found.")
    if not 0 <= pokemon_index < len(trainer["pokemon"]):
        raise ValueError(f"Invalid Pokémon index {pokemon_index}.")

    trainer["pokemon"].pop(pokemon_index)
    _save_raw(data)


def get_trainer_pokemon(trainer_name: str) -> list[dict]:
    """Return the Pokémon list for the named trainer, or [] if not found."""
    data = _load_raw()
    trainer = next(
        (t for t in data["trainers"] if t["name"] == trainer_name), None
    )
    return trainer["pokemon"] if trainer else []


def delete_trainer(trainer_name: str):
    """Delete a trainer entirely from trainers.json."""
    data = _load_raw()
    data["trainers"] = [t for t in data["trainers"] if t["name"] != trainer_name]
    _save_raw(data)
