"""Player-facing text only. Private-control state is never passed here."""

import discord
from .rules import ITEMS, MOVES, TALENTS


def safe(value):
    return discord.utils.escape_markdown(discord.utils.escape_mentions(str(value)))


def chunks(text, size=3500):
    text = str(text)
    while len(text) > size:
        cut = text.rfind('\n', 0, size)
        if cut < size // 2:
            cut = size
        yield text[:cut]
        text = text[cut:].lstrip('\n')
    if text:
        yield text


def hero_text(h, result):
    q = h['quirk'] or {}
    lines = [f"**{safe(h['hero_name'])}** · {safe(h['name'])} · age {h['age']} · {'Approved' if h['approved'] else 'Draft'}",
             ' · '.join(f"{s.title()} d{d}" for s, d in h['stats'].items()),
             f"**Health {h['health']}/6 · Energy {h['energy']}/3 · Plus Ultra {'used' if h['plus_used'] else 'ready'}**",
             f"Goal: {safe(h['goal'])}", f"Team connection: {safe(h['cooperation'])}",
             f"**Quirk: {safe(q.get('name', 'Not written yet'))}**", safe(q.get('ability', '')),
             f"Ordinary uses: {safe(q.get('ordinary', ''))}", f"Reach: {q.get('reach', 'not chosen')}",
             f"Cannot: {safe(q.get('cannot', ''))}", f"Limits: {safe(q.get('limits', ''))}", '**Prepared moves**']
    for m in h['moves']:
        lines.append(f"{safe(h['move_names'].get(m, MOVES[m]['name']))} ({MOVES[m]['name']}, {MOVES[m]['cost']} Energy): {MOVES[m]['rule']}")
    lines += [f"**Talent:** {TALENTS[h['talent']][0]} · {'used' if h['talent_used'] else 'ready'}",
              f"**Item:** {h['item'] or 'none'} · {'used' if h['item_used'] else 'ready'}",
              f"Ordinary gear: {safe(h['gear'])}", f"Training: {h['training']} stored; {result.get('weekly_training', '?')}/2 this week.",
              f"Shared increases applied: {h['increases_applied']}; {result.get('pending_increases', '?')} waiting.",
              f"Healing received this fight: {h['healed']} · Down cheer used: {h['cheered']}",
              f"Prep: {safe(h['prep']['theme']) if h['prep'] else 'none'}"]
    if h.get('prep_offer'):
        lines.append(f"New Prep choice: {safe(h['prep_offer']['theme'])}. /hero prep chooses which to keep.")
    for field, label in [('known_moves', 'Known moves'), ('known_talents', 'Known Talents'), ('known_items', 'Known items')]:
        lines.append(f"{label}: {', '.join(h[field]) or 'none'}")
    if h['unlock_requests']:
        lines.append('Pending unlock requests: ' + ', '.join(x['option'] for x in h['unlock_requests']))
    if h['help']:
        lines.append(f"Help: {safe(h['help']['task'])}, from user {h['help']['source']}; expires at helper's next turn.")
    if h['guard']:
        lines.append(f"Guard: from user {h['guard']['source']}; expires at guard's next turn.")
    lines += [f"{safe(k)}: {safe(v)}" for k, v in h['trackers'].items()]
    return '\n'.join(lines)


