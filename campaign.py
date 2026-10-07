"""Character creation, missions, attendance, preparation, and shared growth."""

import copy
import re
import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .core import operation
from .dice import parse_faces
from .faq import BY_KEY, CATEGORIES, response as faq_response
from .rules import DICE, ITEMS, MOVES, STATS, TALENTS, GameError, clean, require


def new_hero(user, name, hero_name, age, goal, cooperation):
    return {
        'user_id': str(user), 'name': clean(name, 80), 'hero_name': clean(hero_name, 80),
        'age': age, 'goal': clean(goal, 500), 'cooperation': clean(cooperation, 500),
        'stats': dict(zip(STATS, (10, 8, 8, 6))), 'increases_applied': 0,
        'quirk': None, 'approved': False, 'submitted': False,
        'health': 6, 'energy': 3, 'plus_used': False, 'talent_used': False, 'item_used': False,
        'moves': ['heavy_hit', 'rescue_boost'], 'move_names': {}, 'talent': 'strong_spirit', 'item': None,
        'known_moves': ['heavy_hit', 'rescue_boost'], 'known_talents': ['strong_spirit'], 'known_items': [],
        'training': 0, 'training_weeks': {}, 'prep': None, 'prep_offer': None, 'unlock_requests': [],
        'help': None, 'guard': None, 'smoke': False, 'healed': False, 'cheered': False,
        'gear': 'Costume and communicator', 'trackers': {},
    }


def week_key(now, settings):
    local = now.astimezone(ZoneInfo(settings['timezone']))
    day = local.date()
    if local < datetime.combine(day, time(settings['reset_hour']), tzinfo=local.tzinfo):
        day -= timedelta(days=1)
    return (day - timedelta(days=(day.weekday() - settings['reset_weekday']) % 7)).isoformat()


