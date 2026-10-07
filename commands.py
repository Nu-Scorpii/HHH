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


def stat():
    return p('stat', choices=STAT, description='Stat agreed with the GM before rolling')


def method():
    return p('method', description='Your goal and how your hero attempts it')


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
    Spec('help', '', 'Learn the game and find the bot commands', [p('topic', default='quick', choices={x: x.title() for x in ['quick','create','quirks','rolls','battle','training','spar','gm','commands']})], True, 'help'),
    Spec('faq', 'faq', 'Browse or search common questions and campaign answers', [p('question',default='',description='Search words or a FAQ ID, such as energy or plus-ultra'),p('category',default='all',choices=CATEGORIES),p('share',bool,False,'Post the answer publicly instead of privately')], True),
    Spec('rules', '', 'Read move, Talent, item, or core rules', [p('topic', default='core', choices={'core':'Core rules', **MOVE, **TALENT, **{k:k.replace('_',' ').title() for k in ITEMS}})], True, 'rules'),
    Spec('guide', '', 'Download the complete player handbook', [], True, 'guide'),
    Spec('resolve', 'resolve', 'Accept your waiting roll or choose Plus Ultra', [p('plus_ultra',bool,False,'Set true to use Plus Ultra after seeing the roll')]),
    Spec('pending', 'pending_status', 'Show the waiting roll and its decision buttons'),
    Spec('check', 'check', 'Roll your tracked stat outside a battle', [stat(),method(),p('task',default='check',choices=CHECK), *bonuses(), p('rescue',bool,False,'This directly saves or protects someone')]),
    Spec('help-ally', 'ordinary_help', 'Help an ally on a named check outside combat', [member(),p('task',choices=CHECK),method()]),
    Spec('mend', 'mend', 'Use prepared Mend, in combat or outside it', [member()]),
    Spec('item', 'item_use', 'Use your prepared Smoke, Scanner, or Medical Patch', [member(default=None),p('question',default='',description='Field Scanner question for the GM')]),
    Spec('hero create', '', 'Create a student with a guided form', [], True, 'create'),
    Spec('hero edit', '', 'Edit your student’s name, age, goal, and team connection', [], True, 'edit'),
    Spec('hero stats', 'hero_stats', 'Assign d10, d8, d8, and d6 to your starting stats', [p(s,int,choices={n:f'd{n}' for n in [6,8,10,12]}) for s in STATS], True),
    Spec('hero quirk', '', 'Write your power, ordinary uses, reach, and limits', [p('name',description='Your Quirk name'),p('reach',default='ranged',choices={'touch':'Touch: own zone','ranged':'Ranged: own or connected zone'})], True, 'quirk'),
    Spec('hero moves', 'hero_moves', 'Choose and name two starting signature moves', [p('first',choices=MOVE),p('second',choices=MOVE),p('first_name',default=''),p('second_name',default='')], True),
    Spec('hero talent', 'hero_talent', 'Choose your starting Talent', [p('talent',choices=TALENT)], True),
    Spec('hero gear', 'hero_gear', 'Record ordinary costume features and equipment', [p('gear')], True),
    Spec('hero submit', 'hero_submit', 'Send your finished character card for GM approval'),
    Spec('hero sheet', 'hero_sheet', 'View your current character, stats, and resources', [member(default=None),p('share',bool,False,'Post the sheet publicly instead of privately')], True),
    Spec('hero upgrade', 'hero_upgrade', 'Spend a waiting shared stat increase', [stat()]),
    Spec('hero unlock', 'hero_unlock', 'Request a new move, Talent, or item for 3 Training', [p('kind',choices={k:k.title() for k in ['move','talent','item']}),p('option',description='Option ID from /rules or /help topic:training')]),
    Spec('hero prepare', 'hero_prepare', 'Prepare two learned moves, a Talent, and one item for a mission', [p('first',choices=MOVE),p('second',choices=MOVE),p('talent',choices=TALENT),p('item',default='none',choices=ITEM)]),
    Spec('hero tracker', 'hero_tracker', 'Save a custom tracker, or leave its value blank to delete it', [p('name'),p('value',default='',description='Tracker value; leave blank to delete this tracker')], True),
    Spec('hero prep', 'hero_prep', 'Choose whether to replace held Prep with a new offer', [p('replace',bool,False,'False keeps the existing Prep; true takes the new offer')]),
    Spec('dice roll', 'dice_roll', 'Roll arbitrary numbered or weighted custom dice', [p('expression',description='Examples: 2d17+1d8-3, 1d[weather], 2d10'),p('keep',default='all',choices={'all':'All: show and sum numeric dice','high':'Keep highest: Edge pool','low':'Keep lowest: Pressure pool'})]),
    Spec('dice create', 'dice_create', 'GM: define a named die with numeric or text faces', [p('name'),p('faces',description='JSON faces: [0,1,1,5] or ["sun","rain","storm"]')]),
    Spec('dice list', 'dice_list', 'List this server’s named dice', [], True),
    Spec('dice remove', 'dice_remove', 'GM: remove a named custom die', [p('name')]),
    Spec('battle create', 'battle_create', 'GM: create a battle or rescue challenge', [p('name'),p('participants',description='Hero mentions or user IDs, separated by commas'),p('starting_zone',default='start')]),
    Spec('battle start', 'battle_start', 'GM: begin round 1 after announcing enemy intentions'),
    Spec('battle status', 'battle_status', 'Read current zones, turns, Health, enemies, and objectives'),
    Spec('battle panel', 'battle_status', 'GM: post a live battle panel that updates after commands', [], False, 'panel'),
    Spec('battle turn', 'battle_turn', 'Begin your turn after the team chooses its order'),
    Spec('battle end', 'battle_end', 'End your turn, including any unused movement or action'),
    Spec('battle move', 'battle_move', 'Move, Rush, or use Rapid Move on a permitted route', [p('zone'),p('mode',default='normal',choices={'normal':'Free move','rush':'Rush: uses action','rapid':'Rapid Move: 1 Energy'}),p('method',default='Move along a clear route.'),p('carry',default='',description='One cooperative hero ID, or two with Rescue Harness'),p('harness',bool,False),p('grapple',bool,False),p('risky',bool,False,'A risky crossing uses your action and a roll'),p('stat',default='speed',choices=STAT),p('pressure',bool,False),p('talent',bool,False),p('prep',bool,False)]),
    Spec('battle attack', 'battle_attack', 'Attack with a basic strike, Heavy Hit, Burst, or Long Reach', [p('targets',description='Enemy IDs: e1, or e1,e2,e3 for Burst'),stat(),method(),p('move',default='basic',choices={'basic':'Ordinary Attack',**{k:MOVE[k] for k in ['heavy_hit','burst','long_reach']}}),*bonuses(),p('assisted_target',default='',description='Burst Help damage target; defaults to first named target'),p('visible',bool,True,'A clear line of sight is required')]),
    Spec('battle capture', 'battle_capture', 'Use Capture to restrain or interrupt one enemy', [p('enemy'),stat(),method(),*bonuses()]),
    Spec('battle task', 'battle_task', 'Work on an objective or another risky task', [stat(),method(),p('objective',default=''),p('boost',bool,False,'Use prepared Rescue Boost for 1 Energy'),*bonuses(),p('rescue',bool,False),p('task_type',default='task',choices={k:v for k,v in TASK.items() if k not in ['attack','defense','capture']})]),
    Spec('battle automatic', 'battle_automatic', 'Spend an ordinary action on an agreed task needing no roll', [method()]),
    Spec('battle help', 'battle_help', 'Help a named ally and task, or cheer while Down', [member(),p('task',choices=TASK),method(),p('objective',default='')]),
    Spec('battle guard', 'battle_guard', 'Guard yourself or one ally in your zone', [member(default=None),p('method',default='Protect them from the announced attack.')]),
    Spec('battle shield', 'battle_shield', 'Use Shield to prepare protection against one attack', [p('method',default='Prepare a barrier in my zone.')]),
    Spec('battle recover', 'battle_recover', 'Use your action to restore 1 Energy'),
    Spec('battle defend', 'defend', 'Roll defense against the incoming attack', [stat(),method(),member(default=None),*bonuses(),p('bonus_zone',default='',description='Optional big defense destination, or stay')]),
    Spec('battle bonus', 'bonus_move', 'Choose your earned big defense move, or stay', [p('zone',default='stay'),member(default=None)]),
    Spec('battle finish', 'battle_finish', 'GM: finish a fight or challenge and record its outcome', [p('outcome')]),
    Spec('enemy add', 'enemy_add', 'GM: create a Minion, Rival, Elite, or Boss', [p('name'),p('template',choices={k:k.title() for k in ENEMIES}),p('zone'),p('trait',default='none',choices={k:k.title() for k in ['none','armor','protector','wide','fast']}),p('reach',default='touch',choices={'touch':'Own zone','ranged':'Own or connected zone','scene':'Anywhere visible in scene'})]),
    Spec('enemy edit', 'enemy_edit', 'GM: set enemy Health, damage, or action count', [p('enemy'),p('health',int,None),p('damage',int,None),p('actions',int,None)]),
    Spec('enemy trait', 'enemy_trait', 'GM: enable or remove a trait or exposed Armor', [p('enemy'),p('trait',choices={k:k.title() for k in ['armor','protector','wide','fast']}),p('enabled',bool,True)]),
    Spec('enemy intent', 'enemy_intent', 'GM: announce the enemy’s reliable intention', [p('enemy'),p('intention')]),
    Spec('enemy move', 'enemy_move', 'GM: resolve permitted enemy movement', [p('enemy'),p('zone')]),
    Spec('enemy attack', 'enemy_attack', 'GM: spend an enemy action and request player defenses', [p('enemy'),p('targets',description='Active hero IDs or mentions, separated by commas'),p('description',description='Announced attack and fictional effect'),p('damage',int,None,'Announced damage override; default uses the enemy card')]),
    Spec('enemy action', 'enemy_action', 'GM: resolve or skip an enemy action, including objectives', [p('enemy'),p('description'),p('objective',default=''),p('amount',int,1)]),
    Spec('objective add', 'objective_add', 'GM: create a public progress objective and its prerequisites', [p('key'),p('name'),p('goal',int,4),p('zone',default=''),p('prerequisites',default='',description='Existing objective IDs, separated by commas')]),
    Spec('objective tick', 'objective_tick', 'GM: correct or advance objective progress', [p('key'),p('amount',int),p('reason')]),
    Spec('objective danger', 'danger_set', 'GM: announce a Danger track and its consequence', [p('name'),p('consequence'),p('goal',int,3)]),
    Spec('objective stop-danger', 'danger_stop', 'GM: stop the announced cause of danger', [p('reason')]),
    Spec('session start', 'session_start', 'GM: start one official main or side session', [p('name'),p('side',bool,False),p('prep_theme',default='',description='Required theme for an official side session')]),
    Spec('session mark', 'session_mark', 'GM: mark or remove a player’s meaningful participation', [member(),p('participated',bool,True)]),
    Spec('session end', 'session_end', 'GM: record the session and award capped Training and Prep', [p('summary')]),
    Spec('session log', 'session_log', 'Read the latest session records'),
    Spec('mission start', 'mission_start', 'GM: lock prepared choices and assign held Prep to a main mission', [p('name')]),
    Spec('mission end', 'mission_end', 'GM: finish a mission and expire its unused Prep'),
    Spec('scene new', 'scene_new', 'GM: begin a new meaningful scene and refresh Talents and items', [p('name')]),
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
    Spec('gm zone', 'zone_add', 'GM: create a zone with clear or blocked connections', [p('name'),p('connect_to',default='',description='Existing zone IDs separated by commas'),p('clear',bool,True)]),
    Spec('gm link', 'zone_link', 'GM: open or block a connection between two zones', [p('first'),p('second'),p('clear',bool,True)]),
    Spec('gm position', 'position', 'GM: correct a hero or enemy position', [p('target',description='Hero user ID or enemy ID'),p('zone'),p('reason')]),
    Spec('gm phase', 'battle_phase', 'GM: begin the enemy phase or next round', [p('phase',choices={'enemies':'Begin enemy phase','next':'End enemy phase; begin next round'})]),
    Spec('gm skip', 'battle_skip', 'GM: end an absent hero’s turn without spending optional resources', [member(),p('reason')]),
    Spec('gm hazard', 'hazard', 'GM: resolve a damaging hazard using player defenses', [p('targets'),p('damage',int),p('description')]),
    Spec('gm cancel-roll', 'cancel_roll', 'GM: cancel an invalid staged roll and restore its costs', [p('reason')]),
    Spec('gm undo', 'undo', 'GM: undo the latest saved game change', [p('reason')]),
    Spec('gm export', 'export', 'GM: download campaign sheets, sessions, and battle state', [], True),
    Spec('gm faq-add', 'faq_add', 'GM: add or update an answer for this server’s FAQ', [p('key',description='New FAQ ID, such as session-times'),p('question',description='Player question, up to 150 characters'),p('answer',description='Your answer, up to 2000 characters'),p('category',default='campaign',choices={k:v for k,v in CATEGORIES.items() if k != 'all'})], True),
    Spec('gm faq-remove', 'faq_remove', 'GM: remove one of this server’s custom FAQ answers', [p('key',description='Campaign FAQ ID to remove')], True),
]


