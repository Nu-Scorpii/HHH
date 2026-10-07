# Running UA Hero College with the bot

The bot handles the rules and saved numbers. You handle story, Quirk permissions, consequences, reliable enemy intentions, and the truth of fictional advantages. Each Discord server is a separate campaign, with one active battle or spar and one waiting game roll at a time.

## Access and sheets

`BOT_OWNER_ID` is your personal user ID. As the creator, use `/gm config gm_role_id:@GM timezone:America/New_York reset_weekday:0 reset_hour:0` to grant ordinary GM access and set the weekly reset. Re-running config replaces all its settings, so include the GM role again if you want to retain it. Leaving that option empty removes role access; creator access remains.

Players own one hero per server. `/hero create` and `/hero quirk` open forms; `/hero submit` posts the full card. Review the Quirk, reach, limits, starting stat assignment, moves, Talent, and ordinary equipment before `/gm approve user:@Player`. Use `approve:false` to reopen a draft. The initial defaults make a usable baseline, but players should choose options suited to their concept. Starting stats must be one d10, two d8s, and one d6; already-earned shared increases are retained when a reopened draft changes assignment.

`/gm roster` privately lists heroes and resources. `/hero sheet user:@Player` lets you inspect a full sheet. Players can read other heroes' sheets but can change only their own choices and notes. Approvals, shared milestones, resource corrections, session rewards, NPC actions, and setup require creator or configured GM-role access. Server Administrator permission alone is not an access bypass.

## Campaign FAQs

Players use `/faq` to browse topics, search words, or select an answer from autocomplete suggestions. Replies are private unless they choose `share:true`. Core answers are included automatically; `/gm faq-add` adds or updates your server's own answers:

```text
/gm faq-add key:session-times question:When do we play? answer:Saturdays at 6 PM Eastern.
/gm faq-add key:dorm-rules question:Can students leave campus? answer:Tell a staff member first. category:campaign
/faq question:session-times
/gm faq-remove key:dorm-rules
```

Use the same ID to update an answer. IDs begin with a letter and use up to 32 letters, digits, underscores, or hyphens. Questions have up to 150 characters, answers up to 2000. Each server can save 50 custom FAQs. Only creator/GM-role accounts may edit them; built-in rule answers cannot be overwritten or removed. These are player-facing answers, so include information you intend players to read. Custom FAQs survive restarts and are included in exports/backups. End any waiting roll before editing an answer.

## Sessions, scenes, and missions

These represent different things:

| Command | What it does |
|---|---|
| `/session start` | Opens one official session; refreshes Plus Ultra |
| `/session mark` | Marks meaningful participation, or removes it with `participated:false` |
| `/session end` | Records your summary and awards Training/side-session Prep |
| `/scene new` | Starts a meaningful scene between encounters; refreshes Talents and special items |
| `/mission start` | Locks prepared choices and assigns waiting Prep to a main mission |
| `/mission end` | Expires that mission's unused Prep and opens downtime choices |
| `/gm rest` | Confirms ten safe minutes and restores Health and Energy |

Starting a session/scene/battle does not heal heroes or restore Energy. Rest does not refresh Plus Ultra, Talents, or special items. Battle creation counts as a new scene; another scene can begin after the battle finishes. A mission may span sessions and battles. Begin it after players choose their loadouts.

Training is +1 per marked participant per official session, with a cap of 2 per configured server week. The session's **start time** determines its week, even if it crosses midnight/reset time. Splitting one session into artificial starts should not create extra rewards. Failed practice still counts as participation. Winning, kills, repeated checks, and bot-command activity do not award Training automatically.

For a side session, use `/session start name:Rescue Practice side:true prep_theme:Evacuating people from smoke`. End normally. The Prep is for the next main mission, even when Training is already capped. Players choose between an existing Prep and a new offer with `/hero prep`; they never have two active Prep benefits. Ask them to decide before the next mission when possible. Prep earned during an ongoing mission waits for the following one.

Players request learned moves, Talents, or items with `/hero unlock`. Confirm with `/gm unlock user:@Player kind:move option:capture`; default `approve:true` costs 3 Training. Declining spends nothing. Learned choices remain available; `/hero prepare` sets the mission loadout. `/gm milestone reason:Completed the internship arc` grants everyone one shared die increase, including later and returning heroes. There are eight increases until all four dice reach d12.

## An entire first battle