class Campaign:
    @operation(pending=True)
    def faq(self, c, *, question='', category='all'):
        return faq_response(question,category,c.state.get('faq',{}))

    @operation(gm=True)
    def faq_add(self, c, *, key, question, answer, category='campaign'):
        key = clean(key,32).lower()
        require(re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',key), 'Use a FAQ ID such as session-times or dorm_rules.')
        require(key not in BY_KEY, 'That ID belongs to a core rule answer. Choose a different campaign FAQ ID.')
        require(category in CATEGORIES and category != 'all', 'Choose a specific FAQ category.')
        value = {'category':category,'question':clean(question,150),'answer':clean(answer,2000)}
        custom = c.state.setdefault('faq',{})
        require(key in custom or len(custom) < 50, 'Keep at most 50 campaign FAQs. Update or remove an existing answer.')
        updated = key in custom
        custom[key] = value
        return {'title':'Campaign FAQ '+('updated' if updated else 'added'),
                'text':f'Players can read this answer with /faq question:{key}. It is saved for this server.'}

    @operation(gm=True)
    def faq_remove(self, c, *, key):
        key = clean(key,32).lower()
        custom = c.state.get('faq',{})
        require(key in custom, 'That campaign FAQ does not exist. Core rule answers cannot be removed.')
        del custom[key]
        return {'text':f'Campaign FAQ {key} removed.'}

    @operation
    def hero_create(self, c, *, name, hero_name, age=18, goal, cooperation):
        require(c.uid not in c.state['characters'], "You already have a hero. Use /hero edit instead.")
        require(18 <= age <= 150, "Use an adult age from 18–150 for this college AU.")
        c.state['characters'][c.uid] = new_hero(c.uid, name, hero_name, age, goal, cooperation)
        return {'title': 'Hero draft created', 'text': 'Next: /hero stats, /hero quirk, /hero moves, /hero talent, then /hero submit. Shared stat increases are available through /hero upgrade.'}

    @operation
    def hero_edit(self, c, *, name, hero_name, age, goal, cooperation):
        c.quiet()
        require(not c.state['mission'], "Edit your character between missions.")
        h = c.hero(approved=False)
        require(18 <= age <= 150, "Use an adult age from 18–150.")
        h.update(name=clean(name, 80), hero_name=clean(hero_name, 80), age=age,
                 goal=clean(goal, 500), cooperation=clean(cooperation, 500))
        return {'text': 'Character details updated.'}

    @operation
    def hero_stats(self, c, *, power, speed, wits, heart):
        c.downtime()
        h = c.hero(approved=False)
        require(not h['approved'], "An approved hero raises stats through /hero upgrade. Ask the GM to reopen a draft to rearrange stats.")
        values = [power, speed, wits, heart]
        require(all(x in DICE for x in values), "Use d6, d8, d10, or d12.")
        if h['increases_applied'] == 0:
            require(sorted(values) == [6, 8, 8, 10], "Starting stats must use d10, d8, d8, and d6 exactly once.")
        else:
            require(sum(DICE.index(x) for x in values) == 4 + h['increases_applied'], "The assignment must match your earned stat increases.")
        h['stats'] = dict(zip(STATS, values))
        h['submitted'] = False
        return {'text': 'Stats saved. Next: /hero quirk.'}

    @operation
    def hero_quirk(self, c, *, name, ability, ordinary, reach, cannot, limits):
        c.downtime()
        require(reach in {'touch', 'ranged'}, "Choose touch or ranged reach.")
        h = c.hero(approved=False)
        h['quirk'] = {'name': clean(name, 80), 'ability': clean(ability, 500), 'ordinary': clean(ordinary),
                      'reach': reach, 'cannot': clean(cannot), 'limits': clean(limits)}
        h['approved'] = h['submitted'] = False
        return {'text': 'Quirk card saved. Your GM will review its abilities, limits, and chosen moves. Next: /hero moves.'}

    @operation
    def hero_moves(self, c, *, first, second, first_name='', second_name=''):
        c.downtime()
        h = c.hero(approved=False)
        require(first in MOVES and second in MOVES and first != second, "Choose two different move templates.")
        require(not h['approved'] and h['training'] == 0 and not h['unlock_requests'], "Use /hero prepare for learned moves; unlock new moves with Training.")
        require(len(h['known_moves']) == 2, "Use /hero prepare for an established character.")
        h['moves'] = h['known_moves'] = [first, second]
        h['move_names'] = {first: clean(first_name, 80, empty=True) or MOVES[first]['name'],
                           second: clean(second_name, 80, empty=True) or MOVES[second]['name']}
        h['submitted'] = False
        return {'text': 'Two starting moves saved. Next: /hero talent.'}

    @operation
    def hero_talent(self, c, *, talent):
        c.downtime()
        h = c.hero(approved=False)
        require(talent in TALENTS, "Choose a listed Talent.")
        require(not h['approved'] and len(h['known_talents']) == 1 and h['training'] == 0, "Use /hero prepare for an established character.")
        h['talent'] = talent
        h['known_talents'] = [talent]
        h['submitted'] = False
        return {'text': 'Talent saved. Use /hero gear if desired, then /hero submit.'}

    @operation
    def hero_gear(self, c, *, gear):
        c.quiet()
        c.hero(approved=False)['gear'] = clean(gear)
        return {'text': 'Ordinary gear saved. It grants no automatic stat or enhanced-item bonuses.'}

    @operation
    def hero_submit(self, c):
        h = c.hero(approved=False)
        require(h['quirk'], "Write your Quirk with /hero quirk first.")
        h['submitted'] = True
        return {'title': f"{h['hero_name']} is ready for review", 'hero': h, 'text': 'GM: review the Quirk and move fit, then use /gm approve.'}

    @operation(pending=True)
    def hero_sheet(self, c, *, user=None):
        h = c.hero(user, approved=False)
        return {'title': h['hero_name'], 'hero': h, 'pending_increases': c.state['milestones'] - h['increases_applied'],
                'weekly_training': h['training_weeks'].get(week_key(self.clock(), c.state['settings']), 0)}

    @operation
    def hero_upgrade(self, c, *, stat):
        c.downtime()
        h = c.hero(approved=False)
        require(stat in STATS and h['stats'][stat] < 12, "Choose a stat below d12.")
        require(h['increases_applied'] < c.state['milestones'], "No shared stat increases are waiting.")
        h['stats'][stat] = DICE[DICE.index(h['stats'][stat]) + 1]
        h['increases_applied'] += 1
        return {'text': f"{stat.title()} is now d{h['stats'][stat]}."}

    @operation
    def hero_unlock(self, c, *, kind, option):
        c.downtime()
        h = c.hero()
        table, field = self.unlock_table(kind)
        require(option in table, "Choose a listed option.")
        require(option not in h[field], "You already know that option.")
        require(h['training'] >= 3, "You need 3 Training.")
        require({'kind': kind, 'option': option} not in h['unlock_requests'], "That request is already waiting.")
        require(len(h['unlock_requests']) < 10, "Finish your existing requests first.")
        h['unlock_requests'].append({'kind': kind, 'option': option})
        return {'text': f"Requested {option}. The GM confirms it with /gm unlock; 3 Training is spent on approval."}

    @staticmethod
    def unlock_table(kind):
        require(kind in {'move', 'talent', 'item'}, "Choose move, talent, or item.")
        return {'move': (MOVES, 'known_moves'), 'talent': (TALENTS, 'known_talents'), 'item': (ITEMS, 'known_items')}[kind]

    @operation(gm=True)
    def unlock_approve(self, c, *, user, kind, option, approve=True):
        c.downtime()
        h = c.hero(user)
        request = {'kind': kind, 'option': option}
        require(request in h['unlock_requests'], "That hero has not requested this option.")
        if approve:
            table, field = self.unlock_table(kind)
            require(option in table and option not in h[field], "That option cannot be unlocked.")
            require(h['training'] >= 3, "The hero no longer has 3 Training.")
            h['training'] -= 3
            h[field].append(option)
        h['unlock_requests'].remove(request)
        return {'text': f"{h['hero_name']}: request {'approved; spent 3 Training' if approve else 'declined; no Training spent'}."}

    @operation
    def hero_prepare(self, c, *, first, second, talent, item='none'):
        c.downtime()
        h = c.hero()
        require(first != second and first in h['known_moves'] and second in h['known_moves'], "Prepare two different known moves.")
        require(talent in h['known_talents'], "Prepare a known Talent.")
        require(item == 'none' or item in h['known_items'], "Prepare one known item, or none.")
        h.update(moves=[first, second], talent=talent, item=None if item == 'none' else item)
        return {'text': 'Mission choices prepared. Used marks refresh at the next scene, not from swapping options.'}

    @operation
    def hero_tracker(self, c, *, name, value=''):
        h = c.hero(approved=False)
        name = clean(name, 40)
        value = clean(value, 120, empty=True)
        if not value:
            require(name in h['trackers'], 'That tracker does not exist. Supply a value to create it.')
            del h['trackers'][name]
            return {'text': f"Tracker {name} removed."}
        require(name in h['trackers'] or len(h['trackers']) < 20, "Use at most 20 custom trackers.")
        h['trackers'][name] = value
        return {'text': f"Tracker {name} saved. Custom trackers are notes and do not change the core rules."}

    @operation
    def hero_prep(self, c, *, replace=False):
        h = c.hero()
        require(h.get('prep_offer'), 'No new Prep choice is waiting.')
        if replace:
            h['prep'] = h['prep_offer']
        h['prep_offer'] = None
        return {'text': 'Prep choice saved: ' + (h['prep']['theme'] if h['prep'] else 'none') + '. Hold at most one.'}

    @operation
    def ordinary_help(self, c, *, user, task, method):
        c.quiet()
        h, ally = c.hero(), c.hero(user)
        require(c.uid != str(user) and h['health'] > 0, 'A conscious hero can Help a teammate, not themselves.')
        require(task in {'check', 'rescue', 'investigation', 'escape', 'hide'}, 'Choose the named check task.')
        self.expire_help(c)
        ally['help'] = {'source': c.uid, 'task': task, 'method': clean(method, 500)}
        return {'text': f"{h['hero_name']} Helps {ally['hero_name']} with {task}. Next matching check gets Edge; ends when the helper acts again or the scene changes."}

    @operation(gm=True)
    def configure(self, c, *, gm_role_id=None, timezone='America/New_York', reset_weekday=0, reset_hour=0):
        require(c.actor.user_id == self.owner_id, "Only the bot creator can change GM access or weekly reset settings.")
        require(not c.state['session'], "End the current session before changing reset settings.")
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise GameError("Use a timezone such as America/New_York or Etc/UTC.") from exc
        require(0 <= reset_weekday <= 6 and 0 <= reset_hour <= 23, "Weekday is 0–6 (Monday–Sunday); hour is 0–23.")
        c.state['settings'].update(gm_role_id=gm_role_id, timezone=timezone, reset_weekday=reset_weekday, reset_hour=reset_hour)
        return {'text': 'Server configuration and weekly reset saved.'}

    @operation(gm=True)
    def approve(self, c, *, user, approve=True):
        c.quiet()
        h = c.hero(user, approved=False)
        require(not approve or h['submitted'] and h['quirk'], "The player must submit a completed Quirk card first.")
        h['approved'] = approve
        return {'text': f"{h['hero_name']} {'approved' if approve else 'reopened as a draft'}."}

    @operation(gm=True)
    def resource(self, c, *, user, resource, value, reason):
        h = c.hero(user, approved=False)
        require(resource in {'health', 'energy', 'training', 'plus_used', 'talent_used', 'item_used'}, "Choose a tracked core resource.")
        maximum = {'health': 6, 'energy': 3, 'training': 10000, 'plus_used': 1, 'talent_used': 1, 'item_used': 1}[resource]
        require(type(value) is int and 0 <= value <= maximum, f"Use 0–{maximum}.")
        h[resource] = bool(value) if resource.endswith('_used') else value
        return {'text': f"GM set {h['hero_name']}'s {resource} to {value}. Reason: {clean(reason, 300)}"}

    @operation(gm=True, pending=True)
    def roster(self, c):
        return {'title': 'Class roster', 'text': '\n'.join(f"{h['hero_name']} · {uid} · {'approved' if h['approved'] else 'draft'} · HP {h['health']}/6 · E {h['energy']}/3 · Training {h['training']}" for uid, h in c.state['characters'].items()) or 'No heroes yet.'}

    @operation(gm=True)
    def milestone(self, c, *, reason):
        c.quiet()
        require(c.state['milestones'] < 8, "All four stats reach d12 after eight shared increases. Approve Quirk permissions through the story instead.")
        c.state['milestones'] += 1
        return {'text': f"Shared stat increase #{c.state['milestones']} for the whole roster, including returning and new heroes. Use /hero upgrade. Reason: {clean(reason, 300)}"}

    @operation(gm=True)
    def rest(self, c, *, user=None):
        c.quiet()
        heroes = [c.hero(user)] if user else list(c.state['characters'].values())
        for h in heroes:
            h['health'], h['energy'] = 6, 3
        return {'text': 'Ten safe minutes: Health and Energy restored. Other refresh times are unchanged.'}

    @operation(gm=True)
    def assist(self, c, *, user):
        c.quiet()
        h = c.hero(user)
        require(h['health'] == 0, "Basic assistance only wakes a Down hero.")
        h['health'] = 1
        return {'text': f"{h['hero_name']} wakes at 1 Health."}

    @operation(gm=True)
    def scene_new(self, c, *, name):
        c.quiet()
        self.refresh_scene(c.state)
        return {'text': f"New scene: {clean(name, 120)}. Talent and special item uses refreshed; Health and Energy unchanged."}

    @staticmethod
    def refresh_scene(state):
        state['scene'] += 1
        for h in state['characters'].values():
            h.update(talent_used=False, item_used=False, smoke=False, help=None, guard=None)

    @operation(gm=True)
    def session_start(self, c, *, name, side=False, prep_theme=''):
        require(not c.state['session'], "End the existing official session first.")
        require(not side or bool(prep_theme.strip()), "A side session needs a Prep theme.")
        c.state['session'] = {'id': uuid.uuid4().hex, 'name': clean(name, 120), 'side': side,
                              'prep_theme': clean(prep_theme, 120, empty=True), 'week': week_key(self.clock(), c.state['settings']),
                              'participants': [], 'started': self.clock().isoformat()}
        for h in c.state['characters'].values():
            h['plus_used'] = False
        return {'text': f"Official {'side' if side else 'main'} session started. Plus Ultra refreshed. GM: mark meaningful participation with /session mark."}

    @operation(gm=True)
    def session_mark(self, c, *, user, participated=True):
        session = c.state['session']
        require(session is not None, "Start an official session first.")
        h = c.hero(user, approved=participated)
        uid = str(user)
        if participated and uid not in session['participants']:
            session['participants'].append(uid)
        if not participated and uid in session['participants']:
            session['participants'].remove(uid)
        return {'text': f"Participation {'marked' if participated else 'removed'} for {h['hero_name']}."}

    @operation(gm=True)
    def session_end(self, c, *, summary):
        session = c.state['session']
        require(session is not None, "No official session is open.")
        messages = []
        for uid in session['participants']:
            h = c.hero(uid, approved=False)
            earned = h['training_weeks'].get(session['week'], 0)
            award = 1 if earned < 2 else 0
            h['training'] += award
            h['training_weeks'][session['week']] = earned + award
            if session['side']:
                offer = {'theme': session['prep_theme'], 'mission': None}
                if h['prep']:
                    h['prep_offer'] = offer
                else:
                    h['prep'] = offer
            messages.append(f"{h['hero_name']}: +{award} Training" + (' (weekly cap reached)' if not award else '') +
                            (f"; Prep: {session['prep_theme']} for the next main mission" + ('; /hero prep chooses which Prep to keep' if h.get('prep_offer') else '') if session['side'] else ''))
        record = dict(session, summary=clean(summary, 1500), ended=self.clock().isoformat(), awards=messages)
        c.state['session_log'].append(record)
        c.state['session_log'] = c.state['session_log'][-100:]
        c.state['session'] = None
        return {'title': f"Session finished: {session['name']}", 'text': '\n'.join(messages + [record['summary']])}

    @operation(pending=True)
    def session_log(self, c):
        return {'title': 'Recent sessions', 'text': '\n\n'.join(x['name'] + '\n' + x['summary'] for x in c.state['session_log'][-5:]) or 'No completed sessions.'}

    @operation(gm=True)
    def mission_start(self, c, *, name):
        c.quiet()
        require(not c.state['mission'], "End the existing main mission first.")
        mission = {'id': uuid.uuid4().hex, 'name': clean(name, 120)}
        c.state['mission'] = mission
        for h in c.state['characters'].values():
            if h['prep'] and h['prep']['mission'] is None:
                h['prep']['mission'] = mission['id']
            if h.get('prep_offer') and h['prep_offer']['mission'] is None:
                h['prep_offer']['mission'] = mission['id']
        return {'text': f"Main mission started: {mission['name']}. Prepared choices are locked; waiting Prep is assigned to this mission."}

    @operation(gm=True)
    def mission_end(self, c):
        c.quiet()
        require(c.state['mission'], "No main mission is open.")
        mid = c.state['mission']['id']
        for h in c.state['characters'].values():
            if h['prep'] and h['prep']['mission'] == mid:
                h['prep'] = None
            if h.get('prep_offer') and h['prep_offer']['mission'] == mid:
                h['prep_offer'] = None
        c.state['mission'] = None
        return {'text': 'Main mission finished. Its unused Prep expired; prepared choices may be changed in downtime.'}

    @operation(gm=True)
    def dice_create(self, c, *, name, faces):
        name = name.lower().strip()
        require(re.fullmatch(r'[a-z][a-z0-9_]{0,31}', name), 'Use a name such as weather or rescue_kit.')
        require(name in c.state['dice'] or len(c.state['dice']) < 100, 'Keep at most 100 custom dice per server.')
        c.state['dice'][name] = parse_faces(faces)
        return {'text': f"Saved d[{name}] with {len(c.state['dice'][name])} weighted faces. Roll it with /dice roll expression:1d[{name}]."}

    @operation(pending=True)
    def dice_list(self, c):
        return {'title': 'Custom dice', 'text': '\n'.join(f"d[{n}]: {json_faces[:180]}" for n, f in c.state['dice'].items()
                   for json_faces in [str(f)]) or 'No named dice yet. Numbered dice work immediately: 1d17, 3d100, etc.'}

    @operation(gm=True)
    def dice_remove(self, c, *, name):
        require(name in c.state['dice'], 'That die does not exist.')
        del c.state['dice'][name]
        return {'text': 'Custom die removed.'}
