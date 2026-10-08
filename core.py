"""Engine boundaries, ownership checks, atomic command handling, and staged rolls."""

import copy
import json
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from .private_controls import PrivateRolls
from .dice import parse, parse_faces
from .rules import STATS, TALENTS, GameError, clean, require


def operation(function=None, *, gm=False, pending=False):
    def wrap(function):
        function.operation = True
        function.needs_gm = gm
        function.allow_pending = pending
        return function
    return wrap(function) if function is not None else wrap


@dataclass(frozen=True)
class Actor:
    guild_id: int
    user_id: int
    role_ids: tuple = ()


@dataclass
class Context:
    game: object
    actor: Actor
    state: dict
    before: dict

    @property
    def uid(self):
        return str(self.actor.user_id)

    @property
    def gm(self):
        role = self.state['settings']['gm_role_id']
        return self.actor.user_id == self.game.owner_id or role is not None and int(role) in self.actor.role_ids

    def hero(self, user=None, *, approved=True):
        h = self.state['characters'].get(str(user or self.uid))
        require(h is not None, "Create a hero with /hero create first.")
        require(not approved or h['approved'], "The GM must approve this hero first.")
        return h

    def owned(self, user=None, *, approved=True):
        require(user is None or str(user) == self.uid or self.gm, "You can only change your own hero.")
        return self.hero(user, approved=approved)

    def quiet(self):
        b = self.state['battle']
        require(not b or b['phase'] == 'finished', "Finish the current battle first.")
        require(not self.state['spar'], "Finish or cancel the current spar first.")

    def downtime(self):
        self.quiet()
        require(not self.state['mission'], "Change prepared choices during downtime between missions.")


