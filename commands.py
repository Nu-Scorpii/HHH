"""Static slash-command definitions. Names and choices are data, never eval."""

import inspect
from dataclasses import dataclass, field
import discord
from .rules import STATS, MOVES, TALENTS, ITEMS, ENEMIES
from .faq import CATEGORIES

MISSING = inspect.Parameter.empty
STAT = {s: s.title() for s in STATS}
MOVE = {k: v['name'] for k, v in MOVES.items()}
TALENT = {k: v[0] for k, v in TALENTS.items()}
ITEM = {'none': 'None', **{k: k.replace('_', ' ').title() for k in ITEMS}}
TASK = {x: x.title() for x in ['task', 'attack', 'defense', 'capture', 'rescue', 'investigation', 'escape', 'hide']}
CHECK = {x: x.title() for x in ['check', 'rescue', 'investigation', 'escape', 'hide']}


@dataclass
class Option:
    name: str
    annotation: object = str
    default: object = MISSING
    description: str = ''
    choices: dict = field(default_factory=dict)


def p(name, annotation=str, default=MISSING, description='', choices=None):
    return Option(name, annotation, default, description or name.replace('_', ' ').capitalize(), choices or {})


def member(name='user', default=MISSING):
    return p(name, discord.Member, default, 'Choose a player')


def stat(default=MISSING):
    return p('stat', default=default, choices=STAT, description='Stat agreed with the GM before rolling')


def method(default='Agreed action.'):
    return p('method', default=default, description='Your goal and how your hero attempts it')


def bonuses():
    return [p('edge', bool, False, 'GM-approved Edge; extra sources never stack'),
            p('pressure', bool, False, 'GM-announced Pressure'),
            p('talent', bool, False, 'Spend your qualifying Talent before rolling'),
            p('prep', bool, False, 'Spend a fitting Prep for this main mission before rolling')]


@dataclass
class Spec:
    path: str
    operation: str
    description: str
    options: list = field(default_factory=list)
    private: bool = False
    special: str = ''


