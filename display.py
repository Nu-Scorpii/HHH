"""Plain Discord Markdown. No private-control state is passed to this module."""

import discord
from .rules import MOVES, TALENTS

MESSAGE_LIMIT = 2000


def safe(value):
    return discord.utils.escape_markdown(discord.utils.escape_mentions(str(value)))


def short(value, limit=140):
    text = ' '.join(str(value).split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def length(text):
    # This conservative budget also fits clients which count UTF-16 code units.
    return len(str(text).encode('utf-16-le')) // 2


def chunks(text, size=MESSAGE_LIMIT):
    text = str(text)
    while length(text) > size:
        cut, used = 0, 0
        for char in text:
            width = 2 if ord(char) > 0xffff else 1
            if used + width > size:
                break
            cut += 1
            used += width
        newline = text.rfind('\n', 0, cut + 1)
        if newline > 0:
            cut = newline
        while cut > 0 and text[cut - 1] == '\\':
            cut -= 1
        if cut == 0:
            cut = 1
        yield text[:cut]
        text = text[cut:].lstrip('\n')
    if text:
        yield text


def heading(title, icon='✅'):
    return f'{icon} **{safe(short(title))}**'


def roll_values(values):
    # Text faces stay escaped prose; supplied backticks never open code spans.
    return ' · '.join(f'`{v}`' if type(v) is int else safe(short(v, 40)) for v in values)


def dice_text(dice):
    pools = [g for g in dice['groups'] if 'die' in g]
    lines = []
    for group in pools:
        label = 'Rolls' if len(pools) == 1 and group['sign'] > 0 else (
            ('− ' if group['sign'] < 0 else '') + f"{len(group['rolls'])}{group['die']}")
        for offset in range(0, len(group['rolls']), 10):
            prefix = label if offset == 0 else 'More rolls'
            lines.append(f"{prefix}: {roll_values(group['rolls'][offset:offset + 10])}")
        if group['kept'] is not None:
            choice = 'lowest' if dice.get('keep') == 'low' else 'highest'
            lines.append(f"Kept ({choice}): `{group['kept']}`")
    modifiers = [g['modifier'] for g in dice['groups'] if 'modifier' in g]
    if modifiers:
        lines.append(f"Modifier: `{sum(modifiers):+d}`")
    if dice.get('bonus'):
        lines.append(f"Bonus: `{dice['bonus']:+d}`")
    if dice['total'] is not None:
        lines += [f"**Total: {dice['total']}**"]
    return '\n'.join(lines)


def hero_details(h, result):
    q = h['quirk'] or {}
    lines = [f"{safe(h['name'])} · Age {h['age']} · {'Approved' if h['approved'] else 'Draft'}", '',
             '**Resources**',
             f"❤️ Health: `{h['health']}/6` · ⚡ Energy: `{h['energy']}/3`",
             f"Plus Ultra: **{'used' if h['plus_used'] else 'ready'}**", '',
             '**Stats**', ' · '.join(f"{s.title()}: `d{d}`" for s, d in h['stats'].items()), '',
             '**Student**', f"Goal: {safe(h['goal'])}", f"Team connection: {safe(h['cooperation'])}", '',
             f"**Quirk: {safe(q.get('name', 'Not written yet'))}**", safe(q.get('ability', '')),
             f"Ordinary uses: {safe(q.get('ordinary', ''))}", f"Reach: {safe(q.get('reach', 'not chosen'))}",
             f"Cannot: {safe(q.get('cannot', ''))}", f"Limits: {safe(q.get('limits', ''))}", '', '**Prepared moves**']
    for move in h['moves']:
        card = MOVES[move]
        lines.append(f"• **{safe(h['move_names'].get(move, card['name']))}** · `{card['cost']} Energy`\n{card['name']}: {card['rule']}")
    lines += ['', '**Loadout**',
              f"Talent: **{TALENTS[h['talent']][0]}** · {'used' if h['talent_used'] else 'ready'}",
              f"Item: **{safe((h['item'] or 'none').replace('_', ' ').title())}** · {'used' if h['item_used'] else 'ready'}",
              f"Ordinary gear: {safe(h['gear'])}", '', '**Growth & preparation**',
              f"Training: `{h['training']}` stored · `{result.get('weekly_training', '?')}/2` this week",
              f"Shared stat increases: `{h['increases_applied']}` applied · `{result.get('pending_increases', '?')}` waiting",
              f"Prep: {safe(h['prep']['theme']) if h['prep'] else 'none'}"]
    if h.get('prep_offer'):
        lines.append(f"New Prep choice: {safe(h['prep_offer']['theme'])}. Use /hero prep to choose.")
    for field, label in [('known_moves', 'Known moves'), ('known_talents', 'Known Talents'), ('known_items', 'Known items')]:
        lines.append(f"{label}: {safe(', '.join(h[field]).replace('_', ' ')) or 'none'}")
    if h['unlock_requests']:
        lines.append('Pending unlocks: ' + safe(', '.join(x['option'] for x in h['unlock_requests'])))
    lines += ['', '**Scene & battle**',
              f"Healing received this fight: {'yes' if h['healed'] else 'no'} · Down cheer: {'used' if h['cheered'] else 'ready'}"]
    if h['help']:
        lines.append(f"Help: {safe(h['help']['task'])}, from user {safe(h['help']['source'])}; expires at the helper's next turn.")
    if h['guard']:
        lines.append(f"Guard: from user {safe(h['guard']['source'])}; expires at the guard's next turn.")
    if h['trackers']:
        lines += ['', '**Personal trackers**']
        lines += [f"• **{safe(k)}:** {safe(v)}" for k, v in h['trackers'].items()]
    return '\n'.join(lines)


def hero_text(h, result):
    if result.get('details'):
        return hero_details(h, result)
    q = h['quirk'] or {}
    lines = [f"{safe(h['name'])} · {'Ready' if h['approved'] else 'Draft'}",
             f"❤️ **{h['health']}/6** Health · ⚡ **{h['energy']}/3** Energy · Plus Ultra: {'used' if h['plus_used'] else 'ready'}", '',
             ' · '.join(f"**{s.title()}** `d{d}`" for s,d in h['stats'].items()), '',
             f"**Quirk:** {safe(q.get('name', 'Not written yet'))}", safe(short(q.get('ability', ''), 160))]
    if q:
        lines += [f"Limit: {safe(short(q['limits'], 120))}", f"Cannot: {safe(short(q['cannot'], 120))} · Reach: {safe(q['reach'])}"]
    lines += ['', '**Moves:** ' + ' · '.join(f"{safe(h['move_names'].get(m,MOVES[m]['name']))} ({MOVES[m]['cost']} Energy)" for m in h['moves']),
              f"**Talent:** {TALENTS[h['talent']][0]} ({'used' if h['talent_used'] else 'ready'})",
              f"**Item:** {safe((h['item'] or 'none').replace('_',' ').title())} ({'used' if h['item_used'] else 'ready'})",
              f"**Training:** {h['training']} · **Prep:** {safe(short(h['prep']['theme'],60)) if h['prep'] else 'none'}"]
    if result.get('pending_increases'):
        lines.append(f"{result['pending_increases']} stat increase(s) waiting: /hero upgrade")
    if h.get('prep_offer'):
        lines.append('New Prep waiting: /hero prep')
    if h['help'] or h['guard']:
        lines.append('Active: ' + ' · '.join(label for field,label in [('help','Help'),('guard','Guard')] if h[field]))
    if h['trackers']:
        notes = list(h['trackers'].items())
        lines += ['', '**Notes**'] + [f"{safe(k)}: {safe(short(v, 80))}" for k,v in notes[:3]]
        if len(notes) > 3:
            lines.append(f'{len(notes) - 3} more in the full card.')
    lines += ['', '/hero sheet details:true for the full card.']
    return '\n'.join(line for line in lines if line is not None)


def battle_opening(result, *, compact=False):
    b, heroes = result['battle'], result['heroes']
    name = lambda uid: safe(short(heroes.get(uid, {}).get('hero_name', uid), 24 if compact else 80))
    lines = [f"**Round {b['round']} · {b['phase'].title()} phase**"]
    if b['active']:
        budget = b['budget']
        lines += [f"Turn: **{name(b['active'])}**",
                  f"Action: **{'used' if budget['action'] else 'ready'}** · Move: **{'used' if budget['move'] else 'ready'}** · Signature: **{'used' if budget['signature'] else 'ready'}**"]
    if result.get('pending_user'):
        lines.append(f"🎲 Waiting for **{name(result['pending_user'])}** · /battle resolve")
    if b['incoming']:
        attack = b['incoming']
        lines += ['', '**Incoming attack**', safe(short(attack['description'], 120) if compact else attack['description']),
                  'Defenses waiting: ' + (', '.join(name(u) for u in attack['targets'] if u not in attack['results']) or 'none')]
    if b['bonus_moves']:
        lines.append('Bonus moves waiting: ' + ', '.join(name(u) for u in b['bonus_moves']))
    if b['danger']:
        d = b['danger']
        lines.append(f"⚠️ **{safe(short(d['name'], 40) if compact else d['name'])}: {d['progress']}/{d['goal']}** · {'active' if d['active'] else 'stopped'}")
        if not compact:
            lines.append('Consequence: ' + safe(d['consequence']))
    return lines


def battle_text(result):
    b, heroes = result['battle'], result['heroes']
    lines = battle_opening(result) + ['', '**Heroes**']
    for uid, h in heroes.items():
        marks = ['Down'] if h['health'] == 0 else []
        if uid in b['acted']:
            marks.append('turn ended')
        if h['help']:
            marks.append('Help: ' + safe(h['help']['task']))
        if h['guard']:
            marks.append('Guard')
        lines.append(f"• **{safe(h['hero_name'])}** · {safe(b['positions'][uid])} · HP `{h['health']}/6` · Energy `{h['energy']}/3`" + (' · ' + ', '.join(marks) if marks else ''))
    lines += ['', '**Foes & intentions**']
    for key, enemy in b['enemies'].items():
        lines.append(f"• **{safe(enemy['name'])}** (`{safe(key)}`) · {safe(enemy['zone'])} · HP `{enemy['health']}/{enemy['maximum']}`\nDamage `{enemy['damage']}` · Actions `{enemy['used']}/{enemy['actions']}` · {safe(', '.join(enemy['traits'])) or 'no traits'}" + (f" · Capture `{enemy['capture']}`" if enemy['capture'] else ''))
        if enemy['health']:
            lines.append('Intention: ' + safe(enemy['intention']))
    if b['objectives']:
        lines += ['', '**Objectives**']
        for key, objective in b['objectives'].items():
            lines.append(f"• **{safe(objective['name'])}** (`{safe(key)}`): `{objective['progress']}/{objective['goal']}`" + (f" · requires {safe(', '.join(objective['requires']))}" if objective['requires'] else ''))
    lines += ['', '**Zones & routes**']
    for zone, links in b['zones'].items():
        lines.append(f"• **{safe(zone)}:** " + (', '.join(safe(other) + (' (blocked)' if not clear else '') for other, clear in links.items()) or 'no connections'))
    if b['shields']:
        lines.append('Shields: ' + ', '.join(safe(x['zone']) for x in b['shields'].values()))
    if b['phase'] == 'heroes':
        lines += ['', '**Your turn:** move + one action → Keep or Plus Ultra → /battle end']
    elif b['phase'] == 'enemies':
        lines += ['', '**Next:** resolve enemy actions and defenses → /gm battle phase next']
    return '\n'.join(lines)


def result_text(result):
    if 'hero' in result:
        text = hero_text(result['hero'], result)
        return text + ('\n\n' + safe(result['text']) if result.get('text') else '')
    if result.get('type') == 'battle':
        return battle_text(result)
    if result.get('type') == 'dice':
        return dice_text(result['dice'])
    if result.get('type') == 'creation':
        return ('\n'.join(f"**{stat.title()}:** `d{die}`" for stat,die in result['stats'].items())
                + '\nHealth: **6** · Energy: **3**\n\n' + safe(result['text']))
    if result.get('faq_entries'):
        return '\n\n'.join(f"**{safe(e['question'])}**\n{safe(e['answer'])}" for e in result['faq_entries'])
    lines = []
    if result.get('roll'):
        roll = result['roll']
        grade = 'Miss' if roll['kept'] <= 3 else 'Success' if roll['kept'] <= 7 else 'Big success'
        mode = '' if roll['mode'] == 'normal' else ' · ' + roll['mode'].title()
        lines += [f"`d{roll['die']}`{mode} · " + roll_values(roll['rolls']), f"**{roll['kept']} · {grade}**"]
    if result.get('method') and result['method'] != 'Agreed action.':
        lines += ['> ' + safe(result['method'])]
    lines += ['', safe(result.get('text', 'Done.'))]
    return '\n'.join(lines).strip()


def messages(result, *, display_name=None):
    kind = result.get('type')
    icon = result.get('icon', '✅')
    title = result.get('title', 'Done')
    if kind == 'dice':
        title = f"{short(display_name or 'Player', 80)} · {short(result['dice']['expression'], 500)}"
        icon = '🎲'
    elif 'hero' in result:
        icon = '🦸'
    elif kind == 'battle':
        icon = '⚔️'
    elif result.get('roll') or kind == 'creation':
        icon = '🎲'
    elif title.startswith('FAQ') or result.get('faq_entries'):
        icon = '❓'
    elif title in ('Player help', 'Game rules', 'Player handbook'):
        icon = '📖'
    first = f'{icon} **{safe(title)}**' if kind == 'dice' else heading(title, icon)
    continued = heading('Roll continued' if kind == 'dice' else short(title) + ' · continued', icon)
    budget = MESSAGE_LIMIT - max(length(first), length(continued)) - 2
    return [(first if index == 0 else continued) + '\n\n' + piece
            for index, piece in enumerate(chunks(result_text(result) or 'Done.', budget))]


def battle_panel(result):
    """One live message: urgent choices first, then a bounded roster summary."""
    if result.get('type') != 'battle':
        return messages(result)[0]
    b, heroes = result['battle'], result['heroes']
    lines = [heading('Battle · ' + result['title'], '⚔️'), ''] + battle_opening(result, compact=True)
    lines += ['', '**Heroes**']
    for uid, h in heroes.items():
        mark = ' · Down' if h['health'] == 0 else ' · done' if uid in b['acted'] else ''
        lines.append(f"• **{safe(short(h['hero_name'], 24))}** · HP `{h['health']}/6` · E `{h['energy']}/3` · {safe(short(b['positions'][uid], 16))}{mark}")
    lines += ['', '**Foes**']
    lines += [f"• `{safe(key)}` **{safe(short(e['name'], 24))}** · HP `{e['health']}/{e['maximum']}`"
              for key, e in b['enemies'].items()]
    if b['objectives']:
        lines += ['', '**Objectives**']
        lines += [f"• **{safe(short(o['name'], 32))}** · `{o['progress']}/{o['goal']}`" for o in b['objectives'].values()]
    footer = '\n\nFull board & intentions: /battle status'
    output = []
    for line in lines:
        if length('\n'.join(output + [line]) + footer) > MESSAGE_LIMIT:
            output.append('… More on /battle status')
            break
        output.append(line)
    while length('\n'.join(output) + footer) > MESSAGE_LIMIT:
        output.pop(-2 if output[-1].startswith('…') else -1)
    return '\n'.join(output) + footer