This example uses two approved heroes, Mira and Ren. In string fields such as `participants` and `targets`, use their actual mentions or user IDs separated by commas. `user` options are Discord member pickers.

### Setup

```text
/battle create name:Station Rescue participants:@Mira,@Ren starting_zone:street
/gm zone name:lobby connect_to:street
/gm zone name:roof connect_to:lobby
/enemy add name:Bruiser template:elite zone:lobby trait:armor reach:touch
/enemy intent enemy:e1 intention:Move to street and strike a hero for 2 damage
/objective add key:exit name:Open the emergency exit goal:2 zone:lobby
/objective add key:evacuate name:Guide civilians outside goal:4 zone:lobby prerequisites:exit
/objective danger name:Smoke fills the station goal:3 consequence:The roof route becomes blocked
/battle start
/battle panel
```

The bot assigns enemy IDs (`e1`, `e2`, …) and uses your objective keys. Zone IDs use up to 32 letters, digits, underscores, or hyphens. New links can be marked blocked with `clear:false`; `/gm link` later opens them. A blocked link means it is not traversable yet, unless an approved Grapple Line crossing has the right anchor. The bot cannot recognize a sealed wall versus a usable gap: you establish that fictional permission.

The live panel updates after game commands. You can pin its message manually; the bot needs no Manage Messages permission. Very large battles have a shortened panel and a complete `/battle status` readout.

### Heroes act

Mira chooses first:

```text
/battle turn
/battle move zone:lobby
/battle task objective:exit stat:wits method:Release the emergency latch
/resolve
/battle end
```

A normal task gives 1 progress on 4–7 or 2 on 8+. A prepared Rescue Boost uses `boost:true`, costs 1 Energy, and gives 2/3 progress on a fitting task. The evacuation prerequisite stays locked until the exit is complete. If an agreed action is automatic, the player `/battle automatic`; you `/objective tick` for any justified progress. This keeps story rulings explicit.

Ren might move and attack:

```text
/battle turn
/battle move zone:lobby
/battle attack targets:e1 stat:power method:Drive the villain back move:heavy_hit
/resolve
/battle end
```

Every hero gets one free connected-zone move and one action. An action can happen before or after the normal move. A Rush uses the action for an additional connected-zone move. Rapid Move costs 1 Energy, replaces free movement, and comes before an ordinary action. At most one signature is allowed per turn, including movement. The bot spends costs before rolls; a miss does not refund them.

You determine whether a player may use an offered `edge:true`, whether a weakness imposes `pressure:true`, and which stat suits a method. The bot checks the numerical interactions, Talent category, prepared move, reach, Energy, and turn budget. It cannot understand natural language well enough to grant or reject fictional advantages automatically.

### Enemy phase and defenses

After everyone acts:

```text
/gm phase phase:enemies
/enemy attack enemy:e1 targets:@Mira description:The Bruiser follows through with a heavy punch
```

In this example the foe and Mira are already in the lobby. If a foe must move to pursue its declared target, use `/enemy move` first. Ordinary foes move one clear connection; Fast foes can move two in total per phase. You explain an intention adjustment when the original target becomes invalid. Defeated enemies have no remaining actions. Use `/enemy action ... description:Waits because the target escaped` to explicitly resolve a skipped action. NPC work on an objective respects its prerequisites and the enemy card’s reach; `/objective tick` remains your explicit override. Big Capture consumes the cancelled action even if its planned target is now unreachable or invalid.

Mira uses:

```text
/battle defend stat:speed method:Dive behind a station pillar bonus_zone:street
/resolve
```

A miss takes the announced damage; 4+ avoids it; 8+ avoids it and earns a connected-zone move. A preselected bonus move happens after the whole attack resolves. If its route is blocked before the last defense finishes, the player receives a new bonus choice instead of moving through it. If no destination was chosen, the player `/battle bonus zone:street` or `zone:stay`. All defenses and bonus choices finish before another action or a phase change. Hazards also pause hero turns until defenses finish.

For an absent player you may `/battle defend user:@Player` without spending their Talent or Prep, then accept with `/resolve`. Only that player can choose Plus Ultra. You may choose `/battle bonus user:@Player zone:stay` for them; their movement destination remains their choice. `/gm skip user:@Player reason:Absent` ends their hero turn without inventing optional costs.

When all surviving enemy actions are resolved:

```text
/gm phase phase:next
```

Danger advances once, the next round starts, and you announce intentions. When its track fills, the bot prints the consequence and stops further automatic ticks; you apply its story/map effects, such as blocking the roof route. `/objective stop-danger reason:The ventilation is repaired` stops an active cause.

