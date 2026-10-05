# Mist Bot

Mist Bot was envisioned to support the functioning of Mist, a World of Warcraft gaming community.
Built utilizing PyCord, the aim is to provide rich commands and seamless automation. 

Chief among the features is the automated Droptimizer parsing and aggregating toolset.
These features allow community members to submit Droptimizer reports from Raidbots, search for valuable information in the aggregated data, and build reports detailing this data.

While Documentaiton is an ongoing process, please visit our Wiki, Discussions, and Issues pages to read up and contribute!

## Loot Roster Optimizer

Officers with `Manage Roles` can use `/loot optimize` with a boss name and a comma-separated list of exact WoWAudit character names. The bot reads Mythic wishlists only and recommends up to 20 candidates, with no more than two selected characters needing the same item for that boss. Needs are counted across the character's specializations.

Use `/loot deprioritize` to move a character behind other candidates, `/loot prioritize` to remove that preference, and `/loot deprioritized` to review the list. Deprioritized characters are included only when that does not reduce the largest valid roster. Recommendations are advisory; officers still set the in-game roster.