import json
import os
import sys

# Fix for PyInstaller - get the directory where the executable is located
if getattr(sys, 'frozen', False):
    # Running as PyInstaller executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # Running as Python script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

POKEMON_FILE = os.path.join(SCRIPT_DIR, "pokemon.json")
AREA_FILE = os.path.join(SCRIPT_DIR, "areas.json")


def load_pokemon():
    """Load all Pokémon from pokemon.json"""
    if not os.path.exists(POKEMON_FILE):
        print(f"❌ {POKEMON_FILE} not found!")
        return []

    with open(POKEMON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("items", [])


def load_areas():
    """Load areas from areas.json"""
    if not os.path.exists(AREA_FILE):
        return {}
    with open(AREA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_areas(areas):
    """Save areas to areas.json with each Pokémon on one line"""
    with open(AREA_FILE, "w", encoding="utf-8") as f:
        f.write("{\n")
        area_count = len(areas)
        for i, (area_name, data) in enumerate(areas.items()):
            f.write(f'    "{area_name}": {{\n')
            f.write(f'        "name": "{data["name"]}",\n')
            f.write(f'        "pokemon": [\n')

            for j, p in enumerate(data["pokemon"]):
                # Single line per Pokémon
                comma = "," if j < len(data["pokemon"]) - 1 else ""
                f.write(
                    f'            {{"name": "{p["name"]}", "min_level": {p["min_level"]}, "max_level": {p["max_level"]}}}{comma}\n')

            f.write("        ]\n")
            comma = "," if i < area_count - 1 else ""
            f.write(f'    }}{comma}\n')
        f.write("}\n")


def get_level(prompt):
    """Prompt user for a level between 1 and 20"""
    while True:
        try:
            level = int(input(prompt).strip())
            if 1 <= level <= 20:
                return level
            else:
                print("❌ Level must be between 1 and 20.")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")


def select_pokemon(pokemon_list):
    """Prompt user to select Pokémon and levels"""
    selected = []

    while True:
        print("\nType the name of the Pokémon you want to add, or 'done' to finish.")
        name_input = input("Pokémon name: ").strip()
        if name_input.lower() == "done":
            break

        # Find Pokémon in the list
        match = next(
            (p for p in pokemon_list if p["name"].lower() == name_input.lower()), None)
        if not match:
            print("❌ Pokémon not found in pokemon.json. Try again.")
            continue

        min_level = get_level("Minimum level (1-20): ")
        max_level = get_level("Maximum level (1-20): ")

        if min_level > max_level:
            print("❌ Minimum level cannot be higher than maximum level. Try again.")
            continue

        selected.append({
            "name": match["name"],
            "min_level": min_level,
            "max_level": max_level
        })
        print(f"✅ Added {match['name']} (Lv {min_level}-{max_level})")

    return selected


def create_area(areas, pokemon_list):
    """Create a new area"""
    while True:
        area_name = input("Enter the name of the new area: ").strip()
        if not area_name:
            print("❌ Area name cannot be empty!")
            continue
        if area_name in areas:
            print(
                f"❌ Area '{area_name}' already exists. Please choose a different name.")
            continue
        break

    area_pokemon = select_pokemon(pokemon_list)
    if not area_pokemon:
        print("No Pokémon added. Exiting.")
        return

    areas[area_name] = {"name": area_name, "pokemon": area_pokemon}
    save_areas(areas)
    print(f"💾 Area '{area_name}' saved successfully!")


def list_areas(areas):
    """List all areas and their Pokémon"""
    if not areas:
        print("No areas available.")
        return
    for area_name, data in areas.items():
        print(f"\nArea: {area_name}")
        if not data["pokemon"]:
            print("  No Pokémon in this area.")
        for p in data["pokemon"]:
            print(f"  - {p['name']} (Lv {p['min_level']}-{p['max_level']})")


def delete_area(areas):
    """Delete an existing area"""
    area_name = input("Enter the name of the area to delete: ").strip()
    if area_name in areas:
        confirm = input(
            f"Are you sure you want to delete '{area_name}'? (yes/no): ").strip().lower()
        if confirm == "yes":
            del areas[area_name]
            save_areas(areas)
            print(f"❌ Area '{area_name}' deleted.")
        else:
            print("Deletion cancelled.")
    else:
        print("❌ Area not found.")


def edit_area(areas, pokemon_list):
    """Edit an existing area"""
    area_name = input("Enter the name of the area to edit: ").strip()
    if area_name not in areas:
        print("❌ Area not found.")
        return

    area = areas[area_name]
    print(f"\nEditing Area: {area_name}")
    print("Current Pokémon in area:")
    for p in area["pokemon"]:
        print(f"  - {p['name']} (Lv {p['min_level']}-{p['max_level']})")

    while True:
        action = input(
            "\nDo you want to add, edit, or remove Pokémon? (add/edit/remove/done): ").strip().lower()
        if action == "done":
            break
        elif action == "add":
            new_pokemon = select_pokemon(pokemon_list)
            area["pokemon"].extend(new_pokemon)
        elif action == "edit":
            p_name = input("Enter the name of the Pokémon to edit: ").strip()
            match = next(
                (p for p in area["pokemon"] if p["name"].lower() == p_name.lower()), None)
            if match:
                match["min_level"] = get_level("New minimum level (1-20): ")
                match["max_level"] = get_level("New maximum level (1-20): ")
                print(f"✅ Updated {match['name']} levels.")
            else:
                print("❌ Pokémon not found in this area.")
        elif action == "remove":
            p_name = input("Enter the name of the Pokémon to remove: ").strip()
            area["pokemon"] = [p for p in area["pokemon"]
                               if p["name"].lower() != p_name.lower()]
            print(f"✅ Pokémon '{p_name}' removed (if it existed).")
        else:
            print("❌ Invalid action. Type add, edit, remove, or done.")

    areas[area_name] = area
    save_areas(areas)
    print(f"💾 Area '{area_name}' updated successfully!")


def main_menu():
    """Main menu for area manager"""
    pokemon_list = load_pokemon()
    if not pokemon_list:
        return

    areas = load_areas()

    while True:
        print("\n--- Area Manager ---")
        print("1. Create a new area")
        print("2. List existing areas")
        print("3. Edit an area")
        print("4. Delete an area")
        print("5. Exit")
        choice = input("Choose an option (1-5): ").strip()

        if choice == "1":
            create_area(areas, pokemon_list)
        elif choice == "2":
            list_areas(areas)
        elif choice == "3":
            edit_area(areas, pokemon_list)
        elif choice == "4":
            delete_area(areas)
        elif choice == "5":
            print("Exiting Area Manager. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter a number between 1 and 5.")


if __name__ == "__main__":
    main_menu()
