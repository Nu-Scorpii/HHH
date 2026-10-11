"""Small, plain Discord messages. Public output receives only the dice result."""

import discord

LIMIT = 2000


def safe(value):
    return discord.utils.escape_markdown(discord.utils.escape_mentions(str(value)))


def length(text):
    return len(text.encode('utf-16-le')) // 2


def chunks(text, budget=LIMIT):
    while length(text) > budget:
        used, cut = 0, 0
        for char in text:
            width = 2 if ord(char) > 0xffff else 1
            if used + width > budget:
                break
            used += width
            cut += 1
        newline = text.rfind('\n', 0, cut + 1)
        if newline > 0:
            cut = newline
        # Avoid leaving a Markdown escape at the end of a message.
        while cut > 0 and text[cut - 1] == '\\':
            cut -= 1
        if cut == 0:
            cut = 1
        yield text[:cut]
        text = text[cut:].lstrip('\n')
    if text:
        yield text


def roll_messages(result, display_name='Player'):
    name = ' '.join(str(display_name).split())[:80] or 'Player'
    heading = f"🎲 **{safe(name)} rolled {safe(result['expression'])}**"
    continued = '🎲 **Roll continued**'
    pools = [group for group in result['groups'] if 'rolls' in group]
    lines = []
    for group in pools:
        label = 'Rolls' if len(pools) == 1 and group['sign'] == 1 else (
            ('− ' if group['sign'] < 0 else '') + f"{len(group['rolls'])}{group['die']}")
        for offset in range(0, len(group['rolls']), 10):
            values = group['rolls'][offset:offset + 10]
            shown = ' · '.join(f'`{value}`' if type(value) is int else safe(value) for value in values)
            lines.append(f"{label if offset == 0 else 'More rolls'}: {shown}")
        if group['kept'] is not None:
            lines.append(f"Kept ({'highest' if result['keep'] == 'high' else 'lowest'}): `{group['kept']}`")
    modifiers = [group['modifier'] for group in result['groups'] if 'modifier' in group]
    if modifiers:
        lines.append(f'Modifier: `{sum(modifiers):+d}`')
    if result['bonus']:
        lines.append(f"Bonus: `{result['bonus']:+d}`")
    if result['total'] is not None:
        lines.extend(('', f"**Total: {result['total']}**"))
    budget = LIMIT - max(length(heading), length(continued)) - 2
    return [(heading if index == 0 else continued) + '\n\n' + part
            for index, part in enumerate(chunks('\n'.join(lines), budget))]


def private_messages(text):
    return ['🔒 **Creator controls**\n\n' + part for part in chunks(safe(text), 1900)]
