# Your first session with the UA Hero College bot

You describe what your student wants to do. The GM decides what is possible and what is risky. The bot rolls dice and remembers the numbers for you.

## Make your student

Use the slash menu inside the game server. The examples below show command names and option values; Discord lets you fill in the options separately.

1. **`/hero create`** opens a form for your real name, hero name, adult age, goal, and reason to work with classmates.
2. **`/hero stats`** assigns **d10, d8, d8, d6**, once each, among Power, Speed, Wits, and Heart. For example: `power:10 speed:8 wits:6 heart:8`.
3. **`/hero quirk name:Cold Sculptor reach:ranged`** opens a power form. Write one clear power, 2–4 ordinary uses, things it cannot do, and 1–2 clear limits. Touch reaches your zone; a suitable ranged Quirk also reaches one connected zone. The GM approves what your power can actually do.
4. **`/hero moves`** selects two starting signature move templates. You can give each a personal name. Try `first:shield second:rescue_boost` for an ice rescuer.
5. **`/hero talent`** chooses one Talent. It gives Edge on one fitting roll per scene, if declared before rolling.
6. **`/hero gear`** records ordinary costume features and equipment. You start with no special support item.
7. **`/hero submit`** posts your finished card for GM approval. Use **`/hero sheet`** any time to see your sheet; `share:true` posts it publicly.

You start with **6 Health and 3 Energy**. You do not need to enter or remember those yourself. Changing your Quirk reopens its approval, so discuss changes with the GM between missions.

## Roll and choose

The GM names a fitting stat and tells you the risk. Use `/check stat:wits method:Look for the emergency controls` outside combat. The bot shows the roll and waits:

| Kept result | Meaning |
|---|---|
| 1–3 | Miss or setback; the GM applies the stated risk |
| 4–7 | Success |
| 8 or more | Big success with an extra benefit |

Press **Accept result**, or **Plus Ultra**. Plus Ultra changes your result to 8, then costs 2 Health. You get one Plus Ultra per official session. Only you can spend it; the GM can accept a result for an absent player. `/resolve` and `/resolve plus_ultra:true` do the same as the buttons.

Use `talent:true` or `prep:true` **before rolling** to spend an appropriate Talent or Prep. Use `edge:true` only for an advantage the GM agreed to, and `pressure:true` for an announced complication. Edge rolls twice and keeps higher; Pressure keeps lower. Extra sources never stack, and any Edge plus any Pressure cancel to one die.

The server handles one waiting game roll at a time. While someone chooses, use `/pending`, `/hero sheet`, or `/battle status`. Gameplay changes resume when that roll is resolved.

For any raw dice, use `/roll`; it defaults to 1d20. `/roll dice:1d20 bonus:3` adds 3 points. You can also use `/roll dice:2d17+1d8-3`, `dice:2d10 keep:high`, or `dice:2d10 keep:low`. Bonuses and expression modifiers are added after choosing the kept die.

Custom faces work in the same command: `/roll dice:1d[custom] faces:[0,1,1,5]` or `faces:["sun","rain","rain","storm"]`. Repeated faces add weight. These faces apply only to the current roll. Text dice have no numeric total and cannot use bonuses, modifiers, subtraction, or keep-high/low. Raw rolls do not spend Energy or offer Plus Ultra. Use `/check` and battle actions for tracked game effects.

## Take a battle turn

Your team chooses who acts first. Each hero acts once in the heroes phase.

1. **`/battle turn`** starts your turn.
2. Move one clear connected zone for free with **`/battle move zone:lobby`**, before or after your action.
3. Take **one action**. Here are the common choices:

| Goal | Command |
|---|---|
| Attack a foe | `/battle attack targets:e1 stat:power method:Strike with an ice fist` |
| Help a teammate's next attack | `/battle help user:@Ally task:attack method:Pin down their opponent` |
| Guard yourself or a nearby ally | `/battle guard` or `/battle guard user:@Ally` |
| Work on a rescue objective | `/battle task objective:evacuate stat:heart method:Guide the civilians rescue:true` |
| Restore 1 Energy | `/battle recover` |
| Use an agreed action needing no roll | `/battle automatic method:Open the unlocked exit` |

