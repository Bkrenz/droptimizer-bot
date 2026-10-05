import re


MYTHIC_DIFFICULTY = 'Mythic'
ROLE_QUOTAS = {'tank': 2, 'healer': 4, 'damage': 14}
MAX_ROSTER_SIZE = sum(ROLE_QUOTAS.values())

SPEC_ROLES = {
    'blood': 'tank', 'vengeance': 'tank', 'guardian': 'tank', 'brewmaster': 'tank', 'protection': 'tank',
    'discipline': 'healer', 'holy': 'healer', 'restoration': 'healer', 'mistweaver': 'healer', 'preservation': 'healer',
    'devastation': 'damage', 'augmentation': 'damage', 'beast mastery': 'damage', 'marksmanship': 'damage',
    'survival': 'damage', 'arcane': 'damage', 'fire': 'damage', 'frost': 'damage', 'unholy': 'damage',
    'havoc': 'damage', 'feral': 'damage', 'balance': 'damage', 'outlaw': 'damage', 'subtlety': 'damage',
    'assassination': 'damage', 'windwalker': 'damage', 'retribution': 'damage', 'elemental': 'damage',
    'enhancement': 'damage', 'shadow': 'damage', 'affliction': 'damage', 'demonology': 'damage',
    'destruction': 'damage', 'devourer': 'damage',
    'fury': 'damage', 'arms': 'damage',
}


def _iter_payload_objects(value):
    if isinstance(value, dict):
        yield value
        for nested_value in value.values():
            yield from _iter_payload_objects(nested_value)
    elif isinstance(value, list):
        for nested_value in value:
            yield from _iter_payload_objects(nested_value)


