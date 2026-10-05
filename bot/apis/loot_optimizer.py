MYTHIC_DIFFICULTY = 'Mythic'
MAX_ROSTER_SIZE = 20


def parse_character_names(value: str) -> list[str]:
    names = []
    seen = set()
    for name in value.split(','):
        name = name.strip()
        normalized = name.casefold()
        if name and normalized not in seen:
            names.append(name)
            seen.add(normalized)
    return names


def get_boss_item_needs(character_wishlist: dict, boss_name: str) -> dict[str, str]:
    needs = {}
    normalized_boss = boss_name.strip().casefold()

    for instance in character_wishlist.get('instances', []):
        for difficulty_entry in instance.get('difficulties', []):
            if difficulty_entry.get('difficulty', '').casefold() != MYTHIC_DIFFICULTY.casefold():
                continue

            wishlist = difficulty_entry.get('wishlist') or {}
            for encounter in wishlist.get('encounters', []):
                if encounter.get('name', '').strip().casefold() != normalized_boss:
                    continue
                for item in encounter.get('items', []):
                    item_id = item.get('id')
                    if item_id is not None:
                        needs[str(item_id)] = item.get('name') or str(item_id)

    return needs


def recommend_roster(
    candidate_names: list[str],
    needs_by_character: dict[str, dict[str, str]],
    deprioritized: set[str],
    *,
    max_needing_item: int = 2,
) -> tuple[list[str], dict[str, list[str]]]:
    deprioritized_names = {name.casefold() for name in deprioritized}
    needs_by_normalized_name = {
        name.casefold(): needs for name, needs in needs_by_character.items()
    }
    ordered_names = sorted(
        candidate_names,
        key=lambda name: (name.casefold() in deprioritized_names, candidate_names.index(name)),
    )
    order_indexes = {name.casefold(): index for index, name in enumerate(ordered_names)}
    selected = []
    item_counts = {}
    best_names = []
    best_deprioritized_count = len(ordered_names) + 1
    best_order_indexes = ()

    all_candidate_item_counts = {}
    for name in ordered_names:
        for item_id in needs_by_normalized_name.get(name.casefold(), {}):
            all_candidate_item_counts[item_id] = all_candidate_item_counts.get(item_id, 0) + 1

    if all(count <= max_needing_item for count in all_candidate_item_counts.values()):
        best_names = ordered_names[:MAX_ROSTER_SIZE]

    def search(index: int, deprioritized_count: int) -> None:
        nonlocal best_names, best_deprioritized_count, best_order_indexes
        if min(MAX_ROSTER_SIZE, len(selected) + len(ordered_names) - index) < len(best_names):
            return
        if index == len(ordered_names) or len(selected) == MAX_ROSTER_SIZE:
            selected_indexes = tuple(order_indexes[name.casefold()] for name in selected)
            if (
                len(selected) > len(best_names)
                or (len(selected) == len(best_names) and deprioritized_count < best_deprioritized_count)
                or (
                    len(selected) == len(best_names)
                    and deprioritized_count == best_deprioritized_count
                    and selected_indexes < best_order_indexes
                )
            ):
                best_names = selected.copy()
                best_deprioritized_count = deprioritized_count
                best_order_indexes = selected_indexes
            return

        name = ordered_names[index]
        needs = needs_by_normalized_name.get(name.casefold(), {})
        if all(item_counts.get(item_id, 0) < max_needing_item for item_id in needs):
            selected.append(name)
            for item_id in needs:
                item_counts[item_id] = item_counts.get(item_id, 0) + 1
            search(index + 1, deprioritized_count + (name.casefold() in deprioritized_names))
            selected.pop()
            for item_id in needs:
                item_counts[item_id] -= 1

        search(index + 1, deprioritized_count)

    if any(count > max_needing_item for count in all_candidate_item_counts.values()):
        search(0, 0)
    selected_set = {name.casefold() for name in best_names}
    best_item_counts = {}
    for name in best_names:
        for item_id in needs_by_normalized_name.get(name.casefold(), {}):
            best_item_counts[item_id] = best_item_counts.get(item_id, 0) + 1

    excluded = {}
    for name in candidate_names:
        if name.casefold() in selected_set:
            continue
        needs = needs_by_normalized_name.get(name.casefold(), {})
        blocked_items = [item_id for item_id in needs if best_item_counts.get(item_id, 0) >= max_needing_item]
        excluded[name] = [needs[item_id] for item_id in blocked_items]

    return best_names, excluded