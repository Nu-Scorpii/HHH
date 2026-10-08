"""Private transformations which keep displayed dice and arithmetic consistent."""

from copy import deepcopy

MAX_SEARCH = 100_000
BANDS = {'miss': (1, 3), 'success': (4, 7), 'big': (8, 10**12)}


def numeric(dice):
    return all(d.sides or all(type(f) is int for f in d.faces) for d in dice)


def clamp(value, low, high):
    return max(low, min(value, high))


def nearest(values, wanted):
    return min(values, key=lambda value: (abs(value - wanted), value))


def stat_result(natural, die, mode, outcome):
    if mode == 'face':
        wanted = die.forced(outcome)
    elif mode == 'force':
        wanted = 1 if outcome == 'min' else die.sides if outcome == 'max' else int(outcome)
        if not die.contains(wanted):
            return None
    elif mode == 'shift':
        wanted = clamp(natural['kept'] + int(outcome), 1, die.sides)
    else:
        grade = 0 if natural['kept'] <= 3 else 1 if natural['kept'] <= 7 else 2
        names = tuple(BANDS)
        choices = (range(grade + 1, 3) if outcome == 'up' else range(grade - 1, -1, -1)) if outcome in ('up','down') else [names.index(outcome)]
        wanted = None
        for index in choices:
            low, high = BANDS[names[index]]
            if low <= die.sides:
                wanted = clamp(natural['kept'], low, min(high, die.sides))
                break
        if wanted is None and outcome in ('up','down'):
            wanted = natural['kept']
    if wanted is None:
        return None
    result = dict(natural, rolls=list(natural['rolls']), kept=wanted)
    index = result['rolls'].index(natural['kept'])
    result['rolls'][index] = wanted
    if len(result['rolls']) == 2:
        adjust = max if result['mode'] == 'pressure' else min
        result['rolls'] = [adjust(value, wanted) for value in result['rolls']]
    return result


def variables(terms):
    return [(die, sign) for sign, term in terms if isinstance(term, list) for die in term]


def rebuild(natural, values):
    result = deepcopy(natural)
    total, offset, all_numeric = result.get('bonus', 0), 0, True
    for group in result['groups']:
        if 'modifier' in group:
            total += group['modifier']
            continue
        count = len(group['rolls'])
        group['rolls'] = values[offset:offset + count]
        offset += count
        numbers = all(type(value) is int for value in group['rolls'])
        all_numeric &= numbers
        group['kept'] = (min(group['rolls']) if result['keep'] == 'low' else max(group['rolls'])) if result['keep'] != 'all' else None
        if numbers:
            total += group['sign'] * (group['kept'] if group['kept'] is not None else sum(group['rolls']))
    result['total'] = total if all_numeric else None
    return result


def bounds(natural, terms):
    fixed = natural.get('bonus', 0) + sum(group.get('modifier', 0) for group in natural['groups'])
    dice = variables(terms)
    if natural['keep'] != 'all':
        die = dice[0][0]
        return fixed + (1 if die.sides else min(die.faces)), fixed + (die.sides or max(die.faces))
    low = high = fixed
    for die, sign in dice:
        minimum, maximum = (1, die.sides) if die.sides else (min(die.faces), max(die.faces))
        low += minimum if sign > 0 else -maximum
        high += maximum if sign > 0 else -minimum
    return low, high