4. Resolve any rolled result, then **`/battle end`**. You can end early and leave movement or your action unused.

An ordinary attack deals 2 damage on a success or 3 on a big success. Help gives Edge and adds 1 damage to one helped hit, ignoring its Armor. Guard reduces one incoming attack by 2. The bot calculates those effects.

To use a prepared signature, select its option: for example `/battle attack ... move:heavy_hit`, `/battle capture ...`, `/battle task ... boost:true`, `/battle shield`, or `/battle move ... mode:rapid`. **Pay Energy even on a miss, and use at most one signature per turn.** Rapid Move replaces your free movement and leaves an ordinary action. `/rules` explains every move card.

Mend uses `/mend user:@Ally`, costs 2 Energy, and heals in your zone. A special item uses `/item`, except Grapple Line and Rescue Harness, which are options on `/battle move`. The bot checks prepared choices and use limits.

## When danger hits you

The GM announces an attack. If damage remains after protection, use **`/battle defend stat:speed method:Duck behind the cover`**, choosing the stat agreed with the GM. Accept or use Plus Ultra as usual. A 4+ avoids the attack; an 8+ also earns a free move to one clear connected zone.

You may preselect that destination with `bonus_zone:lobby`. Otherwise, after everyone finishes their defense, use **`/battle bonus zone:lobby`** or choose `zone:stay`. Group attacks finish all defenses before bonus moves happen. Defense and bonus movement choices must finish before play continues. Protection that reduces damage to zero needs no defense roll and gives no bonus move.

At **0 Health you are Down**. You can end your turn or give one useful cheer through `/battle help`, once per fight. Mend can revive you. Defeat does not automatically kill your character. Safe recovery is confirmed by the GM, not by rolling repeatedly.

## Grow your hero

- Meaningful participation in an official main or side session earns **1 Training**, up to **2 per server week**. The GM marks participation; winning fights or spamming rolls gives no extra Training.
- Side sessions also earn themed **Prep** for the next main mission. Spend it on one fitting roll for Edge. Hold one Prep; `/hero prep replace:true` takes a new offer, while `replace:false` keeps your old one. Unused Prep for a mission expires when it ends.
- With 3 Training, **`/hero unlock kind:move option:capture`** requests a new option. The GM approves it and the bot spends the Training. Other kinds are `talent` and `item`.
- Between missions, **`/hero prepare`** selects two learned moves, one learned Talent, and at most one learned item. Mission loadouts are locked during the mission. Switching choices does not refresh already-spent scene uses.
- When the class earns a shared milestone, **`/hero upgrade stat:speed`** raises that die one step: d6 → d8 → d10 → d12. New and returning heroes receive the same shared increases.
- **`/hero tracker name:Dorm project value:2/4`** saves your personal notes or custom counters on your sheet. Those notes do not silently change the core game rules.
- **`/spar start opponent:@Ally`** invites a friendly contest. They `/spar join`; both `/spar roll`. First to two wins takes it, ties reroll without new costs, and everyone gets the same participation rewards when the GM runs it as an official session.

Use **`/help`** for short tutorials, **`/rules`** for cards, **`/faq`** for common questions, and **`/guide`** for the full player handbook. Start by saying your goal; the commands follow the decision.

## Ask the FAQ

Try **`/faq question:energy`**, **`/faq question:How do I make a Quirk?`**, or **`/faq category:combat`**. Typing a question suggests matching answers; choosing one reads it. `/faq` alone shows the categories. Answers are private by default; `share:true` posts one in the channel.

You can ask before creating a hero and while another player's roll waits. The GM can add campaign answers about session times, house rules, or the university setting, so `/faq category:campaign` is useful too. The FAQ looks up written answers; if no answer matches, ask your GM.

## Personal notes and custom dice

`/hero tracker name:Dorm project value:2/4` saves a note or manual counter on your sheet. To delete it, use `/hero tracker name:Dorm project` and leave the value blank. Core Health, Energy, and stat dice are tracked by the game commands.

A custom die can contain numbers or text labels, including a mixture. A die with any text face cannot use keep-high/low, subtraction, or numeric modifiers, even if it happens to roll a number. Ordinary positive text pools are allowed; text results have no total.
