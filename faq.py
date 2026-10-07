"""Curated player FAQs and server-specific answers; no network or AI dependency."""

from dataclasses import dataclass
import re
from .rules import clean, require

CATEGORIES = {
    'all': 'All topics',
    'start': 'Getting started',
    'characters': 'Characters and Quirks',
    'rolls': 'Dice and Plus Ultra',
    'combat': 'Combat and teamwork',
    'recovery': 'Health, Energy, and recovery',
    'progression': 'Training, Prep, and growth',
    'sparring': 'Friendly sparring',
    'bot': 'Using the bot',
    'campaign': 'This campaign',
}


@dataclass(frozen=True)
class Answer:
    key: str
    category: str
    question: str
    answer: str
    tags: str = ''


BUILTIN = (
    Answer('start','start','How do I start playing?',
           'Say what your student wants to do. The GM explains what is possible and which stat to roll. Use /hero create to make your student, /help topic:create for the steps, and /guide for the full handbook.', 'begin learn tutorial new player'),
    Answer('create','characters','How do I create a character?',
           'Use /hero create, /hero stats, /hero quirk, /hero moves, /hero talent, and optionally /hero gear. Then /hero submit asks the GM to approve your hero. /hero sheet shows the saved card.', 'character creation sheet student hero'),
    Answer('stats','characters','What are my starting stats and resources?',
           'Assign d10, d8, d8, d6 among Power, Speed, Wits, and Heart with /hero stats. Start with Health 6, Energy 3, two signature moves, and one Talent. You start with no special support item.', 'stat dice starting numbers beginner'),
    Answer('quirk','characters','How do I make a Quirk?',
           'Use /hero quirk to describe one clear power, 2–4 ordinary uses, touch or ranged reach, things it cannot do, and 1–2 limits. The GM approves the fiction. Basic uses are free; enhanced effects use prepared signature templates.', 'power ability weakness limits quirk creation'),
    Answer('limits','characters','Can my Quirk give me extra actions or unlimited power?',
           'Your description does not add extra actions, Health, damage, or free signature effects. Clones, flight, copying, and unusual powers need agreed limits. A hard limit can prevent an attempt; a softer complication may give Pressure. Ask the GM before submitting.', 'clone flying copying overpowered balanced abilities'),
    Answer('approval','characters','Why can I not use my hero yet?',
           'The GM must approve your submitted card with /gm approve. Write your Quirk, then /hero submit. Rewriting a Quirk reopens approval. An existing approved hero changes learned loadouts with /hero prepare between missions.', 'draft approve approved submit permission'),
    Answer('results','rolls','What does my roll mean?',
           'Roll the fitting stat die and add nothing. 1–3 is a miss or setback, 4–7 succeeds, and 8+ is a big success. The GM explains the risk before you roll. Use /check outside battles and the relevant /battle action inside them.', 'success miss big fail thresholds check'),
    Answer('edge','rolls','How do Edge and Pressure work?',
           'Edge rolls twice and keeps higher; Pressure rolls twice and keeps lower. Multiple sources never stack. Any Edge plus any Pressure cancel to one die. Declare fitting Talent or Prep before rolling; other advantages and complications need GM agreement.', 'advantage disadvantage bonuses help cancellation'),
    Answer('plus-ultra','rolls','When can I use Plus Ultra?',
           'After seeing a tracked stat roll, press Plus Ultra or /resolve plus_ultra:true. It changes the result to 8, then costs 2 Health after the effect. Use it once per official session. Only the rolling player can spend it. Raw dice, sparring, and automatic actions do not offer it.', 'plus ultra limit session health boost'),
    Answer('custom-dice','rolls','Can I roll unusual, weighted, or text dice?',
           'Yes. /roll defaults to 1d20. Try /roll dice:2d17+1d8-3, or /roll dice:1d20 bonus:3. Keep-high/low chooses one die from a single numeric pool, then adds modifiers and bonus points. For custom faces, use dice:1d[custom] faces:[0,1,1,5] or faces:["sun","rain","rain","storm"]. Repeated faces add weight; nothing needs to be created or saved. Text faces cannot use keep-high/low, subtraction, numeric modifiers, or bonus points.', 'custom dice arbitrary die weighted weather symbols roll bonus modifiers'),
    Answer('raw-dice','rolls','Does a raw dice roll apply game effects?',
           'No. /roll shows dice and any bonus immediately. Use /check and battle actions for rolls that spend resources, apply game effects, or offer Plus Ultra. Raw rolls do not award Training and can be used while a tracked roll is waiting.', 'raw rolling damage resources standalone'),
    Answer('turn','combat','What can I do on my turn?',
           'Use /battle turn. Move one clear connected zone for free, and take one action, in either order. Resolve a rolled action, then /battle end. Attack, Help, Guard, a task, Recover, and an agreed automatic action are common choices. At most one signature move per turn.', 'turn action movement round order start end'),
    Answer('attack','combat','How much damage does an attack do?',
           'An ordinary attack deals 2 on a success or 3 on a big success. Heavy Hit costs 1 Energy and deals 3/4. Burst costs 1 Energy and hits up to three enemies in one zone for 1/2 each. Armor reduces each unassisted hit by 1. /rules shows move cards.', 'attack damage heavy hit burst armor hit'),
    Answer('help','combat','Why should I Help a teammate?',
           'Help costs your action and gives one ally Edge on their next matching roll before your next turn. A helped attack also adds 1 damage and ignores Armor on one named target. Burst applies this damage bonus to one target chosen before rolling. Help is consumed even on a miss and never stacks.', 'help teamwork support assisted armor cooperation'),
    Answer('guard-shield','combat','Do Guard and Shield stack?',
           'No. Use one damage reduction of 2. Guard protects one person; Shield costs 1 Energy and protects friendly targets in its zone from one attack. The bot uses a zone Shield first, preserving individual Guards. Protection is spent even if defense succeeds. Attacks already at zero before protection do not spend Guard or Shield. At zero damage there is no defense roll or bonus move.', 'guard shield protection group area stacking'),
    Answer('defense','combat','How do I defend against an attack?',
           'When the bot requests defense, use /battle defend with the agreed stat and method, then choose Accept or Plus Ultra. A miss takes remaining announced damage; 4+ avoids it; 8+ also earns /battle bonus to move one connected zone or stay. All group defenses finish before bonus moves.', 'defend defense dodge incoming enemy damage bonus movement'),
    Answer('capture','combat','Can Capture completely stop a boss?',
           'A success prevents movement until the foe’s next action ends and reduces damage from that action by 1. Big success cancels that action. A boss loses at most one action per round. Captures do not stack; keep the stronger effect. Conscious major enemies do not become permanently helpless from one roll.', 'capture boss restrain stun actions interrupt'),
    Answer('movement','combat','What is the difference between moving, Rush, and Rapid Move?',
           'A normal free move crosses one clear connection. Rush spends your action on another connected-zone move. Prepared Rapid Move costs 1 Energy, replaces your free move, and reaches any zone with a permitted route before an ordinary action. It cannot combine with another signature. Sealed barriers still need a way through.', 'move movement rush rapid route carry zones'),
    Answer('objectives','combat','How do rescue objectives and Danger work?',
           'Use /battle task on the named objective. A normal success adds 1 progress, big success 2; prepared Rescue Boost costs 1 Energy and adds 2/3. Announced prerequisites must be completed first. Movement alone does not complete a rescue. Danger advances once per completed round until stopped; the GM applies its announced consequence.', 'objective rescue boost danger progress prerequisites clock'),
    Answer('energy','recovery','How do I get more Energy?',
           'Use /battle recover as your action to restore 1 Energy, up to 3. Between encounters, /gm rest confirms ten safe minutes and restores Health and Energy. Starting a battle, scene, or session does not restore either resource.', 'energy regain refill recover recovery rest tired exhausted'),
    Answer('miss-cost','recovery','Do I lose Energy when my signature move misses?',
           'Yes. Pay before the roll; a miss still spends the action and Energy. Use an ordinary action if you want to conserve Energy. The GM can cancel an invalid waiting roll and restore its costs, but ordinary misses are not automatically refunded.', 'energy miss cost signature refund failure'),
    Answer('down','recovery','What happens at zero Health?',
           'You are Down, not automatically dead. End your turn or give one useful cheer through /battle help, once per fight. Enemies target active threats. Mend revives you at 1 Health; Medical Patch cannot revive. Between encounters, the GM can confirm basic assistance or safe rest.', 'down zero health hp unconscious dying dead death revive'),
    Answer('healing','recovery','How often can someone heal me?',
           'Each hero can receive one healing action per fight, counting Mend and Medical Patch together. Mend costs 2 Energy and restores 2 Health, or revives at 1. Medical Patch restores 1 above zero. These require touch in your zone during a battle. Health never exceeds 6.', 'heal healing mend medical patch hp restore'),
    Answer('refresh','recovery','When do my once-per-scene and session abilities refresh?',
           'A meaningful new scene or battle refreshes Talents and special items. An official session refreshes Plus Ultra. Ten safe minutes restore Health and Energy. Swapping a loadout does not refresh spent uses. The GM decides when these boundaries actually happen.', 'refresh resets talent item session scene rest cooldown'),
    Answer('training','progression','How do I earn Training?',
           'Meaningful participation in an official main or side session earns 1 Training, up to 2 per server week. The GM marks participants and closes the session. Failed practice still counts. Kills, winning a spar, repeated checks, and unapproved chat grinding give no extra Training.', 'training xp experience attendance show up participate rewards weekly cap'),
    Answer('prep','progression','What does a side-session Prep do?',
           'An official side session also gives themed Prep, even if Training is capped. It gives Edge on one fitting roll in the next main mission, declared before rolling. Hold one Prep; /hero prep chooses whether to keep it or take a new offer. Unused Prep expires when its assigned mission ends.', 'prep preparation side session reward theme mission edge expire'),
    Answer('unlock','progression','How do I learn and prepare new options?',
           'With 3 Training, /hero unlock requests a listed move, Talent, or item. GM approval spends the Training and learns it. Between missions, /hero prepare chooses two known moves, one known Talent, and at most one known item. Mission loadouts are locked; learned options stay available.', 'unlock learn upgrade training prepare loadout moves talents items'),
    Answer('milestone','progression','Will I fall behind if I miss a session?',
           'Class milestones give every hero the same stat increases, including new and returning heroes. Use /hero upgrade to step a die from d6 to d8 to d10 to d12. Attendance earns more learned choices and Prep, while shared growth keeps core dice together. Ask your GM for a story recap.', 'missed session absent attendance milestone catch up growth stats'),
    Answer('spar','sparring','How do friendly player-versus-player spars work?',
           'Use /spar start to invite a student; they /spar join. Both roll an approach each exchange; higher kept result wins even below 4. First to two wins takes the spar. Exact ties reroll with the same bonuses and no new costs. No Health damage, prepared move effects, or Plus Ultra. Participation rewards are equal.', 'pvp spar sparring contest duel friendly ties'),
    Answer('pending','bot','Why is the bot asking me to resolve a waiting roll?',
           'The server handles one waiting game roll at a time. Use /pending to see it. The rolling player chooses Accept or Plus Ultra, or uses /resolve. The GM can accept an absent player’s result or cancel an invalid roll with a reason. FAQ, help, sheets, and status commands remain readable.', 'pending waiting stuck blocked resolve button frozen'),
    Answer('trackers','bot','Where can I see or record my stats and notes?',
           '/hero sheet shows core stats, resources, loadout, Training, Prep, and personal trackers. /hero tracker saves a named note or manual counter, such as Dorm project = 2/4. Leave the value blank to delete a tracker. It does not change core mechanics. Sheets and FAQs are private by default; share:true posts them in the channel.', 'tracker stat notes counters sheet private share'),
    Answer('commands','bot','Where can I find help or missing commands?',
           'Use /help for short tutorials, /rules for cards, /faq for common questions, and /guide for the handbook. Slash commands run inside the game server. If commands are missing, ask the GM to check the bot installation, application-command permission, server ID, and Railway connection logs.', 'command help guide rules slash missing handbook faq'),
)

