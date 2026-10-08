# UA Hero College: quick player guide

Say what your hero tries. The GM tells you when to roll. The bot remembers your stats, resources, and battle effects.

## Make a character

1. **`/hero roll`** randomly assigns d10, d8, d8, and d6 to Power, Speed, Wits, and Heart. It saves your result; repeating the command shows it again.
2. **`/hero create`** opens a short form. Enter your real name and hero name. Age defaults to 18; the goal and team connection are optional. Saved starting stats apply automatically.
3. **`/hero quirk name:Ice reach:ranged`** opens your power card: one ability, ordinary uses, what it cannot do, and clear limits. Touch reaches your zone; an agreed ranged ability also reaches a clear connected zone.
4. **`/hero submit`** sends the full card for GM approval.

You start with **6 Health, 3 Energy, two moves, and one Talent**. No extra resource rolls are needed. Defaults are Heavy Hit, Rescue Boost, and Strong Spirit. If you want different choices, use **`/hero build`** before submitting. For example: `first:shield second:rescue_boost talent:sharp_thinker`.

You can run `/hero roll` after creating an unfinished draft too. It assigns starting stats once; it cannot reset an established hero. You may arrange the same balanced dice yourself with `/hero stats`. `/hero sheet` shows your short card; `details:true` shows every rule and note. `share:true` posts it publicly.

## Roll a check

Use **`/check stat:wits`** when the GM asks for Wits outside a battle. Say your method in chat, or add `method:Look for the emergency controls`.

| Result | Meaning |
|---|---|
| 1–3 | Miss or setback |
| 4–7 | Success |
| 8+ | Big success |

Press **Keep**, or **Plus Ultra · −2 HP**. Plus Ultra makes the result 8 and costs 2 Health after the effect. You get one use per official session. `/battle resolve` brings back waiting buttons; `choice:keep` accepts the result and `choice:plus` spends Plus Ultra. Only the rolling player can spend it; the GM may keep an absent player's result.

**Edge** rolls twice and keeps higher. **Pressure** keeps lower. Both together cancel to one die; extra sources never stack. Add `talent:true` or `prep:true` before rolling to spend an appropriate Talent or Prep. Use other Edge/Pressure only as agreed with the GM.

One tracked roll can wait per server. Finish its decision before changing gameplay. You can still read sheets, battle status, help, and FAQs.

## Take a battle turn

Your team chooses an order. **Your first move or action starts your turn automatically.** Each hero gets one free move and one action per round.

| What you want | Command |
|---|---|
| Move one clear connection | `/battle move zone:lobby` |
| Attack | `/battle attack targets:e1` |
| Help an ally's next attack | `/hero help user:@Ally` |
| Guard yourself or a person in your zone | `/battle guard` or `user:@Ally` |
| Work on an objective | `/battle task objective:evacuate` |
| Restore 1 Energy | `/battle recover` |
| Take an agreed action without a roll | `/battle automatic` |
| Finish or pass your turn | `/battle end` |

Default roll stats are Power for attacks, Wits for tasks, and Speed for defenses. Choose another `stat` when agreed with the GM. Say your approach in chat, or fill in `method`. Finish waiting rolls before ending the turn.

Ordinary attacks deal 2 damage on a success, 3 on a big success. Help gives Edge; one helped hit gains 1 damage and ignores Armor. Guard reduces one attack by 2. The bot calculates these effects.

For signature moves, use the matching option:

- Heavy Hit, Burst, Long Reach, or Capture: `/battle attack move:...`.
- Shield: `/battle guard kind:shield`.
- Rescue Boost: `/battle task boost:true`.
- Rapid Move: `/battle move mode:rapid`.
- Mend: `/hero heal user:@Ally`.

Use only your prepared moves. Pay Energy even on a miss; use **at most one signature per turn**. `/help topic:moves` explains the cards. `/hero item` uses Smoke, Scanner, or Medical Patch; Grapple Line and Rescue Harness are movement options.

## Defend and recover

When the GM announces an attack, use **`/battle defend`** if damage remains. Keep or use Plus Ultra. A 4+ avoids it; an 8+ also earns a connected-zone move. Use `/battle bonus zone:lobby` or `zone:stay` if the bot asks for your destination. Group attacks finish everyone's defense before bonus movement.

At **0 Health you are Down**. You can end your turn or cheer with `/hero help` once per fight. Mend can revive you. The GM confirms safe rest; it restores Health and Energy without a roll.

## Grow and organize your hero

Meaningful participation in a main or side session earns **1 Training**, up to **2 per server week**. Side sessions also give themed **Prep** for one fitting roll next main mission. Winning or repeatedly rolling gives no extra rewards.

With 3 Training, `/hero unlock` requests a new move, Talent, or item. The GM approves it. Between missions, `/hero build` chooses your two learned moves, one Talent, and one learned item. Omitted fields keep their choices; `item:none` removes the item. Swapping never refreshes a spent use.

`/hero upgrade` uses a shared class milestone. `/hero prep` chooses a new offered Prep. `/hero notes name:Dorm project value:2/4` saves a note; leave `value` empty to delete it. Notes do not change core stats.

`/spar start opponent:@Ally` invites a friendly best-of-three contest. They `/spar join`; both `/spar roll`. Ties reroll without new costs. There is no Health damage or Plus Ultra.

## Extra dice and questions

**`/roll`** defaults to 1d20. `dice:2d17+1d8-3` uses a custom expression; `bonus:3` adds 3 once to the total. `keep:high` or `keep:low` chooses one die from a single numeric pool before modifiers.

Custom faces work with `dice:1d[custom] faces:[0,1,1,5]` or `faces:["sun","rain","rain","storm"]`. Repeats add weight. Any text faces mean no numeric total, bonus, subtraction, or keep-high/low. Raw dice do not spend resources or apply tracked battle effects.

**`/faq question:energy`** searches answers; `/faq` browses topics. Answers are private unless `share:true` is selected. **`/help`** gives short steps; **`/help topic:handbook`** downloads all the player rules.