Finish with:

```text
/battle finish outcome:The class secures the villain and evacuates the station
/mission end
/session mark user:@Mira
/session mark user:@Ren
/session end summary:The class rescued commuters and identified a villain contact
/gm rest
```

Only confirm rest when ten safe minutes actually pass. A Down hero can instead receive basic assistance between encounters with `/gm assist user:@Player`, returning at 1 Health.

## Interactions the bot calculates

- **Armor:** −1 from each unassisted hit, minimum zero. A helped hit ignores it; for Burst, only the named helped target ignores it. Remove exposed Armor with `/enemy trait trait:armor enabled:false` when the fiction warrants it.
- **Protector:** Pressure on attacks involving the foe. The description should explain how it protects itself/allies.
- **Help:** one fitting next roll gets Edge. An Attack also gains +1 damage and Armor bypass on one target, chosen before rolling. Help expires when the helper acts again or the scene changes.
- **Guard/Shield:** one protection reduction of 2, never stacked. A zone Shield takes priority so individual Guards remain available. Protection is spent even if a later defense succeeds. An attack already reduced to 0 before protection does not spend Guard or Shield. Zero remaining damage skips the roll and grants no bonus move.
- **Capture:** success prevents movement until the foe's next action ends and reduces its attack by 1. Big success cancels that action. A boss loses at most one action per round. Further Captures keep the stronger effect; unspent effects expire after the next enemy phase.
- **Wide attacks:** an ordinary Wide foe hits up to two heroes in one zone for default 1 damage each. A boss may target a larger group in one zone. Every target defends separately. If you supply `damage`, the bot uses that publicly announced value.
- **Healing:** Mend revives a Down hero at 1 or heals 2; Medical Patch heals 1 above zero. One healing action per recipient per fight, counting both together. Mend is 2 Energy; the item has its scene use limit.
- **Plus Ultra:** chosen after a tracked roll, sets result to 8 and charges 2 Health after the effect. It can leave the hero Down. Raw dice, automatic actions, and sparring do not offer it.

Player forms and the handbook explain the eight move templates, six Talents, five support items, and custom dice. Friendly sparring uses invitation/consent and higher-result contests, not cooperative damage or Plus Ultra.

## Corrections, exports, and backups

`/gm cancel-roll reason:Wrong target selected` restores campaign state from before a waiting roll, including spent game costs. `/gm undo reason:...` restores the latest saved change, up to 100 stored changes per server. Undoing a resolution can restore a pending roll; use `/pending` to see it. Public messages already posted are not erased by undo. Recent duplicate interaction deliveries use a saved receipt and do not charge again.

Use `/gm resource` for Health (0–6), Energy (0–3), Training, or a used flag (0/1). It posts your reason. `/objective tick`, `/enemy edit`, and `/gm position` correct other numerical state. A finished battle remains readable until another replaces it.

`/gm export` privately downloads JSON with character sheets, dice, session logs, and battle state. It omits private control tables and a pending roll's internal rollback snapshot. This is a portable reading/reference export, **not a restorable full database backup**.

For Railway, enable [volume backups](https://docs.railway.com/volumes/backups) where your plan supports them. To make a full consistent SQLite backup with access to the host filesystem, use:

```bash
python bot.pyz backup create --db /data/ua.sqlite3 --out /data/backups/ua-2026-10-07.sqlite3
```

The bundle includes this host-only utility. For local source use, `python backup.py create` is equivalent. This works while the bot runs, including WAL data. Use a new filename each time; existing files are not overwritten. A backup on the same volume does not protect against deleting that volume, so also keep a copy elsewhere. Full backups include private creator settings and must stay private.

For Railway restoration, use its volume-backup restore workflow. For a local/offline filesystem restoration, stop **every** bot process first, then:

```bash
python backup.py restore --backup backups/ua-2026-10-07.sqlite3 --db data/ua.sqlite3 --bot-stopped
```

The utility validates the backup before touching current data, preserves the previous database beside it when one exists, then restores. A valid previous database gets a complete SQLite snapshot; a corrupt one gets a `.corrupt` folder containing its original database and any WAL/SHM files. This allows recovery from corruption without losing the damaged files. `--bot-stopped` is your confirmation that you actually stopped it; it is not automatic process detection. Do not restore over an active bot. Start the bot again and check `/hero sheet`, `/pending`, and `/battle status`.
