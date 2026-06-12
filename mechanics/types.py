"""
mechanics/types.py
PokemonType: computes defensive multipliers, vulnerabilities,
resistances, and immunities from the type chart.
"""

from data_loader import TYPE_CHART, ALL_TYPES


class PokemonType:
    def __init__(self, types: list[str]):
        if not types or len(types) > 2:
            raise ValueError("PokemonType must have 1 or 2 types.")
        for t in types:
            if t not in TYPE_CHART:
                raise ValueError(f"Invalid Pokémon type: {t!r}")
        self.types = types

    # ------------------------------------------------------------------
    # Core calculation
    # ------------------------------------------------------------------

    def defensive_multipliers(self) -> dict[str, float]:
        result = {}
        for attack_type in ALL_TYPES:
            multiplier = 1.0
            for defending_type in self.types:
                multiplier *= TYPE_CHART[defending_type][attack_type]
            result[attack_type] = multiplier
        return result

    # ------------------------------------------------------------------
    # Convenience views
    # ------------------------------------------------------------------

    def vulnerabilities(self) -> list[str]:
        return sorted(t for t, m in self.defensive_multipliers().items() if m > 1)

    def resistances(self) -> list[str]:
        return sorted(t for t, m in self.defensive_multipliers().items() if 0 < m < 1)

    def immunities(self) -> list[str]:
        imm = sorted(t for t, m in self.defensive_multipliers().items() if m == 0)
        return imm if imm else ["None"]