BY_KEY = {entry.key: entry for entry in BUILTIN}
STOP_WORDS = set('a an and are as at be can do does for get how i in is it me more my of on or the to use what when where why with'.split())


def tokens(text):
    return set(re.findall(r'[^\W_]+', str(text).casefold())) - STOP_WORDS


def entries(custom):
    return list(BUILTIN) + [Answer(key, value['category'], value['question'], value['answer'], 'campaign')
                           for key, value in sorted(custom.items())]


def search(question, category, custom, *, limit=5):
    require(category in CATEGORIES, 'Choose a FAQ category from the slash menu.')
    question = clean(question, 150, empty=True)
    candidates = [e for e in entries(custom) if category == 'all' or e.category == category]
    exact = next((e for e in candidates if e.key.casefold() == question.casefold()),None)
    if exact:
        return [exact]
    wanted = tokens(question)
    if not wanted:
        return []
    scored = []
    for entry in candidates:
        primary = tokens(entry.key+' '+entry.question+' '+entry.tags)
        primary_hits = len(wanted & primary)
        body_hits = len(wanted & tokens(entry.answer))
        score = primary_hits * 10 + body_hits
        if score:
            scored.append((score,entry))
    # Stable ordering keeps an exact-topic FAQ ahead of merely related body text.
    return [e for _,e in sorted(scored,key=lambda x:-x[0])[:limit]]


