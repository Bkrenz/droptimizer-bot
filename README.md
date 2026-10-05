# Mist Bot

Mist Bot was envisioned to support the functioning of Mist, a World of Warcraft gaming community.
Built utilizing PyCord, the aim is to provide rich commands and seamless automation. 

Chief among the features is the automated Droptimizer parsing and aggregating toolset.
These features allow community members to submit Droptimizer reports from Raidbots, search for valuable information in the aggregated data, and build reports detailing this data.

While Documentaiton is an ongoing process, please visit our Wiki, Discussions, and Issues pages to read up and contribute!

## Loot Roster Optimizer

Officers with `Manage Roles` can use `/loot optimize` with a boss name. Boss autocomplete is populated from current Mythic WoWAudit wishlists, and the bot automatically evaluates every character in the WoWAudit roster. Recommendations target 2 tanks, 4 healers, and 14 DPS. The bot selects the largest role-balanced roster by the sum of the top two raw absolute gains per item, then orders boss items by their strongest available raw gain and assigns up to two priority recipients per item. A player may receive priority assignments for multiple items; the cap applies to each item, not raid attendance. Allocated items show both raw gain and upgrade percentage. Needs are counted across the character's specializations.

Use `/loot deprioritize` to blacklist a character from roster recommendations, `/loot prioritize` to restore eligibility, and `/loot deprioritized` to review the blacklist. Blacklisted characters are never selected. Characters without a recognizable role in WoWAudit data are not selected. Recommendations are advisory; officers still set the in-game roster.