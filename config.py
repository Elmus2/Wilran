"""
config.py
All constants, file paths, and static data tables for Wilran.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

if getattr(sys, "frozen", False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

JSONDATA_DIR   = os.path.join(SCRIPT_DIR, "jsondata")

# Read-only game data — lives in jsondata/
POKEMON_FILE   = os.path.join(JSONDATA_DIR, "pokemon.json")
TYPECHART_FILE = os.path.join(JSONDATA_DIR, "typechart.json")
ABILITIES_FILE = os.path.join(JSONDATA_DIR, "abilities.json")
MOVES_FILE     = os.path.join(JSONDATA_DIR, "moves.json")
TMS_FILE       = os.path.join(JSONDATA_DIR, "tms.json")
ITEMS_FILE     = os.path.join(JSONDATA_DIR, "items.json")

# User-managed data — lives in root
AREA_FILE      = os.path.join(SCRIPT_DIR, "areas.json")
HELDITEMS_FILE = os.path.join(SCRIPT_DIR, "helditems.json")
TRAINERS_FILE  = os.path.join(SCRIPT_DIR, "trainers.json")
FAKEMON_FILE   = os.path.join(SCRIPT_DIR, "fakemon.json")

DEFAULT_IMAGE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/0.png"

# ---------------------------------------------------------------------------
# Game constants
# ---------------------------------------------------------------------------

SHINY_ODDS       = 100      # 1-in-N chance of shiny
HELD_ITEM_CHANCE = 4        # 1-in-N chance of held item
MAX_MOVES        = 4
MAX_STAT_VALUE   = 20
MAX_LEVEL        = 20
ASI_BREAKPOINTS  = [4, 8, 12, 16]

LEVEL_KEYS = [
    ("level2",  2),
    ("level6",  6),
    ("level10", 10),
    ("level14", 14),
    ("level18", 18),
]

# Average HP gained per level for each hit-die size
HIT_DICE_BONUS = {
    "d4":  3,
    "d6":  4,
    "d8":  5,
    "d10": 6,
    "d12": 7,
    "d20": 11,
}

# ---------------------------------------------------------------------------
# Nature table
# ---------------------------------------------------------------------------
# Each nature has an equal 1-in-25 chance — roll with random.choice(NATURES).

NATURES = [
    {"name": "Hardy",   "increase": None,  "decrease": None },
    {"name": "Lonely",  "increase": "str", "decrease": "con"},
    {"name": "Brave",   "increase": "str", "decrease": "dex"},
    {"name": "Adamant", "increase": "str", "decrease": "wis"},
    {"name": "Naughty", "increase": "str", "decrease": "cha"},
    {"name": "Bold",    "increase": "con", "decrease": "str"},
    {"name": "Docile",  "increase": None,  "decrease": None },
    {"name": "Relaxed", "increase": "con", "decrease": "dex"},
    {"name": "Impish",  "increase": "con", "decrease": "wis"},
    {"name": "Lax",     "increase": "con", "decrease": "cha"},
    {"name": "Timid",   "increase": "dex", "decrease": "str"},
    {"name": "Hasty",   "increase": "dex", "decrease": "con"},
    {"name": "Serious", "increase": None,  "decrease": None },
    {"name": "Jolly",   "increase": "dex", "decrease": "wis"},
    {"name": "Naive",   "increase": "dex", "decrease": "cha"},
    {"name": "Modest",  "increase": "wis", "decrease": "str"},
    {"name": "Mild",    "increase": "wis", "decrease": "con"},
    {"name": "Quiet",   "increase": "wis", "decrease": "dex"},
    {"name": "Bashful", "increase": None,  "decrease": None },
    {"name": "Rash",    "increase": "wis", "decrease": "cha"},
    {"name": "Calm",    "increase": "cha", "decrease": "str"},
    {"name": "Gentle",  "increase": "cha", "decrease": "con"},
    {"name": "Sassy",   "increase": "cha", "decrease": "dex"},
    {"name": "Careful", "increase": "cha", "decrease": "wis"},
    {"name": "Quirky",  "increase": None,  "decrease": None },
]

# Ability-score abbreviation → canonical save-type label
SAVE_ABBREV = {
    "str": "STR", "strength": "STR",
    "dex": "DEX", "dexterity": "DEX",
    "con": "CON", "constitution": "CON",
    "int": "INT", "intelligence": "INT",
    "wis": "WIS", "wisdom": "WIS",
    "cha": "CHA", "charisma": "CHA",
}

# Skill → governing ability (3-letter key)
SKILL_ABILITIES = {
    "Athletics":      "str",
    "Acrobatics":     "dex",
    "Sleight of Hand":"dex",
    "Stealth":        "dex",
    "Arcana":         "int",
    "History":        "int",
    "Investigation":  "int",
    "Nature":         "int",
    "Religion":       "int",
    "Animal Handling":"wis",
    "Insight":        "wis",
    "Medicine":       "wis",
    "Perception":     "wis",
    "Survival":       "wis",
    "Deception":      "cha",
    "Intimidation":   "cha",
    "Performance":    "cha",
    "Persuasion":     "cha",
}
