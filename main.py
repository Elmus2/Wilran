"""
main.py
Entry point for Wilran. Loads data, builds the window, starts the loop.
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from data_loader import load_areas, load_all_pokemon as load_pokemon
from gui.app import WilranApp
from gui.battler import BattlerFrame
from gui.battle_log import BattleLogFrame
from config import SCRIPT_DIR


def main():
    print("🎲 Welcome to Wilran! Pokémon Randomizer 🎲")

    areas = load_areas()
    if not areas:
        print("❌ No area data found.")
        return

    all_pokemon = load_pokemon()
    if not all_pokemon:
        print("❌ No Pokémon data found in pokemon.json!")
        return

    root = tk.Tk()
    root.title("Wilran")
    root.geometry("1400x900")
    root.minsize(800, 500)

    # Set window icon
    icon_path = os.path.join(SCRIPT_DIR, "WilranWindowsIcon.png")
    if os.path.exists(icon_path):
        try:
            icon_img = ImageTk.PhotoImage(Image.open(icon_path))
            root.iconphoto(True, icon_img)
        except Exception:
            pass

    style = ttk.Style(root)
    style.configure("Selected.TFrame", background="#cce5ff")

    wrapper = tk.Frame(root)
    wrapper.pack(fill="both", expand=True)

    # --- Left: randomizer (fixed width) ---
    left = tk.Frame(wrapper, width=380)
    left.pack(side="left", fill="y", padx=5, pady=5)
    left.pack_propagate(False)

    # --- Center: battler (expandable) ---
    center = tk.Frame(wrapper)
    center.pack(side="left", fill="both", expand=True, padx=5, pady=5)

    # --- Right: battle log (fixed width) ---
    right = tk.Frame(wrapper, width=300)
    right.pack(side="right", fill="y", padx=5, pady=5)
    right.pack_propagate(False)

    # Instantiate in dependency order.
    # BattlerFrame needs battle_log; app needs battler.
    # After app is created we wire it back into battler so the battler
    # can switch tabs and refresh the trainer list.
    battle_log = BattleLogFrame(right)
    battle_log.pack(fill="both", expand=True)

    battler = BattlerFrame(center, battle_log, all_pokemon)
    battler.pack(fill="both", expand=True)

    app = WilranApp(left, areas, all_pokemon, battler)
    app.pack(fill="both", expand=True)

    # Back-reference so battler can call app.switch_to_leveler() etc.
    battler.app = app

    battle_log.log("⚔️ Battle log ready!")
    battle_log.log("Tip: Choose an area, randomize a Pokémon, and add to the tracker.")

    root.mainloop()


if __name__ == "__main__":
    main()
