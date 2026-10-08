"""Regenerate the public slash reference from the actual command definitions."""

from pathlib import Path
import discord
from ua_bot.commands import MISSING, SPECS


def main():
    types = {str:'text',int:'integer',bool:'true/false',discord.Member:'player',discord.Role:'role'}
    lines = ['# Public slash-command reference','',
             f'The bot provides {len(SPECS)} slash commands in 8 main menus. Start with /help; you only need a few commands for everyday play. Use them inside your game server. Discord presents arguments as selectable fields.','',
             'Commands described as GM require the creator or configured GM role. `/gm config` requires the creator. Errors and personal sheets/help are private where appropriate; battle actions and official changes are public.','',
             'The bot handles one waiting tracked roll per server. While it waits, use its Keep / Plus Ultra buttons, `/battle resolve`, `/faq`, sheet/status commands, or permitted GM recovery tools.','']
    group = None
    roots = ['help','faq','hero','roll','check','battle','spar','gm']
    for spec in sorted(SPECS, key=lambda s: roots.index(s.path.split()[0])):
        root = spec.path.split()[0]
        if root != group:
            group = root
            lines += [f'## /{root}','']
        lines += [f'### /{spec.path}','',spec.description+'.','']
        if spec.options:
            lines += ['| Argument | Required/default | Type or choices | Meaning |',
                      '|---|---|---|---|']
            for o in sorted(spec.options,key=lambda x:x.default is not MISSING):
                default = 'Required' if o.default is MISSING else 'Optional; empty' if o.default in ['',None] else f'Default: `{str(o.default).lower() if isinstance(o.default,bool) else o.default}`'
                values = ', '.join('`'+str(v)+'`' for v in o.choices) if o.choices else types.get(o.annotation,'text')
                description = o.description.replace('|','\\|').replace('\n',' ')
                lines.append(f'| `{o.name}` | {default} | {values} | {description} |')
            lines.append('')
        else:
            lines += ['No arguments.','']
        if spec.special in {'create','edit','quirk'}:
            lines += ['Opens a guided form; submit that form to save.','']
        if spec.private:
            lines += ['Response is private by default.','']
    lines += ['## Values and limits','',
              '- Core stat dice are d6, d8, d10, and d12; starting assignment is d10, d8, d8, d6.',
              '- /hero roll randomly assigns those four starting dice once. It saves the assignment before creation, applies it to a draft, and shows that same saved result on repeat. It does not roll random Health or Energy. /hero stats remains available for manual assignment.',
              '- Hero Health is 0–6; Energy is 0–3. Zero Health means Down.',
              '- Custom dice: 1–1,000,000,000 numbered sides; up to 100 dice and 20 expression terms per command.',
              '- /roll defaults to 1d20. Its bonus field is a whole number within ±1 billion and is added once to the total, alongside any expression modifiers.',
              '- Per-roll custom faces use JSON arrays of 1–1000 integers or text labels. Example: `/roll dice:1d[custom] faces:["sun","rain","rain","storm"]`. Repeated faces add weight. Integers may be negative, zero, or positive within ±1 billion; labels have 1–40 characters. Faces are not saved.',
              '- Previously saved named dice remain usable with `/roll dice:1d[name]`. No dice-create/list/remove slash commands are registered.',
              '- Keep-high/low requires one positive numeric dice pool; modifiers and bonus points are added after choosing the kept die. Dice containing any text faces cannot use keep-high/low, subtraction, numeric modifiers, or bonus points. Text results have no numeric total.',
              '- /roll can be used before character creation or while a tracked roll waits. It does not spend resources or apply tracked game effects.',
              '- /hero notes holds up to 20 names with values up to 120 characters. These are manual notes/counters. Leave the value blank to delete a note. The short sheet previews three notes; details:true shows all of them.',
              '- A battle supports up to 20 participants, 25 zones, 25 enemies, and 20 progress objectives. IDs for zones/objectives use up to 32 letters, digits, underscores, or hyphens.',
              '- Enemy Health corrections: 0–10000; damage: 0–20; action count: 1 or 2. Objective/Danger goals: 1–100.',
              '- Weekly reset: weekday 0=Monday through 6=Sunday; local hour 0–23. Use a timezone name such as America/New_York.',
              '- /hero build combines starting choices and prepared loadouts. Established heroes may select only learned and GM-approved options. Omitted fields keep their current choices. item:none removes a prepared item. Changing choices never refreshes spent uses.',
              '- A hero’s first battle move or action starts the turn automatically. Another hero must end their turn before yours starts. /battle end can also pass an unused turn.',
              '- Resource used flags accept 0 for available and 1 for spent. Training corrections accept 0–10000.',
              '- /faq searches written answers, browses topics, or accepts an exact FAQ ID. Replies are private unless share:true is selected. It is available before character creation and while a roll waits.',
              '- GMs can save up to 50 custom FAQs per server with /gm faq-add; using an existing custom ID updates it. Questions are 1–150 characters, answers 1–2000, and IDs are up to 32 characters. /gm faq-remove removes custom answers; core rule IDs are protected.',
              '', 'See the player handbook for the complete rules and the GM guide for setup and examples.','']
    output = Path(__file__).resolve().parent/'docs'/'COMMAND_REFERENCE.md'
    output.write_text('\n'.join(lines),encoding='utf-8')
    print(f'Generated public reference for {len(SPECS)} commands.')


if __name__ == '__main__':
    main()