SPECS = [
    Spec('help', '', 'Learn the game and find the bot commands', [p('topic', default='quick', choices={x: x.title() for x in ['quick','create','quirks','rolls','battle','training','spar','moves','talents','items','handbook','gm','commands']})], True, 'help'),
    Spec('faq', 'faq', 'Browse or search common questions and campaign answers', [p('question',default='',description='Search words or a FAQ ID, such as energy or plus-ultra'),p('category',default='all',choices=CATEGORIES),p('share',bool,False,'Post the answer publicly instead of privately')], True),
    Spec('battle resolve', 'roll_decision', 'Show a waiting roll, keep it, or choose Plus Ultra', [p('choice',default='show',choices={'show':'Show waiting roll','keep':'Keep result','plus':'Plus Ultra: costs 2 Health'})]),
    Spec('check', 'check', 'Roll your tracked stat outside a battle', [stat(),method(),p('task',default='check',choices=CHECK), *bonuses(), p('rescue',bool,False,'This directly saves or protects someone')]),
    Spec('hero heal', 'mend', 'Use prepared Mend, in combat or outside it', [member()]),
    Spec('hero item', 'item_use', 'Use your prepared Smoke, Scanner, or Medical Patch', [member(default=None),p('question',default='',description='Field Scanner question for the GM')]),
    Spec('hero create', '', 'Create a student with a guided form', [], True, 'create'),
    Spec('hero roll', 'hero_roll', 'Roll and save all four starting stats in one command'),
    Spec('hero build', 'hero_build', 'Choose two moves, a Talent, and a learned item', [p('first',default='',choices=MOVE),p('second',default='',choices=MOVE),p('talent',default='',choices=TALENT),p('item',default='',choices=ITEM)], True),
    Spec('hero help', 'team_help', 'Help an ally, during a battle or outside it', [member(),method(),p('task',default='',choices={'check':'Check',**TASK}),p('objective',default='')]),
    Spec('hero edit', '', 'Edit your student’s name, age, goal, and team connection', [], True, 'edit'),
    Spec('hero stats', 'hero_stats', 'Assign d10, d8, d8, and d6 to your starting stats', [p(s,int,choices={n:f'd{n}' for n in [6,8,10,12]}) for s in STATS], True),
    Spec('hero quirk', '', 'Write your power, ordinary uses, reach, and limits', [p('name',description='Your Quirk name'),p('reach',default='ranged',choices={'touch':'Touch: own zone','ranged':'Ranged: own or connected zone'})], True, 'quirk'),
    Spec('hero submit', 'hero_submit', 'Send your finished character card for GM approval'),
    Spec('hero sheet', 'hero_sheet', 'View your current character, stats, and resources', [member(default=None),p('share',bool,False,'Post the sheet publicly instead of privately'),p('details',bool,False,'Show the complete sheet instead of the short card')], True),
    Spec('hero upgrade', 'hero_upgrade', 'Spend a waiting shared stat increase', [stat()]),
    Spec('hero unlock', 'hero_unlock', 'Request a new move, Talent, or item for 3 Training', [p('kind',choices={k:k.title() for k in ['move','talent','item']}),p('option',description='Option ID from /help topic:moves, talents, or items')]),
    Spec('hero notes', 'hero_tracker', 'Save a custom tracker, or leave its value blank to delete it', [p('name'),p('value',default='',description='Tracker value; leave blank to delete this tracker')], True),
    Spec('hero prep', 'hero_prep', 'Choose whether to replace held Prep with a new offer', [p('replace',bool,False,'False keeps the existing Prep; true takes the new offer')]),
    Spec('roll', 'roll', 'Roll any dice and optionally add bonus points', [
        p('dice',default='1d20',description='Dice to roll: 1d20, 2d17+1d8-3, or 2d[custom]'),
        p('bonus',int,0,'Extra points added to the total; negative numbers subtract'),
        p('keep',default='all',choices={'all':'All: add every die','high':'Highest: keep the best die','low':'Lowest: keep the worst die'}),
        p('faces',default='',description='Optional JSON faces for d[custom]: [0,1,1,5] or ["sun","rain"]')]),
    Spec('gm battle create', 'battle_create', 'GM: create a battle or rescue challenge', [p('name'),p('participants',description='Hero mentions or user IDs, separated by commas'),p('starting_zone',default='start')]),
    Spec('gm battle start', 'battle_start', 'GM: begin round 1 after announcing enemy intentions'),
    Spec('battle status', 'battle_status', 'Read current zones, turns, Health, enemies, and objectives'),
    Spec('gm battle panel', 'battle_status', 'GM: post a live battle panel that updates after commands', [], False, 'panel'),
    Spec('battle end', 'battle_end', 'End your turn, including any unused movement or action'),
    Spec('battle move', 'battle_move', 'Move, Rush, or use Rapid Move on a permitted route', [p('zone'),p('mode',default='normal',choices={'normal':'Free move','rush':'Rush: uses action','rapid':'Rapid Move: 1 Energy'}),p('method',default='Move along a clear route.'),p('carry',default='',description='One cooperative hero ID, or two with Rescue Harness'),p('harness',bool,False),p('grapple',bool,False),p('risky',bool,False,'A risky crossing uses your action and a roll'),p('stat',default='speed',choices=STAT),p('pressure',bool,False),p('talent',bool,False),p('prep',bool,False)]),
    Spec('battle attack', 'strike', 'Attack with a basic strike, your prepared move', [p('targets',description='Enemy IDs: e1, or e1,e2,e3 for Burst'),stat('power'),method(),p('move',default='basic',choices={'basic':'Ordinary Attack',**{k:MOVE[k] for k in ['heavy_hit','burst','long_reach','capture']}}),*bonuses()]),
    Spec('battle task', 'battle_task', 'Work on an objective or another risky task', [stat('wits'),method(),p('objective',default=''),p('boost',bool,False,'Use prepared Rescue Boost for 1 Energy'),*bonuses(),p('rescue',bool,False),p('task_type',default='task',choices={k:v for k,v in TASK.items() if k not in ['attack','defense','capture']})]),
    Spec('battle automatic', 'battle_automatic', 'Spend an ordinary action on an agreed task needing no roll', [method()]),
    Spec('battle guard', 'protect', 'Guard one person or use your prepared Shield', [member(default=None),p('kind',default='guard',choices={'guard':'Guard: one person','shield':'Shield: your zone, costs 1 Energy'}),p('method',default='Protect them from the announced attack.')]),
    Spec('battle recover', 'battle_recover', 'Use your action to restore 1 Energy'),
    Spec('battle defend', 'defend', 'Roll defense against the incoming attack', [stat('speed'),method(),member(default=None),*bonuses(),p('bonus_zone',default='',description='Optional big defense destination, or stay')]),
    Spec('battle bonus', 'bonus_move', 'Choose your earned big defense move, or stay', [p('zone',default='stay'),member(default=None)]),
    Spec('gm battle finish', 'battle_finish', 'GM: finish a fight or challenge and record its outcome', [p('outcome')]),
    Spec('gm enemy add', 'enemy_add', 'GM: create a Minion, Rival, Elite, or Boss', [p('name'),p('template',choices={k:k.title() for k in ENEMIES}),p('zone'),p('trait',default='none',choices={k:k.title() for k in ['none','armor','protector','wide','fast']}),p('reach',default='touch',choices={'touch':'Own zone','ranged':'Own or connected zone','scene':'Anywhere visible in scene'})]),
    Spec('gm enemy edit', 'edit_enemy', 'GM: set enemy Health, damage, or action count', [p('enemy'),p('health',int,None),p('damage',int,None),p('actions',int,None),p('trait',default='',choices={k:k.title() for k in ['armor','protector','wide','fast']}),p('enabled',bool,True)]),
    Spec('gm enemy intent', 'enemy_intent', 'GM: announce the enemy’s reliable intention', [p('enemy'),p('intention')]),
    Spec('gm enemy move', 'enemy_move', 'GM: resolve permitted enemy movement', [p('enemy'),p('zone')]),
    Spec('gm enemy attack', 'enemy_attack', 'GM: spend an enemy action and request player defenses', [p('enemy'),p('targets',description='Active hero IDs or mentions, separated by commas'),p('description',description='Announced attack and fictional effect'),p('damage',int,None,'Announced damage override; default uses the enemy card')]),
    Spec('gm enemy action', 'enemy_action', 'GM: resolve or skip an enemy action, including objectives', [p('enemy'),p('description'),p('objective',default=''),p('amount',int,1)]),
    Spec('gm objective add', 'objective_add', 'GM: create a public progress objective and its prerequisites', [p('key'),p('name'),p('goal',int,4),p('zone',default=''),p('prerequisites',default='',description='Existing objective IDs, separated by commas')]),
    Spec('gm objective tick', 'objective_tick', 'GM: correct or advance objective progress', [p('key'),p('amount',int),p('reason')]),
    Spec('gm objective danger', 'danger', 'GM: announce a Danger track and its consequence', [p('name',default=''),p('consequence',default=''),p('goal',int,3),p('active',bool,True)]),
    Spec('gm session start', 'session_open', 'GM: start one official main or side session', [p('name'),p('side',bool,False),p('prep_theme',default='',description='Required theme for an official side session'),p('participants',default='',description='Optional player mentions/IDs; mark these attendees immediately')]),
    Spec('gm session mark', 'session_mark', 'GM: mark or remove a player’s meaningful participation', [member(),p('participated',bool,True)]),
    Spec('gm session end', 'session_end', 'GM: record the session and award capped Training and Prep', [p('summary')]),
    Spec('gm session log', 'session_log', 'Read the latest session records'),
    Spec('gm mission start', 'mission_start', 'GM: lock prepared choices and assign held Prep to a main mission', [p('name')]),
    Spec('gm mission end', 'mission_end', 'GM: finish a mission and expire its unused Prep'),
    Spec('gm scene', 'scene_new', 'GM: begin a new meaningful scene and refresh Talents and items', [p('name')]),
    Spec('spar start', 'spar_start', 'Invite another student to a friendly best-of-three spar', [member('opponent')]),
    Spec('spar join', 'spar_join', 'Accept your friendly spar invitation'),
    Spec('spar roll', 'spar_roll', 'Roll one spar exchange; ties reroll without new costs', [stat(),method(),p('enhanced',bool,False,'Spend 1 Energy for Edge through a fitting Quirk approach'),*bonuses()]),
    Spec('spar status', 'spar_status', 'Read the current spar score'),
    Spec('spar cancel', 'spar_cancel', 'Cancel your spar; previous costs remain spent'),
    Spec('gm config', 'configure', 'Creator: configure GM access, timezone, and weekly reset', [p('gm_role_id',discord.Role,None,'Role allowed to use GM commands'),p('timezone',default='America/New_York'),p('reset_weekday',int,0,'0=Monday through 6=Sunday'),p('reset_hour',int,0,'Local hour 0–23')], True),
    Spec('gm approve', 'approve', 'GM: approve a submitted hero or reopen their draft', [member(),p('approve',bool,True)]),
    Spec('gm unlock', 'unlock_approve', 'GM: approve or decline a requested Training unlock', [member(),p('kind',choices={k:k.title() for k in ['move','talent','item']}),p('option'),p('approve',bool,True)]),
    Spec('gm resource', 'resource', 'GM: correct a tracked resource with a public reason', [member(),p('resource',choices={k:k.replace('_',' ').title() for k in ['health','energy','training','plus_used','talent_used','item_used']}),p('value',int),p('reason')]),
    Spec('gm roster', 'roster', 'GM: inspect the class roster', [], True),
    Spec('gm milestone', 'milestone', 'GM: grant the whole roster one shared stat increase', [p('reason')]),
    Spec('gm rest', 'rest', 'GM: confirm ten safe minutes and restore Health and Energy', [member(default=None)]),
    Spec('gm assist', 'assist', 'GM: wake a Down hero at 1 Health between encounters', [member()]),
    Spec('gm zone add', 'zone_add', 'GM: create a zone with clear or blocked connections', [p('name'),p('connect_to',default='',description='Existing zone IDs separated by commas'),p('clear',bool,True)]),
    Spec('gm zone link', 'zone_link', 'GM: open or block a connection between two zones', [p('first'),p('second'),p('clear',bool,True)]),
    Spec('gm zone position', 'position', 'GM: correct a hero or enemy position', [p('target',description='Hero user ID or enemy ID'),p('zone'),p('reason')]),
    Spec('gm battle phase', 'battle_phase', 'GM: begin the enemy phase or next round', [p('phase',choices={'enemies':'Begin enemy phase','next':'End enemy phase; begin next round'})]),
    Spec('gm battle skip', 'battle_skip', 'GM: end an absent hero’s turn without spending optional resources', [member(),p('reason')]),
    Spec('gm battle hazard', 'hazard', 'GM: resolve a damaging hazard using player defenses', [p('targets'),p('damage',int),p('description')]),
    Spec('gm cancel-roll', 'cancel_roll', 'GM: cancel an invalid staged roll and restore its costs', [p('reason')]),
    Spec('gm undo', 'undo', 'GM: undo the latest saved game change', [p('reason')]),
    Spec('gm export', 'export', 'GM: download campaign sheets, sessions, and battle state', [], True),
    Spec('gm faq-add', 'faq_add', 'GM: add or update an answer for this server’s FAQ', [p('key',description='New FAQ ID, such as session-times'),p('question',description='Player question, up to 150 characters'),p('answer',description='Your answer, up to 2000 characters'),p('category',default='campaign',choices={k:v for k,v in CATEGORIES.items() if k != 'all'})], True),
    Spec('gm faq-remove', 'faq_remove', 'GM: remove one of this server’s custom FAQ answers', [p('key',description='Campaign FAQ ID to remove')], True),
]