def help_text(topic):
    if topic == 'create':
        return ('Create your hero in order:\n1. /hero create opens a form.\n2. /hero stats assigns d10, d8, d8, d6.\n'
                '3. /hero quirk writes abilities and limits.\n4. /hero moves chooses two templates and names.\n'
                '5. /hero talent chooses a once-per-scene Talent.\n6. /hero gear records ordinary equipment.\n'
                '7. /hero submit asks the GM to approve your card.\n/hero sheet shows everything; /guide downloads the full tutorial.')
    if topic == 'quirks':
        return ('Describe one clear power. List 2–4 ordinary uses, touch or connected-zone reach, what it cannot do, and 1–2 clear limits. '
                'A hard limit can prevent an attempt; a softer weakness gives Pressure. Basic uses are free. Enhanced effects use prepared move cards. '
                'Flight, clones, copied powers, and dramatic descriptions do not create extra actions. Agree with the GM before /hero submit.')
    if topic == 'rolls':
        return ('/check uses your stat outside combat; /battle commands use it during combat. Roll and add nothing: 1–3 miss, 4–7 succeed, 8+ big success. '
                'Edge rolls twice and keeps higher; Pressure keeps lower; any of both cancel. Declare Talent and Prep before rolling. '
                'After the roll, /resolve plus_ultra:true sets it to 8 and costs 2 Health after the effect.\n'
                '/dice roll expression:2d17+1d8-3 handles custom numbered dice. /dice roll expression:2d10 keep:high is an Edge pool. '
                'GM /dice create defines JSON faces, including weighted repeats and text. Limits: 100 dice, 20 terms, 1 billion numbered sides, 1000 custom faces.')
    if topic == 'battle':
        return ('Choose a team order. /battle turn begins your turn; move one connected zone and take one action, then /battle end. '
                'Actions: /battle attack, help, guard, task, automatic, recover. Enhanced options: capture, shield, move mode:rapid; /mend heals. '
                'Attacks deal 2/3; Help gives Edge plus 1 damage and Armor bypass on one hit. Guard reduces one attack by 2. '
                'Pay Energy before using a signature; a miss still pays; at most one signature per turn. '
                'Defense: /battle defend; 4+ avoids, 8+ also earns /battle bonus. Group defenses all finish before bonus moves. '
                'At 0 Health, use /battle help to cheer once per fight. /battle status reads the board; the GM handles phase changes and enemy actions.')
    if topic == 'training':
        return ('The GM marks meaningful participation with /session mark and /session end awards 1 Training, at most 2 per server week. '
                'Side sessions also give one themed Prep for the next main mission. /hero prep chooses between an existing Prep and a new offer. '
                '/hero unlock requests one move, Talent, or item for 3 Training; /gm unlock confirms and spends it. '
                '/hero prepare chooses 2 known moves, 1 Talent, 1 item in downtime. /hero upgrade spends a shared milestone increase.\n'
                'Move IDs: ' + ', '.join(MOVES) + '\nTalent IDs: ' + ', '.join(TALENTS) + '\nItem IDs: ' + ', '.join(ITEMS))
    if topic == 'spar':
        return ('/spar start invites a player; they /spar join. Each uses /spar roll for an exchange. Higher kept result wins even below 4. '
                'First to two wins takes the spar. Exact ties repeat the same stat and bonuses without new costs. Enhanced Quirk use costs 1 Energy for Edge. '
                'Talents and valid main-mission Prep can apply. No Health damage, prepared move effects, or Plus Ultra. Winning adds no extra Training.')
    if topic == 'gm':
        return ('Setup: /gm config, review /hero submit, /gm approve.\nOfficial play: /session start, /session mark, /session end; /mission start/end.\n'
                'Battle: /battle create, /gm zone/link, /enemy add/intent, /objective add/danger, /battle start, /battle panel.\n'
                'After hero turns: /gm phase enemies; /enemy move/attack/action; finish defenses, then /gm phase next.\n'
                'Close: /battle finish, /gm rest if ten safe minutes pass. /scene new refreshes scene uses.\n'
                'Corrections: /gm resource, /objective tick, /gm cancel-roll, /gm undo. /gm export downloads campaign data.')
    if topic == 'commands':
        return '\n'.join('/' + s.path + ' — ' + s.description for s in SPECS)
    return ('Say your goal first. Four stats: Power, Speed, Wits, Heart. Roll one stat die, add nothing: 1–3 miss, 4–7 success, 8+ big success. '
            'Start with Health 6, Energy 3, two moves and one Talent.\n'
            '/help topic:create guides character creation. /help topic:rolls explains dice. /help topic:battle explains turns. '
            '/hero sheet shows your current resources. /faq answers common questions. /guide gives the complete player handbook.')
