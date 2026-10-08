"""Universal creator-only DM controls, absent from public menus and replies."""

import json
import re
import shlex
from datetime import datetime, timezone
from .dice import Die, parse, roll_expression, stat_roll
from .rigging_math import expression_result, numeric, stat_result, variables
from .rules import GameError, require

SCOPES = {'any','dice','check','attack','capture','task','defense','spar','power','speed','wits','heart'}
MAX_VALUE = 10**12

HELP = '''All controls work across every server. Send them in this DM only.

!Rigger luck good — make numeric rolls luckier until turned off
!Rigger luck bad — make numeric rolls unluckier until turned off
!Rigger luck normal — turn off the default luck setting
!Rigger force 15 — force the next possible roll result to 15
!Rigger shift +3 — secretly raise the next result by 3
!Rigger shift -2 — secretly lower the next result by 2
!Rigger shift success — change the next possible result to a success
!Rigger shift up / down — move the next result up or down one available grade

Optional: add a player ID/mention, uses:3, scope:attack, or minutes:30.
Example: !Rigger force 8 <@PLAYER_ID> uses:2 scope:attack
Use uses:always for a lasting setting. Default force/shift: one use within 60 minutes.
Luck also accepts -3 to +3: stronger numbers make the bias stronger; 0 turns it off.
Force controls the kept stat result or final numeric /roll total, including its visible modifiers/bonus.
Dice stay legal, and totals stay consistent. Impossible requests stay queued.
Text faces: !Rigger force "heavy rain". Luck and shifts need entirely numeric dice.

!Rigger status — show all active settings
!Rigger clear [RULE_ID] — clear one rule or all controls
!Rigger audit — show the last ten changes privately
!Rigger next TARGET FACE [COUNT] [SCOPE] [MINUTES] — old face-forcing syntax still works
No server selection is needed. Use counts are shared across servers.'''


