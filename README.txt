Welcome to Wilran! My friend Claude and I created this app to help dungeon masters run their D&D 5e Pokémon game using the rules from https://poke5e.app/


TL;DR This app will allow the user to quickly create and roll for battle ready Pokémon to use at their table. 


Wilran has a few features sorted into tabs at the top left.

Area Builder - Here you will assign wild Pokémon to an area or route for use in the Random Wild tab. You can set a minimum and maximum level range. This data is saved in the areas.json, if you want to manually edit it. Just mind the formatting.

Random Wild - This is where you will randomize the wild Pokémon encounters based on the area or routes you created in the area builder tab. You can then add it to the tracker.
Some things it does when randomizing.

- Add a random nature and adjust ability scores
- Level up the Pokémon and adjust everything that comes with leveling it, randomizing ASIs
- Randomly give it four moves from its list
- Give the Pokémon a 1 in 100 chance of being a shiny
- Give it a random available ability as well as show the hidden ability
- Give it a 1 in 4 chance of having a held item

Leveler - This tab allows you to generate a Pokémon from level 1, picking its nature, ability, gender, held item, and moves. Then you level it up, picking from its available moves and tm's as they become available, as well as its ASIs when they become available. You can add this Pokémon to the tracker, or assign it to a trainer.

Trainer - Here you can create and manage trainer Pokémon teams as well as add their Pokémon to the tracker to battle with.

Fakemon -  This is where you would create your custom Pokémon. Anything created here will be added to the fakemon.json and be available in all the other tabs.


In the center of Wilran, is the battler. Any Pokémon in the tracker can be seen and battled with here. You can track HP and move PP as well as roll attack and damage rolls for most moves. Some moves don't work yet and will need manual dice rolls but all move descriptions will be there. There is a dice roller in this section for when those pop up. You can also make ability checks and saving throws for the Pokémon from here. Any Pokémon loaded into the battler, can also be opened in the leveler for quick modifying or assigned to a trainer.


In this file, there are a few important .jsons.

The abilities, items, moves, pokemon, tms, trainers, and typechart .jsons should remain untouched.

areas.json can be modified if you are careful. I recommend making a copy before attempting to make changes.

helditems.json are the held items that wild pokemon generated using the random wild tab might hold (25% chance). You can edit this pretty easily, just make sure to keep the format. If you want an item to have a higher weight, just add it to the list more times.

trainers.json is where the trainer data is held. You could edit this, but I recommend just using the trainer tab.





