"""Two creator-only settings: lasting luck and one next-roll override."""

import json
import re
import shlex
from .dice import Die, parse, roll_expression, stat_roll
from .rigging_math import bounds, expression_result, numeric, stat_result, variables, clamp
from .rules import GameError, require

HELP = '''DM commands — work in every server, with no server ID:
!Rigger luck good — lasting better luck
!Rigger luck bad — lasting worse luck
!Rigger luck normal — turn luck off
!Rigger force 15 — set the next numeric result to 15
!Rigger shift +3 — raise the next numeric result by 3
!Rigger shift -2 — lower the next numeric result by 2
!Rigger status — see your settings and last change
!Rigger off — reset everything

Add a player mention or user ID after the value to affect only them.
Example: !Rigger force 8 <@PLAYER_ID>
Shortcut: !Rigger 15 is the same as !Rigger force 15.
A new force/shift replaces the previous one. Each lasts for ONE matching numeric roll.
Numbers outside the range are limited to legal results. Custom dice may use a nearby total.
Text dice and character stat assignment are not changed.'''


def defaults():
    return {'luck': 0, 'luck_target': 'any', 'next': None, 'last': None}


class PrivateRolls:
    def __init__(self, store, owner_id, clock):
        self.store, self.owner_id, self.clock = store, int(owner_id), clock
        with store.transaction() as db:
            # Old queues/audits are retained for recovery, but never executed.
            db.execute('CREATE TABLE IF NOT EXISTS simple_controls (creator TEXT PRIMARY KEY, state TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS private_settings (creator TEXT PRIMARY KEY, guild TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO simple_controls VALUES(?,?)', (str(self.owner_id), json.dumps(defaults())))

    def load(self):
        return json.loads(self.store.db.execute('SELECT state FROM simple_controls WHERE creator=?', (str(self.owner_id),)).fetchone()[0])

    def save(self, state):
        self.store.db.execute('UPDATE simple_controls SET state=? WHERE creator=?', (json.dumps(state), str(self.owner_id)))

    def target(self, value):
        if value.lower() in {'any', 'all', '*'}:
            return 'any'
        if value.lower() == 'me':
            return str(self.owner_id)
        match = re.fullmatch(r'(?:<@!?(\d+)>|(\d+))', value)
        require(match is not None, 'Add a player mention or user ID, or leave it out for everyone.')
        number = int(next(x for x in match.groups() if x is not None))
        require(0 < number < 2**64, 'Use a valid player ID.')
        return str(number)

    @staticmethod
    def who(target):
        return 'everyone' if target == 'any' else f'player {target}'

    def handle(self, author_id, content, *, is_dm, guild_ids=()):
        content = content.strip()
        if not is_dm or int(author_id) != self.owner_id or not re.match(r'^!rigger(?=\s|$)', content, re.I):
            return None
        try:
            words = shlex.split(content.replace('−', '-'))
            if not words or words[0].casefold() != '!rigger':
                return None
            args = words[1:]
            if not args or len(args) == 1 and args[0].casefold() == 'help':
                return HELP
            action = args.pop(0).lower()
            if re.fullmatch(r'[+-]?\d+', action):
                args.insert(0, action)
                action = 'force'
            require(action in {'luck', 'force', 'shift', 'status', 'off', 'clear'}, 'Use !Rigger help for the simple commands.')
            with self.store.transaction():
                state = self.load()
                if action in {'off', 'clear'}:
                    require(not args, 'Use !Rigger off without extra arguments.')
                    self.save(defaults())
                    return 'Off. Rolls are normal in every server.'
                if action == 'status':
                    require(not args, 'Use !Rigger status without extra arguments.')
                    luck = {0:'normal', 1:'good', -1:'bad'}[state['luck']]
                    lines = [f"Luck: {luck} for {self.who(state['luck_target'])}."]
                    tweak = state['next']
                    lines.append(f"Next roll: {tweak['mode']} {tweak['value']:+d} for {self.who(tweak['target'])}." if tweak else 'Next roll: no override.')
                    if state['last']:
                        last = state['last']
                        lines.append(f"Last change: {last['natural']} → {last['final']} for player {last['user']}.")
                    return '\n'.join(lines)
                require(1 <= len(args) <= 2, f'Use !Rigger {action} VALUE, optionally followed by one player mention or ID.')
                value, target = args[0], self.target(args[1]) if len(args) == 2 else 'any'
                if action == 'luck':
                    require(value.lower() in {'good','bad','normal','off'}, 'Luck is good, bad, or normal.')
                    state['luck'] = {'good':1, 'bad':-1, 'normal':0, 'off':0}[value.lower()]
                    state['luck_target'] = target if state['luck'] else 'any'
                    reply = f"Luck: {value.lower()} for {self.who(state['luck_target'])}. Lasts until changed or !Rigger off."
                else:
                    amount = int(value)
                    require(abs(amount) <= 10**12, 'Use a whole number within ±1 trillion.')
                    state['next'] = {'mode':action, 'value':amount, 'target':target}
                    reply = f"Next numeric roll: {action} {amount:+d} for {self.who(target)}. One use; replaces the previous override. Dice stay within their legal range."
                self.save(state)
                return reply
        except (GameError, ValueError):
            return 'Could not set that. Use !Rigger help for the short command list.'

    def apply(self, guild, user, natural, draw, score, transform, *, supports_numeric):
        if not supports_numeric:
            return natural
        state = self.load()
        tweak = state['next']
        if tweak and tweak['target'] not in {'any', str(user)}:
            tweak = None
        lucky = state['luck'] and state['luck_target'] in {'any', str(user)}
        result = natural
        # Force wins over luck. A shift happens after any applicable luck.
        if lucky and not (tweak and tweak['mode'] == 'force'):
            choose = max if state['luck'] > 0 else min
            result = choose((natural, draw()), key=score)
        if tweak:
            result = transform(result, tweak['mode'], tweak['value'])
            state['next'] = None
        if lucky or tweak:
            state['last'] = {'natural':score(natural), 'final':score(result), 'user':str(user)}
            self.save(state)
            self.store.db.execute('INSERT INTO rig_audit(guild,target,rule_id,natural,final,created) VALUES(?,?,?,?,?,?)',
                                  (str(guild), str(user), -1, json.dumps(natural), json.dumps(result), self.clock().isoformat()))
        return result

    def stat(self, guild, user, scope, stat, sides, edge, pressure, rng):
        die = Die(sides=sides)
        draw = lambda: stat_roll(sides, edge, pressure, rng)
        def transform(roll, mode, value):
            value = clamp(value, 1, sides) if mode == 'force' else value
            return stat_result(roll, die, mode, str(value))
        return self.apply(guild, user, draw(), draw, lambda r:r['kept'], transform, supports_numeric=True)

    def expression(self, guild, user, expression, custom, keep, rng, *, bonus=0):
        terms = parse(expression, custom)
        draw = lambda: roll_expression(expression, custom, rng, keep, bonus=bonus)
        natural = draw()  # Validate before consuming a setting or drawing extra luck.
        def transform(roll, mode, value):
            if mode == 'force':
                low, high = bounds(roll, terms)
                value = clamp(value, low, high)
                exact = expression_result(roll, terms, mode, str(value))
                if exact is not None:
                    return exact
                return expression_result(roll, terms, 'shift', str(value - roll['total']))
            return expression_result(roll, terms, mode, str(value))
        return self.apply(guild, user, natural, draw, lambda r:r['total'], transform,
                          supports_numeric=numeric([die for die, _ in variables(terms)]))
