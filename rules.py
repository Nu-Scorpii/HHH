"""Small, explicit tables shared by the engine and Discord UI."""

STATS = ("power", "speed", "wits", "heart")
DICE = (6, 8, 10, 12)
MOVES = {
    "heavy_hit": {"name": "Heavy Hit", "cost": 1, "rule": "Attack one foe: 3 damage on 4–7; 4 on 8+."},
    "burst": {"name": "Burst", "cost": 1, "rule": "One roll against up to three foes in one zone: 1 damage each on 4–7; 2 on 8+. Help improves only one named target's damage and Armor bypass."},
    "rescue_boost": {"name": "Rescue Boost", "cost": 1, "rule": "A fitting task gains 2 progress on 4–7; 3 on 8+. Prerequisites still apply."},
    "shield": {"name": "Shield", "cost": 1, "rule": "Action, no roll. Protect your zone against one enemy attack: −2 damage to friendly targets. Expires at your next turn; does not stack with Guard."},
    "capture": {"name": "Capture", "cost": 1, "rule": "4–7: no movement until the foe's next action ends and −1 damage on that action. 8+: cancel its next action. A boss loses at most one action per round."},
    "rapid_move": {"name": "Rapid Move", "cost": 1, "rule": "Replace your free move with movement to any reachable zone. Keep an ordinary action, but no second signature move."},
    "long_reach": {"name": "Long Reach", "cost": 1, "rule": "Attack a visible foe anywhere in the scene for 2 damage on 4–7; 3 on 8+. Needs a suitable ranged power."},
    "mend": {"name": "Mend", "cost": 2, "rule": "Action, touch, no roll. Heal 2, or revive a Down hero at 1. One healing action per recipient per fight, including Medical Patch."},
}
TALENTS = {
    "heavy_hitter": ("Heavy Hitter", "power"),
    "quick_feet": ("Quick on Your Feet", "speed"),
    "sharp_thinker": ("Sharp Thinker", "wits"),
    "strong_spirit": ("Strong Spirit", "heart"),
    "rescue_specialist": ("Rescue Specialist", "rescue"),
    "quirk_specialist": ("Quirk Specialist", "signature"),
}
ITEMS = {
    "grapple_line": "Free move across one anchored gap or difficult connection; no extra move.",
    "smoke_capsule": "Edge on one escape or hiding roll for you or an ally; no attack bonus.",
    "rescue_harness": "For one move, guide two cooperative people if you could normally move one.",
    "field_scanner": "Action, no roll: the GM answers one specific question with a useful true fact nearby.",
    "medical_patch": "Action, touch: heal 1 above 0 Health; cannot revive. One healing action per recipient per fight.",
}
ENEMIES = {"minion": (2, 1, 1), "rival": (4, 2, 1), "elite": (6, 2, 1), "boss": (12, 3, 2)}


class GameError(ValueError):
    """A safe, player-readable validation or permission error."""


def require(condition, message):
    if not condition:
        raise GameError(message)


def clean(text, maximum=1000, *, empty=False):
    value = str(text).strip()
    require((empty or bool(value)) and len(value) <= maximum, f"Use {'0' if empty else '1'}–{maximum} characters.")
    require("\x00" not in value, "That text contains an unsupported character.")
    return value


def ids(text):
    import re
    message = "Provide 1–25 user IDs or user mentions, separated by spaces or commas."
    text = str(text).strip()
    require(0 < len(text) <= 1000, message)
    tokens = re.split(r'[\s,]+', text)
    require(len(tokens) <= 25, message)
    values = []
    for token in tokens:
        match = re.fullmatch(r'(?:<@!?([0-9]{1,20})>|([0-9]{1,20}))', token)
        require(match is not None, message)
        value = int(match.group(1) or match.group(2))
        require(0 < value < 2**64, message)
        values.append(str(value))
    return list(dict.fromkeys(values))