def _iter_labels(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key in ('name', 'label', 'role', 'spec', 'specialization', 'display_name'):
            if key in value:
                yield from _iter_labels(value[key])
    elif isinstance(value, list):
        for nested_value in value:
            yield from _iter_labels(nested_value)


def _role_from_label(value: str) -> str | None:
    normalized_role = value.strip().casefold()
    if 'tank' in normalized_role:
        return 'tank'
    if 'heal' in normalized_role:
        return 'healer'
    if any(role_term in normalized_role for role_term in ('damage', 'dps', 'melee', 'ranged')):
        return 'damage'
    return None


def _specialization_role(value: str) -> str | None:
    normalized_spec = re.sub(r'[^a-z]+', ' ', value.casefold()).strip()
    padded_spec = f' {normalized_spec} '
    for spec_name, spec_role in SPEC_ROLES.items():
        if f' {spec_name} ' in padded_spec:
            return spec_role
    return None


def get_character_role(character: dict) -> str | None:
    for payload_object in _iter_payload_objects(character):
        for key, value in payload_object.items():
            normalized_key = key.casefold()
            if normalized_key in ('role', 'role_name', 'primary_role') or normalized_key.endswith('_role'):
                for label in _iter_labels(value):
                    role = _role_from_label(label)
                    if role is not None:
                        return role
            if any(part in normalized_key for part in ('spec', 'specialization', 'specialisation')):
                for label in _iter_labels(value):
                    role = _specialization_role(label)
                    if role is not None:
                        return role
    return None


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


def format_roster_recommendation_rows(
    selected: list[str],
    roles_by_character: dict[str, str],
    needs_by_character: dict[str, dict[str, str]],
) -> list[str]:
    rows = []
    for name in selected:
        role = roles_by_character.get(name, 'unclassified').title()
        loot_needs = ', '.join(needs_by_character.get(name, {}).values()) or 'No upgrades'
        rows.append(f'{name} | {role} | {loot_needs}')
    return rows


def recommend_roster(
    candidate_names: list[str],
    needs_by_character: dict[str, dict[str, str]],
    deprioritized: set[str],
    *,
    max_needing_item: int = 2,
    roles_by_character: dict[str, str] | None = None,
) -> tuple[list[str], dict[str, list[str]]]:
    deprioritized_names = {name.casefold() for name in deprioritized}
    needs_by_normalized_name = {
        name.casefold(): needs for name, needs in needs_by_character.items()
    }
    ordered_names = sorted(
        candidate_names,
        key=lambda name: (name.casefold() in deprioritized_names, candidate_names.index(name)),
    )
    role_quotas = ROLE_QUOTAS if roles_by_character is not None else {'unassigned': MAX_ROSTER_SIZE}
    roles_by_normalized_name = {
        name.casefold(): role.casefold() for name, role in (roles_by_character or {}).items()
    }
    order_indexes = {name.casefold(): index for index, name in enumerate(ordered_names)}
    selected = []
    item_counts = {}
    role_counts = {role: 0 for role in role_quotas}
    best_names = []
    best_deprioritized_count = len(ordered_names) + 1
    best_role_score = tuple(0 for _ in role_quotas)
    best_order_indexes = ()

    all_candidate_item_counts = {}
    for name in ordered_names:
        role = roles_by_normalized_name.get(name.casefold(), 'unassigned')
        if role not in role_quotas:
            continue
        for item_id in needs_by_normalized_name.get(name.casefold(), {}):
            all_candidate_item_counts[item_id] = all_candidate_item_counts.get(item_id, 0) + 1

    if all(count <= max_needing_item for count in all_candidate_item_counts.values()):
        for name in ordered_names:
            role = roles_by_normalized_name.get(name.casefold(), 'unassigned')
            if role in role_quotas and role_counts[role] < role_quotas[role]:
                best_names.append(name)
                role_counts[role] += 1
        best_deprioritized_count = sum(name.casefold() in deprioritized_names for name in best_names)
        best_role_score = tuple(role_counts[role] for role in role_quotas)
        best_order_indexes = tuple(order_indexes[name.casefold()] for name in best_names)

    def search(index: int, deprioritized_count: int) -> None:
        nonlocal best_names, best_deprioritized_count, best_role_score, best_order_indexes
        remaining_by_role = {role: 0 for role in role_quotas}
        for remaining_name in ordered_names[index:]:
            role = roles_by_normalized_name.get(remaining_name.casefold(), 'unassigned')
            if role in remaining_by_role:
                remaining_by_role[role] += 1
        possible_size = len(selected) + sum(
            min(role_quotas[role] - role_counts[role], remaining_by_role[role])
            for role in role_quotas
        )
        possible_role_score = tuple(
            min(role_quotas[role], role_counts[role] + remaining_by_role[role])
            for role in role_quotas
        )
        if possible_size < len(best_names):
            return
        if possible_size == len(best_names) and possible_role_score < best_role_score:
            return
        if (
            possible_size == len(best_names)
            and possible_role_score == best_role_score
            and deprioritized_count > best_deprioritized_count
        ):
            return
        if index == len(ordered_names) or len(selected) == MAX_ROSTER_SIZE:
            selected_indexes = tuple(order_indexes[name.casefold()] for name in selected)
            selected_role_score = tuple(role_counts[role] for role in role_quotas)
            if (
                len(selected) > len(best_names)
                or (len(selected) == len(best_names) and selected_role_score > best_role_score)
                or (
                    len(selected) == len(best_names)
                    and selected_role_score == best_role_score
                    and deprioritized_count < best_deprioritized_count
                )
                or (
                    len(selected) == len(best_names)
                    and selected_role_score == best_role_score
                    and deprioritized_count == best_deprioritized_count
                    and selected_indexes < best_order_indexes
                )
            ):
                best_names = selected.copy()
                best_deprioritized_count = deprioritized_count
                best_role_score = selected_role_score
                best_order_indexes = selected_indexes
            return

        name = ordered_names[index]
        needs = needs_by_normalized_name.get(name.casefold(), {})
        role = roles_by_normalized_name.get(name.casefold(), 'unassigned')
        if (
            role in role_quotas
            and role_counts[role] < role_quotas[role]
            and all(item_counts.get(item_id, 0) < max_needing_item for item_id in needs)
        ):
            selected.append(name)
            role_counts[role] += 1
            for item_id in needs:
                item_counts[item_id] = item_counts.get(item_id, 0) + 1
            search(index + 1, deprioritized_count + (name.casefold() in deprioritized_names))
            selected.pop()
            role_counts[role] -= 1
            for item_id in needs:
                item_counts[item_id] -= 1

        search(index + 1, deprioritized_count)

    if any(count > max_needing_item for count in all_candidate_item_counts.values()):
        role_counts = {role: 0 for role in role_quotas}
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