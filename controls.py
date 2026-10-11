"""One active creator setting. Commands are accepted only in the creator's DMs."""

import re
import shlex
from .errors import RollError, require

HELP = '''!Rigger 15 — force the next final total to 15
!Rigger +3 / !Rigger -2 — shift the next total
!Rigger good / !Rigger bad — lasting luck
!Rigger off — clear the setting
!Rigger status — show the setting and last affected roll

Optional: add @User or their user ID to target that person in every server.
Example: !Rigger 15 123456789012345678
Without a target, the setting applies to anyone in any server.

Each new setting replaces the old one. Force and shift are used once.
Good/bad rolls twice and keeps the better/worse whole roll until switched off.
Force means the FINAL total, including modifiers and bonus points.
Impossible results roll normally, clear the one-use setting, and notify only you.
Text dice: !Rigger face "storm" forces one text face on one custom die.
Negative forced total: !Rigger force -4.
!Rigger help brings back this guide.'''

MAX_VALUE = 200_000_000_000
TARGET = re.compile(r'(?:<@!?(\d+)>|(\d+))\Z')
NUMBER = re.compile(r'[+-]?\d+\Z')
COMMAND = re.compile(r'!rigger(?:\s|$)', re.IGNORECASE)


def empty_setting():
    return {'mode': 'off', 'value': None, 'target': None, 'last': None}


def parse_command(content):
    require(isinstance(content, str) and len(content) <= 500, 'Keep the command under 500 characters.')
    try:
        words = shlex.split(content)
    except ValueError as exc:
        raise RollError('Close your quotation marks. Example: !Rigger face "heavy rain".') from exc
    args = words[1:]
    if not args:
        return 'help', None
    first = args.pop(0).lower()
    if first in ('help', 'status', 'off'):
        require(not args, f'Use !Rigger {first} by itself.')
        return first, None
    if first in ('force', 'shift', 'face', 'luck'):
        require(args, 'Give a value. Examples: !Rigger 15, !Rigger +3, !Rigger good.')
        value = args.pop(0)
        mode = first
        if first == 'luck':
            mode, value = value.lower(), None
            require(mode in ('good', 'bad'), 'Use !Rigger good or !Rigger bad.')
    elif first in ('good', 'bad'):
        mode, value = first, None
    elif NUMBER.fullmatch(first):
        mode, value = ('shift' if first.startswith(('+', '-')) else 'force'), first
    else:
        raise RollError('Use !Rigger 15, !Rigger +3, !Rigger good, !Rigger bad, or !Rigger off. See !Rigger help.')
    if mode in ('force', 'shift'):
        require(isinstance(value, str) and NUMBER.fullmatch(value), 'Use a whole number, such as 15 or -2.')
        value = int(value)
        require(abs(value) <= MAX_VALUE, 'That number is too large; use a value within ±200 billion.')
    if mode == 'face':
        require(1 <= len(value) <= 40 and not any(ord(c) < 32 for c in value), 'Use a text face of 1–40 characters, with quotes for spaces.')
    require(len(args) <= 1, 'Give only one optional target: @User or their user ID.')
    target = None
    if args:
        match = TARGET.fullmatch(args[0])
        require(match and 0 < int(match[1] or match[2]) < 2**64, 'The target must be @User or a positive Discord user ID.')
        target = str(int(match[1] or match[2]))
    return 'set', {'mode': mode, 'value': value, 'target': target, 'last': None}


def describe(setting):
    mode, value = setting['mode'], setting['value']
    if mode == 'off':
        return 'Rigger is off. Rolls are normal.'
    label = {'force': f'Next final total: {value}', 'shift': f'Next total shift: {value:+d}' if mode == 'shift' else '',
             'face': f'Next text face: {value}', 'good': 'Good luck until switched off', 'bad': 'Bad luck until switched off'}[mode]
    return label + '\nTarget: ' + (f"user {setting['target']} in every server." if setting['target'] else 'anyone in any server.')