def help_text(topic, *, gm=False):
    if topic == 'create':
        return ('1. /hero roll rolls and saves all four starting stats.\n'
                '2. /hero create opens your student form and uses those stats.\n'
                '3. /hero quirk describes your power and its limits.\n'
                '4. /hero submit sends it to the GM.\n'
                'Optional: /hero build chooses two moves and one Talent; defaults are ready to use. '
                '/hero stats lets you arrange the starting dice yourself.\n'
                '/hero sheet shows your short card. Add details:true for everything.')
    if topic == 'quirks':
        return ('One power. Say what it does, a few normal uses, what it cannot do, and its weakness. '
                '/hero quirk saves the card. Your GM approves it. Ordinary uses are free; strong effects use your prepared moves.')
    if topic == 'rolls':
        return ('/check stat:power rolls your hero’s Power die. Change the stat for your approach.\n'
                '1–3: miss • 4–7: success • 8+: big success.\n'
                'Edge: roll twice, keep higher. Pressure: keep lower. Having both cancels them.\n'
                'After a tracked roll, press Keep or Plus Ultra (−2 Health; once per session).\n'
                '/roll is for any other dice: /roll dice:1d20 bonus:3. '
                'For custom dice: /roll dice:1d[custom] faces:[0,1,1,5]. '
                'Text faces work too; they have no bonus or numeric total.')
    if topic == 'battle':
        return ('Your first battle action starts your turn automatically.\n'
                'Move once + take one action, in either order. Then /battle end.\n'
                '/battle attack targets:e1 • /hero help user:@Ally • /battle guard • /battle task • /battle recover.\n'
                'Ordinary attacks deal 2 damage on success, 3 on big success. Enhanced moves cost Energy even on a miss.\n'
                'When attacked: /battle defend, then Keep or Plus Ultra. A big defense earns /battle bonus.\n'
                '/battle status shows the board. /battle resolve brings back a waiting roll’s buttons.')
    if topic == 'training':
        return ('Show up and take part: 1 Training per official session, up to 2 per week. Side sessions also give Prep.\n'
                '3 Training requests a new move, Talent, or item with /hero unlock. The GM approves it.\n'
                '/hero build changes your prepared options between missions. /hero upgrade uses a shared class milestone.\n'
                '/hero prep chooses a new offered Prep. Prep gives Edge on one fitting roll next mission.')
    if topic == 'spar':
        return ('/spar start invites a student; they /spar join. Each uses /spar roll. Higher result wins an exchange; first to two wins. '
                'Ties reroll with no new costs. No Health damage or Plus Ultra. Winning gives no extra Training.')
    if topic == 'moves':
        return '\n\n'.join(f"{v['name']} ({k}) • {v['cost']} Energy\n{v['rule']}" for k,v in MOVES.items())
    if topic == 'talents':
        return '\n'.join(f'{name} ({key}): Edge on one fitting {kind} roll per scene.' for key,(name,kind) in TALENTS.items())
    if topic == 'items':
        return '\n\n'.join(f"{key.replace('_',' ').title()} ({key})\n{rule}" for key,rule in ITEMS.items())
    if topic == 'gm':
        return ('Character review: /gm approve. Setup: /gm config.\n'
                'Attendance: /gm session start participants:@Player,@Player, then /gm session end.\n'
                'Battle: /gm battle create, /gm zone add, /gm enemy add, /gm enemy intent, /gm battle start.\n'
                '/gm battle panel posts a live board. /gm battle phase advances heroes/enemies.\n'
                '/gm mission start/end handles loadout locks. /gm scene refreshes scene uses.\n'
                'Corrections: /gm resource, /gm cancel-roll, /gm undo. /gm export downloads the campaign.')
    if topic == 'commands':
        return '\n'.join('/'+s.path+' — '+s.description for s in SPECS if gm or not s.path.startswith('gm '))
    return ('Say what your hero tries. Roll only when the GM asks.\n'
            '1–3 miss • 4–7 success • 8+ big success.\n'
            '/hero roll + /hero create: start a character.\n'
            '/hero sheet: stats and resources. /check: a hero check. /roll: any dice.\n'
            '/battle status: the fight. /faq: ask a question.\n'
            '/help topic:create or battle: short steps. /help topic:handbook: the full guide.')
