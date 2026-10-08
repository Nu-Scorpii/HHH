"""Cooperative battle engine: zones, turns, protection, objectives, and defense."""

from collections import deque
from .core import operation
from .rules import ENEMIES, ITEMS, MOVES, STATS, clean, ids, require


def zone_id(value):
    import re
    value = str(value).strip().lower()
    require(re.fullmatch(r'[a-z0-9_-]{1,32}', value), 'Zone IDs use 1–32 letters, digits, underscores, or hyphens.')
    return value


class Battle:
    @operation
    def strike(self, c, *, targets, stat='power', method='Agreed action.', move='basic', edge=False, pressure=False, talent=False, prep=False):
        if move == 'capture':
            foes = [value.strip() for value in targets.split(',')]
            require(len(foes) == 1 and foes[0], 'Capture chooses one enemy ID.')
            return self.battle_capture(c, enemy=foes[0], stat=stat, method=method, edge=edge, pressure=pressure, talent=talent, prep=prep)
        return self.battle_attack(c, targets=targets, stat=stat, method=method, move=move,
                                  edge=edge, pressure=pressure, talent=talent, prep=prep)

    @operation
    def protect(self, c, *, user=None, method='Protect against the announced attack.', kind='guard'):
        require(kind in {'guard','shield'}, 'Choose Guard or Shield.')
        if kind == 'shield':
            require(user is None, 'Shield protects your zone. Leave the player option empty.')
            return self.battle_shield(c, method=method)
        return self.battle_guard(c, user=user, method=method)

    @operation(gm=True)
    def edit_enemy(self, c, *, enemy, health=None, damage=None, actions=None, trait='', enabled=True):
        result = self.enemy_edit(c, enemy=enemy, health=health, damage=damage, actions=actions)
        if trait:
            result = self.enemy_trait(c, enemy=enemy, trait=trait, enabled=enabled)
        return result

    @operation(gm=True)
    def danger(self, c, *, name='', consequence='', goal=3, active=True):
        if not active:
            return self.danger_stop(c, reason=consequence or 'The danger has ended.')
        return self.danger_set(c, name=name, consequence=consequence, goal=goal)

    def battle(self, c, *, phase=None):
        b = c.state['battle']
        require(b is not None and b['phase'] != 'finished', 'There is no active battle. GM: /gm battle create.')
        require(phase is None or b['phase'] == phase, f"This needs the {phase} phase.")
        return b

    def turn(self, c, *, allow_down=False):
        b = self.battle(c, phase='heroes')
        require(not b['incoming'] and not b['bonus_moves'], 'Finish all defenses and bonus movement choices first.')
        if b['active'] is None:
            self.battle_turn(c)
        require(b['active'] == c.uid, 'Another hero is taking their turn. Wait for them to end it.')
        h = c.hero()
        require(allow_down or h['health'] > 0, 'A Down hero can only cheer once per fight, or end the turn.')
        return b, h, b['budget']

    def action(self, budget):
        require(not budget['action'], 'You have already used your action this turn.')
        budget['action'] = True

    def signature(self, hero, budget, move):
        require(move in hero['moves'], 'That signature move is not prepared.')
        require(not budget['signature'], 'Use at most one signature move on your turn.')
        require(hero['energy'] >= MOVES[move]['cost'], 'Not enough Energy. Recover or use an ordinary action.')
        hero['energy'] -= MOVES[move]['cost']
        budget['signature'] = True

    def path(self, b, source, destination, *, maximum=None, blocked=False):
        require(destination in b['zones'], 'That zone does not exist.')
        queue, seen = deque([(source, 0)]), {source}
        while queue:
            here, steps = queue.popleft()
            if here == destination:
                return maximum is None or steps <= maximum
            for other, clear in b['zones'][here].items():
                if (clear or blocked) and other not in seen and (maximum is None or steps < maximum):
                    seen.add(other)
                    queue.append((other, steps + 1))
        return False

    def reach(self, b, h, target_zone, *, long=False):
        here = b['positions'][h['user_id']]
        return target_zone == here or long or h['quirk']['reach'] == 'ranged' and b['zones'][here].get(target_zone, False)

    def expire(self, c, uid):
        for h in c.state['characters'].values():
            if h['help'] and h['help']['source'] == uid:
                h['help'] = None
            if h['guard'] and h['guard']['source'] == uid:
                h['guard'] = None
        c.state['battle']['shields'].pop(uid, None)

    @operation(gm=True)
    def battle_create(self, c, *, name, participants, starting_zone='start'):
        c.quiet()
        users = ids(participants)
        require(len(users) <= 20, 'Use at most 20 heroes in one battle.')
        for user in users:
            c.hero(user)
        zone = zone_id(starting_zone)
        self.refresh_scene(c.state)
        c.state['battle'] = {
            'name': clean(name, 120), 'phase': 'setup', 'round': 0, 'participants': users,
            'zones': {zone: {}}, 'positions': dict.fromkeys(users, zone), 'enemies': {},
            'acted': [], 'active': None, 'budget': None, 'objectives': {}, 'danger': None,
            'shields': {}, 'incoming': None, 'bonus_moves': {}, 'next_enemy': 1,
        }
        for user in users:
            c.hero(user).update(healed=False, cheered=False)
        return {'text': 'Battle created. GM: add zones, enemies, objectives, and intentions, then /gm battle start. Health and Energy are unchanged.'}

    @operation(gm=True)
    def zone_add(self, c, *, name, connect_to='', clear=True):
        b = self.battle(c)
        name = zone_id(name)
        links = [zone_id(x) for x in connect_to.split(',') if x.strip()]
        require(name not in b['zones'], 'That zone already exists. Use /gm zone link to change a connection.')
        require(len(b['zones']) < 25 and all(x in b['zones'] for x in links), 'Use at most 25 zones and existing connections.')
        b['zones'][name] = {}
        for other in links:
            b['zones'][name][other] = b['zones'][other][name] = clear
        return {'text': f"Zone {name} added. {'Clear' if clear else 'Blocked'} links: {', '.join(links) or 'none'}."}

    @operation(gm=True)
    def zone_link(self, c, *, first, second, clear=True):
        b = self.battle(c)
        first, second = zone_id(first), zone_id(second)
        require(first in b['zones'] and second in b['zones'] and first != second, 'Choose two different existing zones.')
        b['zones'][first][second] = b['zones'][second][first] = clear
        return {'text': f"{first} ↔ {second}: {'clear' if clear else 'blocked'}."}

    @operation(gm=True)
    def position(self, c, *, target, zone, reason):
        b = self.battle(c)
        zone = zone_id(zone)
        require(zone in b['zones'], 'That zone does not exist.')
        target = str(target).lower()
        if target in b['positions']:
            b['positions'][target] = zone
        else:
            require(target in b['enemies'], 'Use a hero user ID or enemy ID.')
            b['enemies'][target]['zone'] = zone
        return {'text': f"GM positioned {target} in {zone}. Reason: {clean(reason, 300)}"}

    @operation(gm=True)
    def enemy_add(self, c, *, name, template, zone, trait='none', reach='touch'):
        b = self.battle(c)
        require(template in ENEMIES and reach in {'touch', 'ranged', 'scene'}, 'Choose a template and valid enemy reach.')
        zone = zone_id(zone)
        require(zone in b['zones'] and len(b['enemies']) < 25, 'Use an existing zone and at most 25 foes.')
        require(trait in {'none', 'armor', 'protector', 'wide', 'fast'}, 'Choose a listed enemy trait.')
        hp, damage, actions = ENEMIES[template]
        key = f"e{b['next_enemy']}"
        b['next_enemy'] += 1
        b['enemies'][key] = {'id': key, 'name': clean(name, 80), 'health': hp, 'maximum': hp,
                            'damage': damage, 'actions': actions, 'boss': template == 'boss', 'zone': zone,
                            'traits': [] if trait == 'none' else [trait], 'reach': reach, 'intention': 'GM has not announced an intention.',
                            'used': 0, 'moved': 0, 'capture': 0, 'cancelled': 0}
        return {'text': f"{key}: {name}, Health {hp}, damage {damage}, {actions} action(s)."}

    @operation(gm=True)
    def enemy_edit(self, c, *, enemy, health=None, damage=None, actions=None):
        foe = self.foe(self.battle(c), enemy, alive=False)
        if health is not None:
            require(0 <= health <= 10000, 'Enemy Health is 0–10000.')
            foe['health'], foe['maximum'] = health, max(health, foe['maximum'])
        if damage is not None:
            require(0 <= damage <= 20, 'Enemy damage is 0–20.')
            foe['damage'] = damage
        if actions is not None:
            require(actions in (1, 2), 'Enemies have one or two actions.')
            foe['actions'], foe['boss'] = actions, actions == 2
        return {'text': 'Enemy numbers updated.'}

    @operation(gm=True)
    def enemy_trait(self, c, *, enemy, trait, enabled=True):
        foe = self.foe(self.battle(c), enemy, alive=False)
        require(trait in {'armor', 'protector', 'wide', 'fast'}, 'Choose a listed trait.')
        if enabled and trait not in foe['traits']:
            foe['traits'].append(trait)
        elif not enabled and trait in foe['traits']:
            foe['traits'].remove(trait)
        return {'text': f"{foe['name']}: {trait} {'enabled' if enabled else 'removed'}."}

    @operation(gm=True)
    def enemy_intent(self, c, *, enemy, intention):
        foe = self.foe(self.battle(c), enemy, alive=False)
        foe['intention'] = clean(intention, 500)
        return {'text': f"{foe['name']}: {foe['intention']}"}

    def foe(self, b, enemy, *, alive=True):
        enemy = str(enemy).lower().strip()
        require(enemy in b['enemies'], 'Use an enemy ID such as e1 from /battle status.')
        foe = b['enemies'][enemy]
        require(not alive or foe['health'] > 0, 'That enemy is defeated and loses its actions.')
        return foe

    @operation(gm=True)
    def objective_add(self, c, *, key, name, goal=4, zone='', prerequisites=''):
        b = self.battle(c)
        key = zone_id(key)
        require(key not in b['objectives'] and len(b['objectives']) < 20, 'Use a new objective ID; maximum 20.')
        require(1 <= goal <= 100, 'Use 1–100 progress marks.')
        zone = zone_id(zone) if zone else None
        require(zone is None or zone in b['zones'], 'The objective zone does not exist.')
        prior = [zone_id(x) for x in prerequisites.split(',') if x.strip()]
        require(all(x in b['objectives'] for x in prior), 'Prerequisites must be existing objective IDs.')
        b['objectives'][key] = {'name': clean(name, 120), 'progress': 0, 'goal': goal, 'zone': zone, 'requires': prior}
        return {'text': f"Objective {key} added: 0/{goal}. Prerequisites: {', '.join(prior) or 'none'}."}

    @operation(gm=True)
    def objective_tick(self, c, *, key, amount, reason):
        b = self.battle(c)
        require(key in b['objectives'], 'That objective does not exist.')
        o = b['objectives'][key]
        require(abs(amount) <= 100, 'Change at most 100 marks.')
        o['progress'] = max(0, min(o['goal'], o['progress'] + amount))
        return {'text': f"{o['name']}: {o['progress']}/{o['goal']}. Reason: {clean(reason, 300)}"}

    @operation(gm=True)
    def danger_set(self, c, *, name, goal=3, consequence):
        require(1 <= goal <= 100, 'Use 1–100 danger marks.')
        self.battle(c)['danger'] = {'name': clean(name, 120), 'progress': 0, 'goal': goal,
                                     'active': True, 'consequence': clean(consequence, 500)}
        return {'text': 'Danger announced. It advances once at the end of a round until its cause is stopped.'}

    @operation(gm=True)
    def danger_stop(self, c, *, reason):
        danger = self.battle(c)['danger']
        require(danger, 'No Danger track exists.')
        danger['active'] = False
        return {'text': f"Danger stopped. Reason: {clean(reason, 300)}"}

    @operation(gm=True)
    def battle_start(self, c):
        b = self.battle(c, phase='setup')
        b.update(phase='heroes', round=1)
        return {'text': 'Round 1: heroes choose order. Your first move or action starts your turn automatically. Finish with /battle end.'}

    @operation
    def battle_turn(self, c):
        b = self.battle(c, phase='heroes')
        require(not b['incoming'] and not b['bonus_moves'], 'Finish all defenses and bonus movement choices first.')
        require(c.uid in b['participants'] and c.uid not in b['acted'], 'You are not an unacted participant this round.')
        require(b['active'] is None, 'Another hero is taking their turn.')
        self.expire(c, c.uid)
        b['active'], b['budget'] = c.uid, {'action': False, 'move': False, 'signature': False}
        return {'text': f"{c.hero()['hero_name']}'s turn. One free move and one action."}

    @operation
    def battle_end(self, c):
        b, h, budget = self.turn(c, allow_down=True)
        b['acted'].append(c.uid)
        b['active'], b['budget'] = None, None
        return {'text': f"{h['hero_name']}'s turn ended."}

    @operation(gm=True)
    def battle_skip(self, c, *, user, reason):
        b = self.battle(c, phase='heroes')
        require(not b['incoming'] and not b['bonus_moves'], 'Finish all defenses and bonus movement choices first.')
        uid = str(user)
        require(uid in b['participants'] and uid not in b['acted'], 'Choose an unacted battle participant.')
        require(b['active'] in (None, uid), 'Another hero is active.')
        self.expire(c, uid)
        b['acted'].append(uid)
        b['active'], b['budget'] = None, None
        return {'text': f"GM ended {c.hero(uid)['hero_name']}'s turn without spending optional resources. Reason: {clean(reason, 300)}"}

    @operation(gm=True)
    def battle_phase(self, c, *, phase):
        b = self.battle(c)
        require(b['active'] is None and not b['incoming'] and not b['bonus_moves'],
                'Finish the active turn, all defenses, and bonus movement choices first.')
        if phase == 'enemies':
            require(b['phase'] == 'heroes', 'This needs the heroes phase.')
            missing = [u for u in b['participants'] if u not in b['acted'] and c.hero(u)['health'] > 0]
            require(not missing, 'Heroes still have turns. They can /battle end, or the GM can /gm battle skip.')
            b['phase'] = 'enemies'
            return {'text': 'Enemy phase. GM: resolve each surviving foe’s announced actions with /gm enemy attack or /gm enemy action.'}
        require(phase == 'next' and b['phase'] == 'enemies', 'Use enemies, or next after the enemy phase.')
        require(all(e['health'] == 0 or e['used'] >= e['actions'] for e in b['enemies'].values()), 'Resolve or explicitly skip the remaining enemy actions first.')
        messages = []
        d = b['danger']
        if d and d['active']:
            d['progress'] = min(d['goal'], d['progress'] + 1)
            messages.append(f"Danger {d['name']}: {d['progress']}/{d['goal']}.")
            if d['progress'] == d['goal']:
                d['active'] = False
                messages.append(f"Consequence: {d['consequence']}")
        for e in b['enemies'].values():
            e.update(used=0, moved=0, capture=0, cancelled=0)
        b.update(phase='heroes', round=b['round'] + 1, acted=[])
        messages.append(f"Round {b['round']}: GM announces intentions; heroes choose order.")
        return {'text': '\n'.join(messages)}

    @operation(gm=True)
    def battle_finish(self, c, *, outcome):
        b = self.battle(c)
        require(not b['incoming'], 'Resolve the incoming attack first.')
        b.update(phase='finished', active=None, budget=None, shields={}, bonus_moves={})
        for uid in b['participants']:
            c.hero(uid).update(help=None, guard=None)
        return {'text': f"Battle finished: {clean(outcome, 500)}. Health and Energy carry over until safe recovery."}

    @operation(pending=True)
    def battle_status(self, c):
        b = c.state['battle']
        require(b is not None, 'No battle has been created.')
        return {'type': 'battle', 'title': b['name'], 'battle': b,
                'heroes': {uid: c.hero(uid, approved=False) for uid in b['participants']},
                'pending_user': c.state['pending']['user_id'] if c.state['pending'] else None}

    @operation(gm=True, pending=True)
    def board_set(self, c, *, channel_id, message_id):
        self.battle(c)['board'] = {'channel_id': channel_id, 'message_id': message_id}
        return {'text': 'Live battle panel saved.'}

    @operation
    def battle_move(self, c, *, zone, mode='normal', method='Move along a clear route.', carry='',
                    harness=False, grapple=False, risky=False, stat='speed', pressure=False, talent=False, prep=False):
        b, h, budget = self.turn(c)
        require(mode in {'normal', 'rush', 'rapid'}, 'Choose normal, rush, or rapid movement.')
        destination, source = zone_id(zone), b['positions'][c.uid]
        require(destination != source, 'Choose a different zone, or keep your free move.')
        passengers = ids(carry) if carry.strip() else []
        require(c.uid not in passengers and len(passengers) <= (2 if harness else 1), 'Carry one cooperative person, or two with Rescue Harness.')
        require(all(u in b['positions'] and b['positions'][u] == source for u in passengers), 'Passengers must start in your zone.')
        require(not (harness and grapple), 'Prepare at most one special support item.')
        for item, active in [('rescue_harness', harness), ('grapple_line', grapple)]:
            if active:
                require(h['item'] == item and not h['item_used'], 'That support item is not prepared or has already been used.')
        require(not grapple or mode == 'normal' and not risky, 'Grapple Line uses an ordinary free move across one anchored connection.')
        require(self.path(b, source, destination, maximum=None if mode == 'rapid' else 1, blocked=grapple), 'No permitted route reaches that zone. The GM can open a connection when your Quirk or situation allows it.')
        if mode != 'rush':
            require(not budget['move'], 'You have already used your free movement.')
            budget['move'] = True
        if mode == 'rapid':
            require(not budget['action'] and not risky, 'Rapid Move comes before an ordinary action on a reachable route.')
            self.signature(h, budget, 'rapid_move')
        if mode == 'rush' or risky:
            self.action(budget)
        if harness or grapple:
            h['item_used'] = True
        if risky:
            return self.staged(c, h, stat=stat, scope='task', method=method,
                effect={'kind': 'move', 'zone': destination, 'passengers': passengers}, pressure=pressure,
                talent=talent, prep=prep)
        b['positions'][c.uid] = destination
        for user in passengers:
            b['positions'][user] = destination
        return {'text': f"{h['hero_name']} moved to {destination}" + (f" with {len(passengers)} cooperative passenger(s)." if passengers else '.')}

    @operation
    def battle_attack(self, c, *, targets, stat, method, move='basic', edge=False, pressure=False,
                      talent=False, prep=False, assisted_target='', visible=True):
        b, h, budget = self.turn(c)
        require(move in {'basic', 'heavy_hit', 'burst', 'long_reach'}, 'Choose basic, Heavy Hit, Burst, or Long Reach.')
        keys = list(dict.fromkeys(x.strip().lower() for x in targets.split(',') if x.strip()))
        require(1 <= len(keys) <= (3 if move == 'burst' else 1), 'Name one foe, or up to three for Burst.')
        foes = [self.foe(b, key) for key in keys]
        require(move != 'burst' or len({f['zone'] for f in foes}) == 1, 'Burst targets must share one zone.')
        require(visible, 'A blocked line of sight prevents this attack. Choose another action.')
        require(move != 'long_reach' or h['quirk']['reach'] == 'ranged', 'Long Reach needs a suitable ranged Quirk.')
        require(all(self.reach(b, h, f['zone'], long=move == 'long_reach') for f in foes), 'A target is outside your approved normal reach.')
        chosen = assisted_target.lower().strip() or keys[0]
        require(chosen in keys, 'The assisted target must be one of the named targets.')
        self.action(budget)
        if move != 'basic':
            self.signature(h, budget, move)
        pressure = pressure or any('protector' in f['traits'] for f in foes)
        return self.staged(c, h, stat=stat, scope='attack', method=method, effect={'kind': 'attack', 'targets': keys,
            'move': move, 'assisted_target': chosen}, edge=edge, pressure=pressure, talent=talent, prep=prep, signature=move != 'basic')

    @operation
    def battle_capture(self, c, *, enemy, stat, method, edge=False, pressure=False, talent=False, prep=False):
        b, h, budget = self.turn(c)
        foe = self.foe(b, enemy)
        require(self.reach(b, h, foe['zone']), 'The foe is out of normal reach.')
        self.action(budget)
        self.signature(h, budget, 'capture')
        return self.staged(c, h, stat=stat, scope='capture', method=method, effect={'kind': 'capture', 'enemy': foe['id']},
            edge=edge, pressure=pressure or 'protector' in foe['traits'], talent=talent, prep=prep, signature=True)

    @operation
    def battle_task(self, c, *, stat, method, objective='', boost=False, edge=False, pressure=False, talent=False, prep=False, rescue=False, task_type='task'):
        b, h, budget = self.turn(c)
        require(task_type in {'task', 'escape', 'hide', 'rescue', 'investigation'}, 'Choose a valid task type.')
        if objective:
            require(objective in b['objectives'], 'That objective does not exist.')
            o = b['objectives'][objective]
            require(o['progress'] < o['goal'], 'That objective is already complete.')
            require(all(b['objectives'][x]['progress'] >= b['objectives'][x]['goal'] for x in o['requires']), 'Complete the announced prerequisites first.')
            require(o['zone'] is None or self.reach(b, h, o['zone']), 'The objective is out of reach.')
        self.action(budget)
        if boost:
            require(objective, 'Rescue Boost needs a progress objective.')
            self.signature(h, budget, 'rescue_boost')
        return self.staged(c, h, stat=stat, scope=task_type, method=method,
            effect={'kind': 'task', 'objective': objective, 'boost': boost}, edge=edge, pressure=pressure,
            talent=talent, prep=prep, signature=boost, rescue=rescue or boost,
            help_task=f"objective:{objective}" if objective else task_type)

    @operation
    def battle_help(self, c, *, user, task, method, objective=''):
        b, h, budget = self.turn(c, allow_down=True)
        ally = c.hero(user)
        require(str(user) in b['participants'] and str(user) != c.uid, 'Help a teammate in this battle, not yourself.')
        require(task in {'attack', 'defense', 'capture', 'task', 'rescue', 'investigation', 'escape', 'hide'}, 'Choose the named task to support.')
        if objective:
            require(objective in b['objectives'] and task == 'task', 'Choose task and an existing objective ID.')
            task = f"objective:{objective}"
        if h['health'] == 0:
            require(not h['cheered'], 'You have already cheered while Down this fight.')
            h['cheered'] = True
        self.action(budget)
        ally['help'] = {'source': c.uid, 'task': task, 'method': clean(method, 500)}
        return {'text': f"{h['hero_name']} Helps {ally['hero_name']} on {task}. Expires at the start of the helper's next turn. Any previous Help is replaced."}

    @operation
    def battle_guard(self, c, *, user=None, method='Protect them from the announced attack.'):
        b, h, budget = self.turn(c)
        ally = c.hero(user or c.uid)
        require(ally['user_id'] in b['positions'] and b['positions'][ally['user_id']] == b['positions'][c.uid], 'Guard someone in your zone.')
        self.action(budget)
        ally['guard'] = {'source': c.uid, 'method': clean(method, 500)}
        return {'text': f"{ally['hero_name']} is Guarded against one attack for 2 damage reduction, until the guard's next turn."}

    @operation
    def battle_shield(self, c, *, method='Prepare a barrier in my zone.'):
        b, h, budget = self.turn(c)
        self.action(budget)
        self.signature(h, budget, 'shield')
        b['shields'][c.uid] = {'zone': b['positions'][c.uid], 'method': clean(method, 500)}
        return {'text': 'Shield prepared: friendly targets in this zone get −2 damage from one enemy attack. Expires at your next turn; no protection stacking.'}

    @operation
    def battle_recover(self, c):
        b, h, budget = self.turn(c)
        self.action(budget)
        h['energy'] = min(3, h['energy'] + 1)
        return {'text': f"Recovered 1 Energy. Energy {h['energy']}/3."}

    @operation
    def mend(self, c, *, user):
        b = c.state['battle']
        active = b is not None and b['phase'] != 'finished'
        if active:
            b, h, budget = self.turn(c)
            require(str(user) in b['positions'] and b['positions'][str(user)] == b['positions'][c.uid], 'Mend requires touch in your own zone.')
            self.action(budget)
            self.signature(h, budget, 'mend')
        else:
            c.quiet()
            h = c.hero()
            require(h['health'] > 0 and 'mend' in h['moves'] and h['energy'] >= 2, 'Prepare Mend and have 2 Energy while conscious.')
            h['energy'] -= 2
            self.expire_help(c)
        ally = c.hero(user)
        require(not active or not ally['healed'], 'That hero has already received a healing action this fight.')
        require(ally['health'] < 6, 'That hero is already at full Health.')
        ally['health'] = 1 if ally['health'] == 0 else min(6, ally['health'] + 2)
        if active:
            ally['healed'] = True
        return {'text': f"{ally['hero_name']} now has {ally['health']}/6 Health."}

    @operation
    def item_use(self, c, *, user=None, question=''):
        h = c.hero()
        item = h['item']
        require(item in ITEMS and not h['item_used'], 'Prepare a support item; use it once per scene.')
        require(h['health'] > 0, 'A Down hero cannot use an item.')
        require(item not in {'grapple_line', 'rescue_harness'}, 'Use /battle move with grapple or harness enabled for that item.')
        b = c.state['battle']
        active = b is not None and b['phase'] != 'finished'
        ally = c.hero(user or c.uid)
        if not active:
            c.quiet()
            if item in {'medical_patch', 'field_scanner'}:
                self.expire_help(c)
        if active:
            b, h, budget = self.turn(c)
            require(ally['user_id'] in b['positions'], 'Choose a battle participant.')
            if item == 'medical_patch':
                require(b['positions'][ally['user_id']] == b['positions'][c.uid], 'Medical Patch requires touch in your zone.')
            if item in {'medical_patch', 'field_scanner'}:
                self.action(budget)
        if item == 'medical_patch':
            require(0 < ally['health'] < 6 and (not active or not ally['healed']), 'Medical Patch needs an injured conscious hero who has not been healed this fight.')
            ally['health'] += 1
            if active:
                ally['healed'] = True
            text = f"{ally['hero_name']} now has {ally['health']}/6 Health."
        elif item == 'smoke_capsule':
            ally['smoke'] = True
            text = f"{ally['hero_name']} has Edge on the next escape or hiding roll this scene."
        else:
            text = f"Scanner question: {clean(question, 500)}\nGM: give one useful true fact within the scanner's agreed scope."
        h['item_used'] = True
        return {'text': text}

    @operation
    def battle_automatic(self, c, *, method):
        b, h, budget = self.turn(c)
        self.action(budget)
        return {'text': f"{h['hero_name']} uses an ordinary action: {clean(method, 500)}\nGM: confirm the fictional effect. Use /gm objective tick if this safely advances a track."}

    def enemy_action_budget(self, foe):
        require(foe['used'] < foe['actions'], 'That enemy has used all its actions this round.')
        foe['used'] += 1
        captured = foe['capture']
        foe['capture'] = 0
        if captured >= 8 and (not foe['boss'] or foe['cancelled'] < 1):
            foe['cancelled'] += 1
            return False, 0
        return True, 1 if 4 <= captured < 8 else 0

    @operation(gm=True)
    def enemy_move(self, c, *, enemy, zone):
        b = self.battle(c, phase='enemies')
        require(not b['incoming'] and not b['bonus_moves'], 'Finish the current attack and bonus movement choices first.')
        foe = self.foe(b, enemy)
        maximum = 2 if 'fast' in foe['traits'] else 1
        require(foe['capture'] < 4, 'Capture blocks movement until the next action ends or is cancelled.')
        destination = zone_id(zone)
        require(destination != foe['zone'], 'Choose a different zone.')
        remaining = maximum - foe['moved']
        require(remaining > 0 and self.path(b, foe['zone'], destination, maximum=remaining), 'The foe has no remaining permitted move to that zone.')
        # Count actual connections, so two short moves cannot exceed a Fast foe's budget.
        steps = next(n for n in range(1, remaining + 1) if self.path(b, foe['zone'], destination, maximum=n))
        foe['zone'], foe['moved'] = destination, foe['moved'] + steps
        return {'text': f"{foe['name']} moves to {destination}."}

    @operation(gm=True)
    def enemy_action(self, c, *, enemy, description, objective='', amount=1):
        b = self.battle(c, phase='enemies')
        require(not b['incoming'] and not b['bonus_moves'], 'Finish the current attack and bonus movements first.')
        foe = self.foe(b, enemy)
        description = clean(description, 500)
        allowed, penalty = self.enemy_action_budget(foe)
        if not allowed:
            return {'text': f"Capture cancels {foe['name']}'s action. {foe['actions'] - foe['used']} action(s) remain."}
        if objective:
            require(objective in b['objectives'] and 0 <= amount <= 100, 'Use a valid objective and progress amount.')
            o = b['objectives'][objective]
            require(o['progress'] < o['goal'], 'That objective is already complete.')
            require(all(b['objectives'][key]['progress'] >= b['objectives'][key]['goal'] for key in o['requires']), 'Complete the prerequisite objectives first.')
            require(o['zone'] is None or o['zone'] == foe['zone'] or foe['reach'] == 'scene' or
                    foe['reach'] == 'ranged' and b['zones'][foe['zone']].get(o['zone'], False),
                    'The objective is out of enemy reach. Resolve its permitted movement first.')
            o['progress'] = min(o['goal'], o['progress'] + amount)
        return {'text': f"{foe['name']}: {description}" + (f"\n{objective}: {o['progress']}/{o['goal']}" if objective else '')}

    @operation(gm=True)
    def enemy_attack(self, c, *, enemy, targets, damage=None, description):
        b = self.battle(c, phase='enemies')
        require(not b['incoming'] and not b['bonus_moves'], 'Finish the current attack and all bonus movement choices first.')
        foe = self.foe(b, enemy)
        description = clean(description, 500)
        allowed, penalty = self.enemy_action_budget(foe)
        if not allowed:
            return {'text': f"Capture cancels {foe['name']}'s attack. {foe['actions'] - foe['used']} action(s) remain."}
        users = ids(targets)
        require(all(u in b['positions'] and c.hero(u)['health'] > 0 for u in users), 'Target active heroes in this battle; Down heroes are not attacked again.')
        zones = {b['positions'][u] for u in users}
        require(len(users) == 1 or len(zones) == 1 and ('wide' in foe['traits'] or foe['boss']), 'Group attacks need Wide Attack or a boss, and targets in one zone.')
        require('wide' not in foe['traits'] or foe['boss'] or len(users) <= 2, 'Ordinary Wide Attack hits at most two heroes.')
        require(all(z == foe['zone'] or foe['reach'] == 'scene' or foe['reach'] == 'ranged' and b['zones'][foe['zone']].get(z, False) for z in zones), 'A target is out of enemy reach. Resolve its permitted movement first.')
        base = (1 if len(users) > 1 and 'wide' in foe['traits'] else foe['damage']) if damage is None else damage
        require(0 <= base <= 20, 'Use 0–20 announced damage.')
        return self.incoming(c, users, max(0, base - penalty), description, source=foe['name'])

    @operation(gm=True)
    def hazard(self, c, *, targets, damage, description):
        b = self.battle(c)
        require(b['phase'] in {'heroes', 'enemies'}, 'Start the challenge before resolving a hazard.')
        require(not b['incoming'] and not b['bonus_moves'], 'Finish the current attack and bonus movement choices first.')
        users = ids(targets)
        require(all(u in b['positions'] and c.hero(u)['health'] > 0 for u in users), 'Target active battle participants.')
        require(0 <= damage <= 20, 'Use 0–20 damage.')
        return self.incoming(c, users, damage, clean(description, 500), source='Hazard')

    def incoming(self, c, users, damage, description, *, source):
        b = self.battle(c)
        protected = {}
        # One zone Shield takes priority over individual Guards; they never add together.
        if damage > 0:
            for uid, shield in list(b['shields'].items()):
                zone = shield['zone']
                if zone not in protected and any(b['positions'][u] == zone for u in users):
                    protected[zone] = uid
        attack = {'source': source, 'description': description, 'targets': {}, 'results': {}, 'bonus': {}}
        messages = [f"{source}: {description}"]
        for user in users:
            h = c.hero(user)
            shield = b['positions'][user] in protected
            guarded = damage > 0 and not shield and h['guard'] is not None
            reduced = max(0, damage - (2 if shield or guarded else 0))
            if guarded:
                h['guard'] = None
            attack['targets'][user] = reduced
            if reduced == 0:
                attack['results'][user] = {'result': None, 'damage': 0}
                messages.append(f"{h['hero_name']}: 0 damage; no defense roll or bonus move.")
            else:
                messages.append(f"{h['hero_name']}: defend against {reduced} damage with /battle defend.")
        for uid in protected.values():
            b['shields'].pop(uid, None)
        b['incoming'] = attack
        messages += self.finish_incoming(c)
        return {'title': 'Incoming attack', 'text': '\n'.join(messages)}

    @operation
    def defend(self, c, *, stat, method, user=None, edge=False, pressure=False, talent=False, prep=False, bonus_zone=''):
        b = self.battle(c)
        attack = b['incoming']
        require(attack is not None, 'No attack is waiting for defenses.')
        uid = str(user or c.uid)
        require(uid == c.uid or c.gm and not talent and not prep, 'The GM can roll an absent player’s ordinary defense without spending optional Talent or Prep.')
        require(uid in attack['targets'] and uid not in attack['results'], 'That hero does not have an unresolved defense.')
        h = c.hero(uid)
        zone = zone_id(bonus_zone) if bonus_zone and bonus_zone != 'stay' else bonus_zone
        if zone and zone != 'stay':
            require(self.path(b, b['positions'][uid], zone, maximum=1), 'Choose a connected clear zone for a possible big defense move.')
        return self.staged(c, h, stat=stat, scope='defense', method=method,
            effect={'kind': 'defense', 'bonus_zone': zone}, edge=edge, pressure=pressure,
            talent=talent, prep=prep, rescue=True)

    def finish_incoming(self, c):
        b = c.state['battle']
        attack = b['incoming']
        if not attack or len(attack['results']) != len(attack['targets']):
            return []
        messages = ['The whole attack is resolved.']
        for user, destination in attack['bonus'].items():
            if destination == 'stay':
                continue
            if destination and self.path(b, b['positions'][user], destination, maximum=1):
                b['positions'][user] = destination
                messages.append(f"{c.hero(user)['hero_name']} takes the big defense move to {destination}.")
            else:
                b['bonus_moves'][user] = True
                if destination:
                    messages.append(f"{c.hero(user)['hero_name']}'s chosen route is no longer clear.")
                messages.append(f"{c.hero(user)['hero_name']}: /battle bonus to move or choose stay before the next enemy action.")
        b['incoming'] = None
        return messages

    @operation
    def bonus_move(self, c, *, zone='stay', user=None):
        b = self.battle(c)
        uid = str(user or c.uid)
        require(uid == c.uid or c.gm and zone == 'stay', 'Only the player can choose their bonus movement; the GM can choose stay for an absent player.')
        require(uid in b['bonus_moves'], 'No big defense move is waiting for that hero.')
        if zone != 'stay':
            zone = zone_id(zone)
            require(self.path(b, b['positions'][uid], zone, maximum=1), 'Choose one connected clear zone.')
            b['positions'][uid] = zone
        del b['bonus_moves'][uid]
        return {'text': f"{c.hero(uid)['hero_name']} {'stays in place' if zone == 'stay' else 'moves to ' + zone}."}

    def apply_effect(self, c, h, effect, result, assisted):
        kind = effect['kind']
        if kind == 'check':
            return ['Miss or setback: the GM resolves the stated risk.' if result < 4 else
                    'Big success: the GM gives the action’s fitting extra benefit.' if result >= 8 else 'Success: the stated action works.']
        b = self.battle(c)
        big, hit = result >= 8, result >= 4
        if kind == 'attack':
            messages = []
            for key in effect['targets']:
                foe = self.foe(b, key)
                damage = (4 if big else 3) if effect['move'] == 'heavy_hit' else (2 if big else 1) if effect['move'] == 'burst' else (3 if big else 2)
                helped = assisted and key == effect['assisted_target']
                damage = 0 if not hit else max(0, damage + int(helped) - int('armor' in foe['traits'] and not helped))
                foe['health'] = max(0, foe['health'] - damage)
                messages.append(f"{foe['name']}: {damage} damage; Health {foe['health']}/{foe['maximum']}" + ('; defeated, loses its actions.' if foe['health'] == 0 else '.'))
            return messages
        if kind == 'capture':
            foe = self.foe(b, effect['enemy'])
            if hit:
                foe['capture'] = max(foe['capture'], 8 if big else 4)
            return [f"{foe['name']}: " + ('next action is cancelled; a boss loses at most one action per round.' if big else 'cannot move until its next action ends; that action has −1 damage.' if hit else 'Capture misses.')]
        if kind == 'task':
            key = effect['objective']
            if not key:
                return ['Big success: GM resolves the fitting extra benefit.' if big else 'Success: GM resolves the stated effect.' if hit else 'Miss: GM resolves the stated consequence.']
            o = b['objectives'][key]
            amount = (3 if big else 2) if effect['boost'] else (2 if big else 1)
            amount = amount if hit else 0
            o['progress'] = min(o['goal'], o['progress'] + amount)
            return [f"{o['name']}: +{amount} progress; {o['progress']}/{o['goal']}." + (' Complete.' if o['progress'] == o['goal'] else '')]
        if kind == 'move':
            if hit:
                for user in [h['user_id']] + effect['passengers']:
                    b['positions'][user] = effect['zone']
            return [f"Moved to {effect['zone']}." if hit else 'The risky move fails. The GM resolves the stated risk.']
        if kind == 'defense':
            attack = b['incoming']
            uid = h['user_id']
            require(attack and uid in attack['targets'] and uid not in attack['results'], 'This defense is no longer valid.')
            damage = 0 if hit else attack['targets'][uid]
            h['health'] = max(0, h['health'] - damage)
            attack['results'][uid] = {'result': result, 'damage': damage}
            if big:
                attack['bonus'][uid] = effect['bonus_zone']
            messages = [f"{h['hero_name']}: {'avoids the attack' if hit else str(damage) + ' damage'}; Health {h['health']}/6."]
            return messages + self.finish_incoming(c)
        raise ValueError(f'Unknown effect kind: {kind}')