def fit_total(natural, terms, low, high, preferred, *, approximate=False):
    """Find legal faces in a total interval, with bounded search for sparse dice."""
    dice = variables(terms)
    minimum, maximum = bounds(natural, terms)
    low, high = max(low, minimum), min(high, maximum)
    if low > high:
        return None
    preferred = clamp(preferred, low, high)
    fixed = natural.get('bonus', 0) + sum(g.get('modifier', 0) for g in natural['groups'])
    original = [value for g in natural['groups'] if 'die' in g for value in g['rolls']]
    if natural['keep'] != 'all':
        die = dice[0][0]
        if die.sides:
            wanted = clamp(preferred - fixed, max(1, low - fixed), min(die.sides, high - fixed))
        else:
            available = [face for face in set(die.faces) if low <= face + fixed <= high]
            if not available:
                if not approximate:
                    return None
                available = list(set(die.faces))
            wanted = nearest(available, preferred - fixed)
        choose = min if natural['keep'] == 'high' else max
        selected = max(original) if natural['keep'] == 'high' else min(original)
        original[original.index(selected)] = wanted
        return rebuild(natural, [choose(value, wanted) for value in original])

    contribution = [sign * value for value, (_, sign) in zip(original, dice)]
    ranges, discrete = {}, {}
    for index, (die, sign) in enumerate(dice):
        if die.sides:
            ranges[index] = (1, die.sides) if sign > 0 else (-die.sides, -1)
        else:
            discrete[index] = sorted({sign * face for face in die.faces})
    continuous_low = sum(limits[0] for limits in ranges.values())
    continuous_high = sum(limits[1] for limits in ranges.values())
    target = preferred - fixed

    def with_continuous(plan, goal):
        plan = list(plan)
        difference = goal - sum(plan)
        for index, (lower, upper) in ranges.items():
            replacement = clamp(plan[index] + difference, lower, upper)
            difference -= replacement - plan[index]
            plan[index] = replacement
        return plan

    def output(plan):
        return rebuild(natural, [sign * value for value, (_, sign) in zip(plan, dice)])

    # Most rolls have contiguous numbered dice or need only one face changed.
    plan = with_continuous(contribution, target)
    best = list(plan)
    for index, available in discrete.items():
        difference = target - sum(plan)
        plan[index] = nearest(available, plan[index] + difference)
        plan = with_continuous(plan, target)
        if abs(target - sum(plan)) < abs(target - sum(best)):
            best = list(plan)
        if low <= sum(plan) + fixed <= high:
            return output(plan)
    if low <= sum(plan) + fixed <= high:
        return output(plan)

    # A small interval dynamic program covers non-greedy sparse combinations.
    # Contiguous dice are intervals; never enumerate up to a billion faces.
    items = list(discrete.items())
    future_low = sum(values[0] for _, values in items) + continuous_low
    future_high = sum(values[-1] for _, values in items) + continuous_high
    states, visits = {0: ()}, 0
    for position, (index, available) in enumerate(items):
        future_low -= available[0]
        future_high -= available[-1]
        next_states = {}
        ordered = sorted(available, key=lambda value: (abs(value - contribution[index]), value))
        for subtotal, chosen in states.items():
            for value in ordered:
                visits += 1
                if visits > MAX_SEARCH:
                    return output(best) if approximate else None
                current = subtotal + value
                if current + future_low + fixed > high or current + future_high + fixed < low:
                    continue
                if current in next_states:
                    continue
                selection = chosen + (value,)
                if position == len(items) - 1:
                    feasible_low = max(continuous_low, low - fixed - current)
                    feasible_high = min(continuous_high, high - fixed - current)
                    if feasible_low <= feasible_high:
                        candidate = list(contribution)
                        for (slot, _), replacement in zip(items, selection):
                            candidate[slot] = replacement
                        goal = current + clamp(target - current, feasible_low, feasible_high)
                        return output(with_continuous(candidate, goal))
                next_states[current] = selection
        states = next_states
        if not states:
            break
    return output(best) if approximate else None


def expression_result(natural, terms, mode, outcome):
    dice = variables(terms)
    if mode == 'face':
        forced = [die.forced(outcome) for die, _ in dice]
        return rebuild(natural, forced) if all(value is not None for value in forced) else None
    if not numeric([die for die, _ in dice]):
        return None
    low, high = bounds(natural, terms)
    if mode == 'force':
        wanted = low if outcome == 'min' else high if outcome == 'max' else int(outcome)
        return fit_total(natural, terms, wanted, wanted, wanted)
    if mode == 'shift':
        wanted = clamp(natural['total'] + int(outcome), low, high)
        return fit_total(natural, terms, wanted, wanted, wanted, approximate=True)
    grade = 0 if natural['total'] <= 3 else 1 if natural['total'] <= 7 else 2
    names = tuple(BANDS)
    choices = (range(grade + 1, 3) if outcome == 'up' else range(grade - 1, -1, -1)) if outcome in ('up','down') else [names.index(outcome)]
    for index in choices:
        lower, upper = BANDS[names[index]]
        result = fit_total(natural, terms, lower, upper, natural['total'])
        if result is not None:
            return result
    return deepcopy(natural) if outcome in ('up','down') else None
