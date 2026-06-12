"""
mechanics/dice.py
Low-level dice and D&D stat helpers with no dependencies on other
Wilran modules (safe to import anywhere).
"""

import re
import random


def roll_dice(dice_str: str) -> int:
    """
    Roll NdM dice and return the total.
    Falls back to int(dice_str) if the string is a plain number.
    """
    match = re.match(r"(\d+)d(\d+)", dice_str)
    if not match:
        return int(dice_str)
    n, m = map(int, match.groups())
    return sum(random.randint(1, m) for _ in range(n))


def ability_modifier(score: int) -> int:
    """Return the D&D ability modifier for a given score."""
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    """Return the proficiency bonus for a given character level."""
    if level <= 4:
        return 2
    if level <= 8:
        return 3
    if level <= 12:
        return 4
    if level <= 16:
        return 5
    return 6