class Core:
    def __init__(self, store, owner_id, *, rng=None, clock=None):
        require(int(owner_id) > 0, "BOT_OWNER_ID must be your Discord user ID.")
        self.store, self.owner_id = store, int(owner_id)
        self.rng = rng or random.SystemRandom()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.private = PrivateRolls(store, owner_id, self.clock)

    def execute(self, actor, operation_name, *, request_id=None, **kwargs):
        method = getattr(self, operation_name, None)
        require(method is not None and getattr(method, 'operation', False), "Unknown game operation.")
        require(actor.guild_id > 0 and actor.user_id > 0, "Use a game command inside a server.")
        with self.store.transaction() as db:
            if request_id:
                cached = db.execute("SELECT guild,result FROM receipts WHERE request=?", (str(request_id),)).fetchone()
                if cached:
                    require(cached['guild'] == str(actor.guild_id), "Invalid command receipt.")
                    return json.loads(cached['result'])
            state = self.store.load(actor.guild_id)
            before = copy.deepcopy(state)
            context = Context(self, actor, state, before)
            require(not method.needs_gm or context.gm, "Only the creator or configured GM role can do that.")
            require(not state['pending'] or method.allow_pending, "Resolve the waiting roll first with /battle resolve or its buttons.")
            result = method(context, **kwargs)
            require(isinstance(result, dict), "The command did not produce a valid result.")
            if context.state != before:
                self.store.save(actor.guild_id, context.state)
                if operation_name not in {'undo', 'cancel_roll', 'board_set'}:
                    db.execute("INSERT INTO history(guild,actor,operation,before_state,created) VALUES(?,?,?,?,?)",
                               (str(actor.guild_id), context.uid, operation_name, json.dumps(before), self.clock().isoformat()))
                    db.execute("DELETE FROM history WHERE guild=? AND id NOT IN (SELECT id FROM history WHERE guild=? ORDER BY id DESC LIMIT 100)",
                               (str(actor.guild_id), str(actor.guild_id)))
            if request_id:
                db.execute("INSERT INTO receipts VALUES(?,?,?)", (str(request_id), str(actor.guild_id), json.dumps(result)))
                db.execute("DELETE FROM receipts WHERE guild=? AND rowid NOT IN (SELECT rowid FROM receipts WHERE guild=? ORDER BY rowid DESC LIMIT 1000)",
                           (str(actor.guild_id), str(actor.guild_id)))
            return result

    def bonuses(self, c, hero, *, stat, scope, signature=False, rescue=False, edge=False,
                pressure=False, talent=False, prep=False, help_task=None):
        require(stat in STATS, "Choose Power, Speed, Wits, or Heart.")
        if talent:
            require(not hero['talent_used'], "Your Talent has already been used this scene.")
            category = TALENTS[hero['talent']][1]
            require(category == stat or category == 'rescue' and rescue or category == 'signature' and signature,
                    "Your prepared Talent does not fit this roll.")
            hero['talent_used'] = True
            edge = True
        if prep:
            p = hero['prep']
            require(p is not None and c.state['mission'] and p['mission'] == c.state['mission']['id'], "You do not have Prep for this main mission.")
            # The submitted method must fit the theme; fiction remains the GM's decision.
            hero['prep'] = None
            edge = True
        held = hero['help']
        assisted = bool(held and held['task'] == (help_task or scope))
        if assisted:
            edge = True
            hero['help'] = None
        if hero.get('smoke') and scope in {'escape', 'hide'}:
            edge = True
            hero['smoke'] = False
        return edge, pressure, assisted

    def staged(self, c, hero, *, stat, scope, effect, method, edge=False, pressure=False,
               talent=False, prep=False, signature=False, rescue=False, help_task=None):
        require(not c.state['pending'], "Another roll is waiting.")
        method = clean(method, 500)
        edge, pressure, assisted = self.bonuses(c, hero, stat=stat, scope=scope, signature=signature,
            rescue=rescue, edge=edge, pressure=pressure, talent=talent, prep=prep, help_task=help_task)
        rig_scope = effect['kind'] if effect['kind'] in {'check', 'attack', 'capture', 'task', 'defense'} else 'task'
        roll = self.private.stat(c.actor.guild_id, hero['user_id'], rig_scope, stat, hero['stats'][stat], edge, pressure, self.rng)
        token = uuid.uuid4().hex[:16]
        c.state['pending'] = {'id': token, 'user_id': hero['user_id'], 'stat': stat, 'scope': scope,
                              'method': method, 'roll': roll, 'effect': effect, 'assisted': assisted,
                              'rollback': c.before}
        return {'type': 'pending', 'title': f"{hero['hero_name']} · {scope}", 'roll': roll,
                'pending_id': token, 'user_id': hero['user_id'], 'method': method,
                'text': "Keep this roll, or use Plus Ultra (−2 Health, once per session)."}

    @operation(pending=True)
    def roll_decision(self, c, *, choice='show'):
        require(choice in {'show','keep','plus'}, 'Choose show, keep, or plus.')
        return self.pending_status(c) if choice == 'show' else self.resolve(c, plus_ultra=choice == 'plus')

    @operation(pending=True)
    def resolve(self, c, *, plus_ultra=False, pending_id=None):
        p = c.state['pending']
        require(p is not None, "No roll is waiting.")
        require(pending_id is None or p['id'] == pending_id, "This button belongs to an older roll.")
        require(c.uid == p['user_id'] or c.gm and not plus_ultra, "Only the rolling player can choose Plus Ultra. The GM may accept a waiting result.")
        h = c.hero(p['user_id'])
        if plus_ultra:
            require(not h['plus_used'], "Plus Ultra has already been used this session.")
            h['plus_used'] = True
        result = 8 if plus_ultra else p['roll']['kept']
        c.state['pending'] = None
        messages = self.apply_effect(c, h, p['effect'], result, p['assisted'])
        if plus_ultra:
            h['health'] = max(0, h['health'] - 2)
            messages.append(f"Plus Ultra costs 2 Health. Health {h['health']}/6.")
        return {'title': f"{h['hero_name']} · {'Plus Ultra' if plus_ultra else 'result'} {result}",
                'text': '\n'.join(messages), 'roll': dict(p['roll'], kept=result), 'type': 'result'}

    @operation(gm=True, pending=True)
    def cancel_roll(self, c, *, reason):
        require(c.state['pending'], "No roll is waiting.")
        reason = clean(reason, 300)
        c.state = c.state['pending']['rollback']
        return {'title': 'GM cancelled a staged roll', 'text': f"Restored the game state from before that command. Reason: {reason}"}

    @operation(gm=True)
    def undo(self, c, *, reason):
        reason = clean(reason, 300)
        row = self.store.db.execute("SELECT * FROM history WHERE guild=? ORDER BY id DESC LIMIT 1", (str(c.actor.guild_id),)).fetchone()
        require(row is not None, "There is no recent change to undo.")
        c.state = json.loads(row['before_state'])
        self.store.db.execute("DELETE FROM history WHERE id=?", (row['id'],))
        return {'title': 'GM correction', 'text': f"Undid {row['operation']}. Reason: {reason}"}

    @operation(pending=True)
    def pending_status(self, c):
        p = c.state['pending']
        if not p:
            return {'text': 'No roll is waiting.'}
        return {'type': 'pending', 'title': f"Waiting for {c.hero(p['user_id'])['hero_name']}",
                'roll': p['roll'], 'pending_id': p['id'], 'user_id': p['user_id'], 'text': 'Use /battle resolve or the buttons.'}

    @operation(pending=True)
    def roll(self, c, *, dice='1d20', bonus=0, keep='all', faces=''):
        return self.dice_roll(c, expression=dice, bonus=bonus, keep=keep, faces=faces)

    @operation(pending=True)
    def dice_roll(self, c, *, expression, keep='all', bonus=0, faces=''):
        # Old saved names remain usable. Per-roll faces never change campaign data.
        custom = dict(c.state['dice'])
        if faces:
            custom['custom'] = parse_faces(faces)
            terms = parse(expression, custom)
            require(any(die.label == 'd[custom]' for _, term in terms if isinstance(term, list)
                        for die in term), 'Use dice:1d[custom] (or 2d[custom], etc.) with the faces field.')
        r = self.private.expression(c.actor.guild_id, c.uid, expression, custom, keep, self.rng, bonus=bonus)
        return {'type': 'dice', 'title': 'Dice roll', 'dice': r}

    def expire_help(self, c):
        for other in c.state['characters'].values():
            if other['help'] and other['help']['source'] == c.uid:
                other['help'] = None

    @operation
    def check(self, c, *, stat, method, task='check', edge=False, pressure=False, talent=False, prep=False, rescue=False):
        c.quiet()
        h = c.hero()
        require(h['health'] > 0, "A Down hero needs assistance or safe recovery first.")
        require(task in {'check', 'escape', 'hide', 'rescue', 'investigation'}, "Choose an ordinary check task.")
        self.expire_help(c)
        return self.staged(c, h, stat=stat, scope=task, method=method,
                          effect={'kind': 'check'}, edge=edge, pressure=pressure, talent=talent, prep=prep, rescue=rescue,
                          help_task=task)

    @operation(gm=True, pending=True)
    def export(self, c):
        # Campaign state only: private control tables and credentials are never serialized.
        safe = copy.deepcopy(c.state)
        if safe['pending']:
            safe['pending'].pop('rollback', None)
        return {'type': 'file', 'filename': 'ua_campaign.json', 'data': safe, 'text': 'Campaign export. Full database backups can be made with the included backup utility.'}
