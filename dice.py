"""Bounded dice parser: no eval, arbitrary numbered dice and weighted custom faces."""

import json
import random
import re
from dataclasses import dataclass
from .rules import GameError, require

RNG = random.SystemRandom()
MAX_DICE = 100
MAX_SIDES = 1_000_000_000


@dataclass(frozen=True)
class Die:
    sides: int | None = None
    faces: tuple | None = None
    label: str = ""

    def roll(self, rng=RNG):
        return rng.randint(1, self.sides) if self.sides else rng.choice(self.faces)

    def contains(self, value):
        return isinstance(value, int) and 1 <= value <= self.sides if self.sides else value in self.faces

    def forced(self, outcome):
        # Preserve numeric labels; for custom dice, a string face has priority.
        if self.faces and outcome in self.faces:
            return outcome
        try:
            number = int(outcome)
        except (ValueError, TypeError):
            number = None
        if number is not None:
            return number if self.contains(number) else None
        if self.sides:
            bounds = {"min": (1, 1), "max": (self.sides, self.sides), "miss": (1, min(3, self.sides)),
                      "success": (4, min(7, self.sides)), "big": (8, self.sides)}
            if outcome not in bounds:
                return None
            low, high = bounds[outcome]
            return low if low <= high else None
        numbers = [x for x in self.faces if type(x) is int]
        if len(numbers) != len(self.faces):
            return None
        eligible = numbers if outcome in ("min", "max") else [x for x in numbers if
                    (1 <= x <= 3 if outcome == "miss" else 4 <= x <= 7 if outcome == "success" else x >= 8 if outcome == "big" else False)]
        return (max(eligible) if outcome == "max" else min(eligible)) if eligible else None


def parse_faces(value):
    try:
        faces = json.loads(value) if isinstance(value, str) else value
    except ValueError as exc:
        raise GameError('Faces must be JSON, such as [0,1,1,5] or ["sun","rain","storm"].') from exc
    require(isinstance(faces, list) and 1 <= len(faces) <= 1000, "A custom die needs 1–1000 faces. Repeated faces add weight.")
    require(all((type(f) is int and abs(f) <= MAX_SIDES) or
                (isinstance(f, str) and 1 <= len(f) <= 40 and "\x00" not in f) for f in faces),
            "Faces must be integers within ±1 billion or short text labels.")
    return faces


def parse(expression, custom):
    expression = expression.strip().lower().replace('−', '-')
    require(0 < len(expression) <= 500, "Keep the dice expression under 500 characters.")
    position, terms, count = 0, [], 0
    # Each term is signed integer or NdN / Nd[name]. Spaces are permitted.
    pattern = re.compile(r"\s*([+-]?)\s*(?:(\d*)d(\d+|\[[a-z][a-z0-9_]{0,31}\])|(\d+))")
    while position < len(expression):
        match = pattern.match(expression, position)
        require(match is not None, "Use dice such as 2d17 + 1d8 - 3 or 1d[weather].")
        sign, amount, source, modifier = match.groups()
        require(not terms or bool(sign), "Separate dice terms with + or −.")
        sign_value = -1 if sign == "-" else 1
        if modifier is not None:
            require(int(modifier) <= MAX_SIDES, "Modifiers are limited to ±1 billion.")
            terms.append((sign_value, int(modifier)))
        else:
            n = int(amount) if amount else 1
            count += n
            require(n >= 1 and count <= MAX_DICE, "Roll 1–100 dice per command.")
            if source.startswith("["):
                name = source[1:-1]
                require(name in custom, 'That saved die does not exist. Use numbered dice, or dice:1d[custom] with faces:[0,1,1,5].')
                die = Die(faces=tuple(parse_faces(custom[name])), label=f"d[{name}]")
            else:
                sides = int(source)
                require(1 <= sides <= MAX_SIDES, "Numbered dice can have 1–1 billion sides.")
                die = Die(sides=sides, label=f"d{sides}")
            terms.append((sign_value, [die] * n))
        position = match.end()
        if not expression[position:].strip():
            break
        require(len(terms) < 20, "Use at most 20 terms.")
    require(count > 0, "Include at least one die.")
    return terms


def roll_expression(expression, custom, rng=RNG, keep="all", force=None, *, bonus=0):
    require(keep in ("all", "high", "low"), "Keep must be all, high, or low.")
    require(type(bonus) is int and abs(bonus) <= MAX_SIDES, "Bonus points must be a whole number within ±1 billion.")
    terms = parse(expression, custom)
    dice = [die for _, term in terms if isinstance(term, list) for die in term]
    pools = [(sign, term) for sign, term in terms if isinstance(term, list)]
    require(keep == "all" or len(pools) == 1 and pools[0][0] == 1, "Keep-high/low uses a single positive dice pool, such as 2d10+3.")
    # Validate possible faces before drawing anything. A mixed die must not
    # randomly accept an operation on numeric faces and reject its text faces.
    text_dice = any(die.faces and any(type(face) is not int for face in die.faces) for die in dice)
    if text_dice:
        require(keep == 'all', "Keep-high/low needs entirely numeric dice faces.")
        require(bonus == 0, "Text dice cannot have bonus points.")
        require(all(not isinstance(term, int) for _, term in terms), "Text dice cannot have numeric modifiers.")
        require(all(sign == 1 or all(not die.faces or all(type(face) is int for face in die.faces) for die in term)
                    for sign, term in terms if isinstance(term, list)), "Text faces cannot be subtracted.")
    forced = [die.forced(force) for die in dice] if force is not None else None
    require(forced is None or all(x is not None for x in forced), "That outcome is unavailable on one of these dice.")
    results, total, numeric, offset = [], 0, True, 0
    for sign, term in terms:
        if isinstance(term, int):
            results.append({"modifier": sign * term})
            total += sign * term
            continue
        values = [forced[offset + j] if forced is not None else die.roll(rng) for j, die in enumerate(term)]
        offset += len(term)
        all_numbers = all(type(x) is int for x in values)
        require(all_numbers or keep == "all", "Keep-high/low needs numeric dice faces.")
        numeric &= all_numbers
        kept = (max(values) if keep == "high" else min(values)) if keep != "all" else None
        if all_numbers:
            total += sign * (kept if kept is not None else sum(values))
        else:
            require(sign == 1, "Text faces cannot be subtracted.")
        results.append({"die": term[0].label, "sign": sign, "rolls": values, "kept": kept})
    require(numeric or all("modifier" not in x for x in results), "Text dice cannot have numeric modifiers.")
    return {"expression": expression, "groups": results, "bonus": bonus,
            "keep": keep, "total": total + bonus if numeric else None}


def stat_roll(sides, edge=False, pressure=False, rng=RNG, force=None):
    die = Die(sides=sides, label=f"d{sides}")
    count = 1 if bool(edge) == bool(pressure) else 2
    values = [die.roll(rng) for _ in range(count)]
    kept = min(values) if pressure and not edge else max(values)
    if force is not None:
        wanted = die.forced(force)
        require(wanted is not None, "That result is unavailable on this stat die.")
        # Both faces remain possible and consistent with the kept result.
        values[0] = wanted
        if count == 2:
            values[1] = max(values[1], wanted) if pressure else min(values[1], wanted)
        kept = wanted
    return {"die": sides, "rolls": values, "kept": kept,
            "mode": "normal" if count == 1 else "pressure" if pressure else "edge"}