class PrivateRolls:
    def __init__(self, store, owner_id, clock):
        self.store, self.owner_id, self.clock = store, int(owner_id), clock
        # Migrate old queues atomically. Keep old selection data for backup compatibility.
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS private_settings (creator TEXT PRIMARY KEY, guild TEXT NOT NULL)')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(rig_rules)')}
            if 'mode' not in columns:
                db.execute("ALTER TABLE rig_rules ADD COLUMN mode TEXT NOT NULL DEFAULT 'face'")
            db.execute("UPDATE rig_rules SET guild='*' WHERE creator=? AND guild<>'*'", (str(self.owner_id),))

    def target(self, value):
        if value.lower() in {'any','all','*'}:
            return 'any'
        if value.lower() == 'me':
            return str(self.owner_id)
        match = re.fullmatch(r'(?:<@!?(\d+)>|(\d+))', value)
        require(match is not None, 'Use a player ID, mention, me, or any.')
        number = int(next(part for part in match.groups() if part is not None))
        require(0 < number < 2**64, 'Use a valid Discord player ID.')
        return str(number)

    def options(self, args, *, luck=False):
        options, seen = {'target':'any','uses':'always' if luck else '1','scope':'any'}, set()
        aliases = {'player':'target','count':'uses'}
        for argument in args:
            split = re.split(r'[:=]', argument, maxsplit=1)
            if len(split) == 2:
                key, value = split
                key = aliases.get(key.lower(), key.lower())
            else:
                key, value = 'target', argument
            require(key in {'target','uses','scope','minutes'} and key not in seen,
                    'Use one player target and optional uses:3, scope:attack, or minutes:30.')
            seen.add(key)
            options[key] = value
        target = self.target(options['target'])
        persistent = options['uses'].lower() in {'always','forever'}
        uses = -1 if persistent else int(options['uses'])
        require(persistent or 1 <= uses <= 100, 'Use uses:1 through uses:100, or uses:always.')
        scope = options['scope'].lower()
        scope = {'roll':'dice','all':'any'}.get(scope, scope)
        require(scope in SCOPES, 'Choose a valid roll scope, such as dice, attack, defense, or power.')
        minutes = int(options['minutes']) if 'minutes' in options else None if uses == -1 else 60
        require(minutes is None or 1 <= minutes <= 1440, 'Use minutes:1 through minutes:1440.')
        expires = self.clock().timestamp() + minutes * 60 if minutes is not None else 0
        return target, uses, scope, expires

    def queue(self, db, mode, outcome, target, uses, scope, expires):
        if mode == 'luck':
            db.execute("DELETE FROM rig_rules WHERE creator=? AND mode='luck' AND target=? AND scope=?",
                       (str(self.owner_id), target, scope))
            if int(outcome) == 0 and target == 'any' and scope == 'any':
                return 'Default luck returned to normal across all servers. Player/scoped settings remain; !Rigger clear resets everything.'
        count = db.execute('SELECT count(*) FROM rig_rules WHERE creator=?', (str(self.owner_id),)).fetchone()[0]
        require(count < 100, 'Keep at most 100 active settings; use !Rigger clear RULE_ID to free a slot.')
        row = db.execute('INSERT INTO rig_rules(guild,target,outcome,scope,remaining,expires,creator,mode) VALUES(?,?,?,?,?,?,?,?)',
                         ('*', target, outcome, scope, uses, expires, str(self.owner_id), mode))
        duration = 'until cleared' if expires == 0 else 'until ' + datetime.fromtimestamp(expires, timezone.utc).isoformat(timespec='minutes')
        return f"Queued rule #{row.lastrowid} across all servers: {mode} {outcome} · {target} · {scope} · {'always' if uses == -1 else str(uses) + ' use(s)'} · {duration}."

    def handle(self, author_id, content, *, is_dm, guild_ids=()):
        # Identity and one-to-one DM context are checked before parsing or replying.
        if not is_dm or int(author_id) != self.owner_id or not content.startswith('!Rigger'):
            return None
        try:
            args = shlex.split(content.replace('−', '-'))
            if not args or args[0] != '!Rigger':
                return None
            args = args[1:]
            if not args or args == ['help']:
                return HELP
            action = args.pop(0).lower()
            if action == 'server':
                return 'Server selection is no longer needed. Controls automatically work across every server the bot joins.'
            with self.store.transaction() as db:
                db.execute('DELETE FROM rig_rules WHERE creator=? AND (remaining=0 OR (expires>0 AND expires<=?))',
                           (str(self.owner_id), self.clock().timestamp()))
                if action in {'force','shift','outcome','luck'}:
                    require(args, f'Use !Rigger {action} VALUE. See !Rigger help for examples.')
                    outcome = args.pop(0)
                    mode = action
                    if action == 'luck':
                        outcome = {'good':'1','bad':'-1','normal':'0','off':'0'}.get(outcome.lower(), outcome)
                        strength = int(outcome)
                        require(-3 <= strength <= 3, 'Luck accepts good, bad, normal, or a number from -3 to +3.')
                        outcome = str(strength)
                    elif action in {'shift','outcome'}:
                        outcome = outcome.lower()
                        if outcome in {'miss','success','big','up','down'}:
                            mode = 'outcome'
                        else:
                            require(action == 'shift', 'Use outcome miss, success, big, up, or down.')
                            amount = int(outcome)
                            require(abs(amount) <= MAX_VALUE, 'Use a whole-number shift within ±1 trillion.')
                            outcome = str(amount)
                    elif outcome.lower() in {'miss','success','big'}:
                        mode, outcome = 'outcome', outcome.lower()
                    elif outcome.lower() in {'min','max'}:
                        outcome = outcome.lower()
                    elif outcome.startswith('face:'):
                        mode, outcome = 'face', outcome[5:]
                        require(1 <= len(outcome) <= 40, 'Use a face with 1–40 characters.')
                    elif re.fullmatch(r'[+-]?\d+', outcome):
                        require(abs(int(outcome)) <= MAX_VALUE, 'Use a whole-number result within ±1 trillion.')
                        outcome = str(int(outcome))
                    else:
                        mode = 'face'
                        require(1 <= len(outcome) <= 40, 'Quote a text face with 1–40 characters.')
                    return self.queue(db, mode, outcome, *self.options(args, luck=action == 'luck'))
                if action == 'next':
                    require(2 <= len(args) <= 5, 'Use !Rigger next TARGET FACE [COUNT] [SCOPE] [MINUTES].')
                    target = self.target(args[0])
                    outcome = args[1]
                    require(1 <= len(outcome) <= 40, 'Use a short face or outcome.')
                    uses = int(args[2]) if len(args) > 2 else 1
                    scope = args[3].lower() if len(args) > 3 else 'any'
                    minutes = int(args[4]) if len(args) > 4 else 60
                    require(1 <= uses <= 100 and 1 <= minutes <= 1440, 'Use 1–100 rolls and 1–1440 minutes.')
                    require(scope in SCOPES, 'Unknown scope.')
                    return self.queue(db, 'face', outcome, target, uses, scope, self.clock().timestamp() + minutes * 60)
                if action == 'clear':
                    require(len(args) <= 1, 'Use !Rigger clear or !Rigger clear RULE_ID.')
                    if args:
                        require(0 < int(args[0]) < 2**63, 'Use a valid positive rule ID from !Rigger status.')
                        db.execute('DELETE FROM rig_rules WHERE creator=? AND id=?', (str(self.owner_id), int(args[0])))
                    else:
                        db.execute('DELETE FROM rig_rules WHERE creator=?', (str(self.owner_id),))
                    return 'Cleared matching controls across all servers.'
                require(not args, f'Use !Rigger {action} without extra arguments.')
                if action == 'status':
                    rows = db.execute('SELECT * FROM rig_rules WHERE creator=? ORDER BY id LIMIT 30', (str(self.owner_id),)).fetchall()
                    return 'No queued rules.' if not rows else 'Active across all servers:\n' + '\n'.join(
                        f"#{r['id']} · {r['mode']} {r['outcome']} · {r['target']} · {r['scope']} · "
                        + ('always' if r['remaining'] == -1 else f"{r['remaining']} left") + ' · '
                        + ('until cleared' if r['expires'] == 0 else 'expires ' + datetime.fromtimestamp(r['expires'], timezone.utc).isoformat(timespec='minutes'))
                        for r in rows)
                if action == 'audit':
                    rows = db.execute('SELECT * FROM rig_audit ORDER BY id DESC LIMIT 10').fetchall()
                    return 'No applied overrides.' if not rows else '\n\n'.join(
                        f"Rule #{r['rule_id']} · server {r['guild']} · player {r['target']} · {r['created']}\n"
                        f"Natural {self.summary(r['natural'])} → final {self.summary(r['final'])}" for r in rows)
                raise GameError('Unknown creator command. Use !Rigger help.')
        except (GameError, ValueError) as exc:
            return f'Could not apply that command: {exc}'

    @staticmethod
    def summary(payload):
        result = json.loads(payload)
        if 'groups' in result:
            values = [str(value) for group in result['groups'] if 'die' in group for value in group['rolls']]
            return ', '.join(values[:8]) + ('…' if len(values) > 8 else '') + f"; total {result['total']}"
        return ', '.join(map(str, result['rolls'])) + f"; kept {result['kept']}"

    def rules(self, guild, user, scope, stat, *, luck=False):
        # A single universal use budget, including servers joined in the future.
        return self.store.db.execute(
            "SELECT * FROM rig_rules WHERE creator=? AND guild IN ('*', ?) AND target IN (?, 'any') "
            "AND scope IN (?, ?, 'any') AND (remaining=-1 OR remaining>0) AND (expires=0 OR expires>?) "
            "AND " + ("mode='luck' " if luck else "mode<>'luck' ") +
            "ORDER BY CASE WHEN target=? THEN 0 ELSE 1 END, " +
            ("CASE WHEN scope='any' THEN 1 ELSE 0 END, " if luck else '') +
            "CASE WHEN remaining=-1 THEN 1 ELSE 0 END, id",
            (str(self.owner_id), str(guild), str(user), scope, stat or scope, self.clock().timestamp(), str(user))).fetchall()

    def record(self, guild, rule, user, natural, final):
        if rule['remaining'] > 0:
            self.store.db.execute('UPDATE rig_rules SET remaining=remaining-1 WHERE id=? AND remaining>0', (rule['id'],))
        self.store.db.execute('INSERT INTO rig_audit(guild,target,rule_id,natural,final,created) VALUES(?,?,?,?,?,?)',
                             (str(guild), str(user), rule['id'], json.dumps(natural), json.dumps(final), self.clock().isoformat()))

    def apply(self, guild, user, scope, stat, natural, transform, draw, score, *, supports_luck):
        rule, prepared = None, None
        for candidate in self.rules(guild, user, scope, stat):
            result = transform(natural, candidate['mode'], candidate['outcome'])
            if result is not None:
                rule, prepared = candidate, result
                break
        # An exact force takes priority without consuming or drawing luck.
        if rule is not None and rule['mode'] in {'force','face'}:
            self.record(guild, rule, user, natural, prepared)
            return prepared
        base = natural
        luck = next(iter(self.rules(guild, user, scope, stat, luck=True)), None) if supports_luck else None
        if luck and int(luck['outcome']) != 0:
            strength = int(luck['outcome'])
            choose = max if strength > 0 else min
            candidates = [natural] + [draw() for _ in range(abs(strength))]
            base = choose(candidates, key=score)
            self.record(guild, luck, user, natural, base)
        elif luck and luck['remaining'] > 0:
            # A targeted normal setting masks the global bias for its use budget.
            self.record(guild, luck, user, natural, base)
        if rule is not None:
            final = transform(base, rule['mode'], rule['outcome'])
            if final is None:
                final = prepared
            self.record(guild, rule, user, base, final)
            return final
        return base

    def stat(self, guild, user, scope, stat, sides, edge, pressure, rng):
        die = Die(sides=sides)
        draw = lambda: stat_roll(sides, edge, pressure, rng)
        natural = draw()
        return self.apply(guild, user, scope, stat, natural,
                          lambda roll, mode, outcome: stat_result(roll, die, mode, outcome),
                          draw, lambda roll: roll['kept'], supports_luck=True)

    def expression(self, guild, user, expression, custom, keep, rng, *, bonus=0):
        terms = parse(expression, custom)
        draw = lambda: roll_expression(expression, custom, rng, keep, bonus=bonus)
        natural = draw()  # Validates all input before any rule or luck is consumed.
        return self.apply(guild, user, 'dice', None, natural,
                          lambda roll, mode, outcome: expression_result(roll, terms, mode, outcome),
                          draw, lambda roll: roll['total'], supports_luck=numeric([die for die, _ in variables(terms)]))
