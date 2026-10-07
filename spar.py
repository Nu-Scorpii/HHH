"""Friendly best-of-three sparring, including cost-free tie rerolls."""

from .core import operation
from .rules import STATS, clean, require


class Spar:
    @operation
    def spar_start(self, c, *, opponent):
        c.quiet()
        other = c.hero(opponent)
        require(str(opponent) != c.uid, 'Choose another player.')
        require(c.hero()['health'] > 0 and other['health'] > 0, 'Both students must be conscious.')
        c.state['spar'] = {'players': [c.uid, str(opponent)], 'joined': False,
                           'scores': {c.uid: 0, str(opponent): 0}, 'exchange': 1, 'rolls': {}, 'paid': {}}
        return {'text': f"Spar invitation for {other['hero_name']}. They must /spar join to agree. Best of three exchanges; no Health damage or Plus Ultra."}

    @operation
    def spar_join(self, c):
        s = c.state['spar']
        require(s and c.uid == s['players'][1] and not s['joined'], 'There is no new spar invitation for you.')
        s['joined'] = True
        return {'text': 'Spar accepted. Each player uses /spar roll once per exchange.'}

    @operation
    def spar_roll(self, c, *, stat, method, enhanced=False, edge=False, pressure=False, talent=False, prep=False):
        s = c.state['spar']
        require(s and s['joined'] and c.uid in s['players'], 'Join an agreed spar first.')
        require(c.uid not in s['rolls'], 'You have already rolled this exchange. Wait for your opponent.')
        h = c.hero()
        require(stat in STATS, 'Choose a listed stat.')
        method = clean(method, 500)
        self.expire_help(c)
        if c.uid in s['paid']:
            saved = s['paid'][c.uid]
            require(stat == saved['stat'], 'Tie rerolls use the same stat and declared bonuses; no new costs.')
            edge, pressure = saved['edge'], saved['pressure']
        else:
            if enhanced:
                require(h['energy'] >= 1, 'The enhanced spar approach needs 1 Energy.')
                h['energy'] -= 1
                edge = True
            edge, pressure, _ = self.bonuses(c, h, stat=stat, scope='spar', edge=edge, pressure=pressure,
                                           talent=talent, prep=prep, signature=False, rescue=False, help_task='spar')
            s['paid'][c.uid] = {'stat': stat, 'edge': edge, 'pressure': pressure}
        roll = self.private.stat(c.actor.guild_id, c.uid, 'spar', stat, h['stats'][stat], edge, pressure, self.rng)
        s['rolls'][c.uid] = roll
        messages = [f"{h['hero_name']}: {method}. Kept {roll['kept']}."]
        if len(s['rolls']) == 2:
            first, second = s['players']
            a, b = s['rolls'][first]['kept'], s['rolls'][second]['kept']
            if a == b:
                s['rolls'] = {}
                messages.append('Exact tie. Reroll with the same stat and bonuses, paying no costs again.')
            else:
                winner = first if a > b else second
                s['scores'][winner] += 1
                messages.append(f"{c.hero(winner)['hero_name']} wins exchange {s['exchange']}. Score {s['scores'][first]}–{s['scores'][second]}.")
                if s['scores'][winner] == 2:
                    messages.append(f"{c.hero(winner)['hero_name']} wins the spar. Participation rewards are the same for both students.")
                    c.state['spar'] = None
                else:
                    s['exchange'] += 1
                    s['rolls'], s['paid'] = {}, {}
        return {'title': 'Friendly spar', 'text': '\n'.join(messages), 'roll': roll}

    @operation(pending=True)
    def spar_status(self, c):
        s = c.state['spar']
        require(s, 'No spar is active.')
        return {'title': 'Friendly spar', 'text': f"Exchange {s['exchange']} · {'accepted' if s['joined'] else 'invitation pending'}\n" +
                '\n'.join(f"{c.hero(u)['hero_name']}: {s['scores'][u]} win(s); {'rolled' if u in s['rolls'] else 'waiting'}" for u in s['players'])}

    @operation
    def spar_cancel(self, c):
        s = c.state['spar']
        require(s and (c.uid in s['players'] or c.gm), 'Only a participant or GM can cancel this spar.')
        c.state['spar'] = None
        return {'text': 'Spar cancelled. Previously spent costs are kept.'}