def battle_text(result):
    b, heroes = result['battle'], result['heroes']
    lines = [f"**Round {b['round']} · {b['phase'].title()} phase**"]
    if b['active']:
        budget = b['budget']
        lines.append(f"Active: {safe(heroes[b['active']]['hero_name'])} · action {'used' if budget['action'] else 'ready'} · free move {'used' if budget['move'] else 'ready'} · signature {'used' if budget['signature'] else 'ready'}")
    if result.get('pending_user'):
        lines.append(f"Waiting roll: {safe(heroes.get(result['pending_user'], {}).get('hero_name', result['pending_user']))} · /pending or /resolve")
    lines.append('**Zones**')
    for z, links in b['zones'].items():
        lines.append(f"{z}: " + (', '.join(f"{o}{' (blocked)' if not clear else ''}" for o, clear in links.items()) or 'no connections'))
    lines.append('**Heroes**')
    for uid, h in heroes.items():
        marks = ['Down'] if h['health'] == 0 else []
        if uid in b['acted']:
            marks.append('turn ended')
        if h['help']:
            marks.append('Help: ' + h['help']['task'])
        if h['guard']:
            marks.append('Guard')
        lines.append(f"{safe(h['hero_name'])} ({uid}) · {b['positions'][uid]} · HP {h['health']}/6 · E {h['energy']}/3" + (' · ' + ', '.join(marks) if marks else ''))
    lines.append('**Foes and intentions**')
    for key, e in b['enemies'].items():
        lines.append(f"{key}: {safe(e['name'])} · {e['zone']} · HP {e['health']}/{e['maximum']} · damage {e['damage']} · actions {e['used']}/{e['actions']} · {', '.join(e['traits']) or 'no traits'}" + (f" · Capture {e['capture']}" if e['capture'] else ''))
        if e['health']:
            lines.append('Intention: ' + safe(e['intention']))
    if b['objectives']:
        lines.append('**Objectives**')
        for key, o in b['objectives'].items():
            lines.append(f"{key}: {safe(o['name'])} {o['progress']}/{o['goal']}" + (f" · requires {', '.join(o['requires'])}" if o['requires'] else ''))
    if b['danger']:
        d = b['danger']
        lines.append(f"**Danger:** {safe(d['name'])} {d['progress']}/{d['goal']} · {'active' if d['active'] else 'stopped'}\nConsequence: {safe(d['consequence'])}")
    if b['shields']:
        lines.append('Shields: ' + ', '.join(x['zone'] for x in b['shields'].values()))
    if b['incoming']:
        a = b['incoming']
        lines.append('**Incoming:** ' + safe(a['description']))
        lines.append('Defenses waiting: ' + ', '.join(safe(heroes[u]['hero_name']) for u in a['targets'] if u not in a['results']))
    if b['bonus_moves']:
        lines.append('Bonus movement waiting: ' + ', '.join(safe(heroes[u]['hero_name']) for u in b['bonus_moves']))
    if b['phase'] == 'heroes':
        lines.append('**Next:** /battle turn → move and one action → /resolve if rolling → /battle end. Use /help topic:battle for options.')
    return '\n'.join(lines)


def result_text(result):
    if 'hero' in result:
        text = hero_text(result['hero'], result)
        if result.get('text'):
            text += '\n\n' + safe(result['text'])
        return text
    if result.get('type') == 'battle':
        return battle_text(result)
    if result.get('type') == 'dice':
        d = result['dice']
        lines = [safe(d['expression'])]
        for g in d['groups']:
            if 'modifier' in g:
                lines.append(f"Modifier: {g['modifier']:+d}")
            else:
                lines.append(f"{'−' if g['sign'] < 0 else ''}{g['die']}: {safe(', '.join(str(v) for v in g['rolls']))}" + (f" → keep {g['kept']}" if g['kept'] is not None else ''))
        if d['total'] is not None:
            lines.append(f"**Total: {d['total']}**")
        return '\n'.join(lines)
    lines = []
    if result.get('roll'):
        r = result['roll']
        lines.append(f"d{r['die']} · {r['mode']} · rolled {', '.join(str(x) for x in r['rolls'])} · **kept {r['kept']}**")
    if result.get('method'):
        lines.append(safe(result['method']))
    lines.append(safe(result.get('text', 'Done.')))
    return '\n\n'.join(lines)


def embeds(result):
    title = safe(result.get('title', 'UA Hero College'))[:230]
    return [discord.Embed(title=title if i == 0 else title + ' · continued', description=part,
                          colour=0x253E55) for i, part in enumerate(chunks(result_text(result)))]