def response(question='', category='all', custom=None):
    custom = custom or {}
    question = clean(question,150,empty=True)
    require(category in CATEGORIES,'Choose a FAQ category from the slash menu.')
    if not question:
        available = entries(custom)
        if category == 'all':
            lines = ['Choose a category, search a few words, or enter a FAQ ID.',
                     'Examples: /faq question:energy · /faq category:combat · /faq question:plus-ultra', '']
            for key,label in CATEGORIES.items():
                if key != 'all':
                    count = sum(e.category == key for e in available)
                    lines.append(f'{label} ({key}): {count} answer(s).')
        else:
            lines = [f'{e.key}: {e.question}' for e in available if e.category == category]
            if not lines:
                lines = ['The GM has not added answers in this category yet.']
            lines += ['', 'Use /faq question:ID for an answer, or add search words.']
        return {'title':'FAQ · '+CATEGORIES[category],'text':'\n'.join(lines)}
    matches = search(question,category,custom)
    if not matches:
        return {'title':'FAQ · no matching answer','text':'Try a short topic such as energy, capture, or training, or browse a category. If your question is about this campaign, ask the GM to add an answer.'}
    return {'title':'FAQ · answers','text':'\n\n'.join(f'{e.question}\n{e.answer}\nFAQ ID: {e.key} · {CATEGORIES[e.category]}' for e in matches),
            'faq_entries':[{'question':e.question,'answer':e.answer,'key':e.key,'category':CATEGORIES[e.category]} for e in matches]}
