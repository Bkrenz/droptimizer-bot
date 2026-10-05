# Mist Bot

Mist Bot was envisioned to support the functioning of Mist, a World of Warcraft gaming community.
Built utilizing PyCord, the aim is to provide rich commands and seamless automation. 

Chief among the features is the automated Droptimizer parsing and aggregating toolset.
These features allow community members to submit Droptimizer reports from Raidbots, search for valuable information in the aggregated data, and build reports detailing this data.

While Documentaiton is an ongoing process, please visit our Wiki, Discussions, and Issues pages to read up and contribute!

## Loot Roster Optimizer

Officers with `Manage Roles` can use `/loot optimize` with a boss name. Boss autocomplete is populated from current Mythic WoWAudit wishlists, and the bot automatically evaluates every character in the WoWAudit roster. Recommendations target 2 tanks, 4 healers, and 14 DPS, with no more than two selected characters needing the same item for that boss. Among equally large, role-balanced rosters, the bot prefers the lineup with the greatest summed item upgrade percentages. Needs are counted across the character's specializations.

Use `/loot deprioritize` to move a character behind other candidates, `/loot prioritize` to remove that preference, and `/loot deprioritized` to review the list. Deprioritized characters are included only when that does not reduce the largest valid roster. Characters without a recognizable role in WoWAudit data are not selected. Recommendations are advisory; officers still set the in-game roster.