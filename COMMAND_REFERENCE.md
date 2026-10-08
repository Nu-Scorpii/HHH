# Public slash-command reference

The bot provides 74 slash commands in 8 main menus. Start with /help; you only need a few commands for everyday play. Use them inside your game server. Discord presents arguments as selectable fields.

Commands described as GM require the creator or configured GM role. `/gm config` requires the creator. Errors and personal sheets/help are private where appropriate; battle actions and official changes are public.

The bot handles one waiting tracked roll per server. While it waits, use its Keep / Plus Ultra buttons, `/battle resolve`, `/faq`, sheet/status commands, or permitted GM recovery tools.

## /help

### /help

Learn the game and find the bot commands.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `topic` | Default: `quick` | `quick`, `create`, `quirks`, `rolls`, `battle`, `training`, `spar`, `moves`, `talents`, `items`, `handbook`, `gm`, `commands` | Topic |

Response is private by default.

## /faq

### /faq

Browse or search common questions and campaign answers.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `question` | Optional; empty | text | Search words or a FAQ ID, such as energy or plus-ultra |
| `category` | Default: `all` | `all`, `start`, `characters`, `rolls`, `combat`, `recovery`, `progression`, `sparring`, `bot`, `campaign` | Category |
| `share` | Default: `false` | true/false | Post the answer publicly instead of privately |

Response is private by default.

## /hero

### /hero heal

Use prepared Mend, in combat or outside it.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |

### /hero item

Use your prepared Smoke, Scanner, or Medical Patch.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Optional; empty | player | Choose a player |
| `question` | Optional; empty | text | Field Scanner question for the GM |

### /hero create

Create a student with a guided form.

No arguments.

Opens a guided form; submit that form to save.

Response is private by default.

### /hero roll

Roll and save all four starting stats in one command.

No arguments.

### /hero build

Choose two moves, a Talent, and a learned item.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `first` | Optional; empty | `heavy_hit`, `burst`, `rescue_boost`, `shield`, `capture`, `rapid_move`, `long_reach`, `mend` | First |
| `second` | Optional; empty | `heavy_hit`, `burst`, `rescue_boost`, `shield`, `capture`, `rapid_move`, `long_reach`, `mend` | Second |
| `talent` | Optional; empty | `heavy_hitter`, `quick_feet`, `sharp_thinker`, `strong_spirit`, `rescue_specialist`, `quirk_specialist` | Talent |
| `item` | Optional; empty | `none`, `grapple_line`, `smoke_capsule`, `rescue_harness`, `field_scanner`, `medical_patch` | Item |

Response is private by default.

### /hero help

Help an ally, during a battle or outside it.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |
| `method` | Default: `Agreed action.` | text | Your goal and how your hero attempts it |
| `task` | Optional; empty | `check`, `task`, `attack`, `defense`, `capture`, `rescue`, `investigation`, `escape`, `hide` | Task |
| `objective` | Optional; empty | text | Objective |

### /hero edit

Edit your student’s name, age, goal, and team connection.

No arguments.

Opens a guided form; submit that form to save.

Response is private by default.

### /hero stats

Assign d10, d8, d8, and d6 to your starting stats.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `power` | Required | `6`, `8`, `10`, `12` | Power |
| `speed` | Required | `6`, `8`, `10`, `12` | Speed |
| `wits` | Required | `6`, `8`, `10`, `12` | Wits |
| `heart` | Required | `6`, `8`, `10`, `12` | Heart |

Response is private by default.

### /hero quirk

Write your power, ordinary uses, reach, and limits.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Your Quirk name |
| `reach` | Default: `ranged` | `touch`, `ranged` | Reach |

Opens a guided form; submit that form to save.

Response is private by default.

### /hero submit

Send your finished character card for GM approval.

No arguments.

### /hero sheet

View your current character, stats, and resources.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Optional; empty | player | Choose a player |
| `share` | Default: `false` | true/false | Post the sheet publicly instead of privately |
| `details` | Default: `false` | true/false | Show the complete sheet instead of the short card |

Response is private by default.

### /hero upgrade

Spend a waiting shared stat increase.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `stat` | Required | `power`, `speed`, `wits`, `heart` | Stat agreed with the GM before rolling |

### /hero unlock

Request a new move, Talent, or item for 3 Training.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `kind` | Required | `move`, `talent`, `item` | Kind |
| `option` | Required | text | Option ID from /help topic:moves, talents, or items |

### /hero notes

Save a custom tracker, or leave its value blank to delete it.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Name |
| `value` | Optional; empty | text | Tracker value; leave blank to delete this tracker |

Response is private by default.

### /hero prep

Choose whether to replace held Prep with a new offer.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `replace` | Default: `false` | true/false | False keeps the existing Prep; true takes the new offer |

## /roll

### /roll

Roll any dice and optionally add bonus points.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `dice` | Default: `1d20` | text | Dice to roll: 1d20, 2d17+1d8-3, or 2d[custom] |
| `bonus` | Default: `0` | integer | Extra points added to the total; negative numbers subtract |
| `keep` | Default: `all` | `all`, `high`, `low` | Keep |
| `faces` | Optional; empty | text | Optional JSON faces for d[custom]: [0,1,1,5] or ["sun","rain"] |

## /check

### /check

Roll your tracked stat outside a battle.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `stat` | Required | `power`, `speed`, `wits`, `heart` | Stat agreed with the GM before rolling |
| `method` | Default: `Agreed action.` | text | Your goal and how your hero attempts it |
| `task` | Default: `check` | `check`, `rescue`, `investigation`, `escape`, `hide` | Task |
| `edge` | Default: `false` | true/false | GM-approved Edge; extra sources never stack |
| `pressure` | Default: `false` | true/false | GM-announced Pressure |
| `talent` | Default: `false` | true/false | Spend your qualifying Talent before rolling |
| `prep` | Default: `false` | true/false | Spend a fitting Prep for this main mission before rolling |
| `rescue` | Default: `false` | true/false | This directly saves or protects someone |

## /battle

### /battle resolve

Show a waiting roll, keep it, or choose Plus Ultra.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `choice` | Default: `show` | `show`, `keep`, `plus` | Choice |

### /battle status

Read current zones, turns, Health, enemies, and objectives.

No arguments.

### /battle end

End your turn, including any unused movement or action.

No arguments.

### /battle move

Move, Rush, or use Rapid Move on a permitted route.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `zone` | Required | text | Zone |
| `mode` | Default: `normal` | `normal`, `rush`, `rapid` | Mode |
| `method` | Default: `Move along a clear route.` | text | Method |
| `carry` | Optional; empty | text | One cooperative hero ID, or two with Rescue Harness |
| `harness` | Default: `false` | true/false | Harness |
| `grapple` | Default: `false` | true/false | Grapple |
| `risky` | Default: `false` | true/false | A risky crossing uses your action and a roll |
| `stat` | Default: `speed` | `power`, `speed`, `wits`, `heart` | Stat |
| `pressure` | Default: `false` | true/false | Pressure |
| `talent` | Default: `false` | true/false | Talent |
| `prep` | Default: `false` | true/false | Prep |

### /battle attack

Attack with a basic strike, your prepared move.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `targets` | Required | text | Enemy IDs: e1, or e1,e2,e3 for Burst |
| `stat` | Default: `power` | `power`, `speed`, `wits`, `heart` | Stat agreed with the GM before rolling |
| `method` | Default: `Agreed action.` | text | Your goal and how your hero attempts it |
| `move` | Default: `basic` | `basic`, `heavy_hit`, `burst`, `long_reach`, `capture` | Move |
| `edge` | Default: `false` | true/false | GM-approved Edge; extra sources never stack |
| `pressure` | Default: `false` | true/false | GM-announced Pressure |
| `talent` | Default: `false` | true/false | Spend your qualifying Talent before rolling |
| `prep` | Default: `false` | true/false | Spend a fitting Prep for this main mission before rolling |

### /battle task

Work on an objective or another risky task.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `stat` | Default: `wits` | `power`, `speed`, `wits`, `heart` | Stat agreed with the GM before rolling |
| `method` | Default: `Agreed action.` | text | Your goal and how your hero attempts it |
| `objective` | Optional; empty | text | Objective |
| `boost` | Default: `false` | true/false | Use prepared Rescue Boost for 1 Energy |
| `edge` | Default: `false` | true/false | GM-approved Edge; extra sources never stack |
| `pressure` | Default: `false` | true/false | GM-announced Pressure |
| `talent` | Default: `false` | true/false | Spend your qualifying Talent before rolling |
| `prep` | Default: `false` | true/false | Spend a fitting Prep for this main mission before rolling |
| `rescue` | Default: `false` | true/false | Rescue |
| `task_type` | Default: `task` | `task`, `rescue`, `investigation`, `escape`, `hide` | Task type |

### /battle automatic

Spend an ordinary action on an agreed task needing no roll.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `method` | Default: `Agreed action.` | text | Your goal and how your hero attempts it |

### /battle guard

Guard one person or use your prepared Shield.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Optional; empty | player | Choose a player |
| `kind` | Default: `guard` | `guard`, `shield` | Kind |
| `method` | Default: `Protect them from the announced attack.` | text | Method |

### /battle recover

Use your action to restore 1 Energy.

No arguments.

### /battle defend

Roll defense against the incoming attack.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `stat` | Default: `speed` | `power`, `speed`, `wits`, `heart` | Stat agreed with the GM before rolling |
| `method` | Default: `Agreed action.` | text | Your goal and how your hero attempts it |
| `user` | Optional; empty | player | Choose a player |
| `edge` | Default: `false` | true/false | GM-approved Edge; extra sources never stack |
| `pressure` | Default: `false` | true/false | GM-announced Pressure |
| `talent` | Default: `false` | true/false | Spend your qualifying Talent before rolling |
| `prep` | Default: `false` | true/false | Spend a fitting Prep for this main mission before rolling |
| `bonus_zone` | Optional; empty | text | Optional big defense destination, or stay |

### /battle bonus

Choose your earned big defense move, or stay.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `zone` | Default: `stay` | text | Zone |
| `user` | Optional; empty | player | Choose a player |

## /spar

### /spar start

Invite another student to a friendly best-of-three spar.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `opponent` | Required | player | Choose a player |

### /spar join

Accept your friendly spar invitation.

No arguments.

### /spar roll

Roll one spar exchange; ties reroll without new costs.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `stat` | Required | `power`, `speed`, `wits`, `heart` | Stat agreed with the GM before rolling |
| `method` | Default: `Agreed action.` | text | Your goal and how your hero attempts it |
| `enhanced` | Default: `false` | true/false | Spend 1 Energy for Edge through a fitting Quirk approach |
| `edge` | Default: `false` | true/false | GM-approved Edge; extra sources never stack |
| `pressure` | Default: `false` | true/false | GM-announced Pressure |
| `talent` | Default: `false` | true/false | Spend your qualifying Talent before rolling |
| `prep` | Default: `false` | true/false | Spend a fitting Prep for this main mission before rolling |

### /spar status

Read the current spar score.

No arguments.

### /spar cancel

Cancel your spar; previous costs remain spent.

No arguments.

## /gm

### /gm battle create

GM: create a battle or rescue challenge.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Name |
| `participants` | Required | text | Hero mentions or user IDs, separated by commas |
| `starting_zone` | Default: `start` | text | Starting zone |

### /gm battle start

GM: begin round 1 after announcing enemy intentions.

No arguments.

### /gm battle panel

GM: post a live battle panel that updates after commands.

No arguments.

### /gm battle finish

GM: finish a fight or challenge and record its outcome.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `outcome` | Required | text | Outcome |

### /gm enemy add

GM: create a Minion, Rival, Elite, or Boss.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Name |
| `template` | Required | `minion`, `rival`, `elite`, `boss` | Template |
| `zone` | Required | text | Zone |
| `trait` | Default: `none` | `none`, `armor`, `protector`, `wide`, `fast` | Trait |
| `reach` | Default: `touch` | `touch`, `ranged`, `scene` | Reach |

### /gm enemy edit

GM: set enemy Health, damage, or action count.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `enemy` | Required | text | Enemy |
| `health` | Optional; empty | integer | Health |
| `damage` | Optional; empty | integer | Damage |
| `actions` | Optional; empty | integer | Actions |
| `trait` | Optional; empty | `armor`, `protector`, `wide`, `fast` | Trait |
| `enabled` | Default: `true` | true/false | Enabled |

### /gm enemy intent

GM: announce the enemy’s reliable intention.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `enemy` | Required | text | Enemy |
| `intention` | Required | text | Intention |

### /gm enemy move

GM: resolve permitted enemy movement.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `enemy` | Required | text | Enemy |
| `zone` | Required | text | Zone |

### /gm enemy attack

GM: spend an enemy action and request player defenses.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `enemy` | Required | text | Enemy |
| `targets` | Required | text | Active hero IDs or mentions, separated by commas |
| `description` | Required | text | Announced attack and fictional effect |
| `damage` | Optional; empty | integer | Announced damage override; default uses the enemy card |

### /gm enemy action

GM: resolve or skip an enemy action, including objectives.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `enemy` | Required | text | Enemy |
| `description` | Required | text | Description |
| `objective` | Optional; empty | text | Objective |
| `amount` | Default: `1` | integer | Amount |

### /gm objective add

GM: create a public progress objective and its prerequisites.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `key` | Required | text | Key |
| `name` | Required | text | Name |
| `goal` | Default: `4` | integer | Goal |
| `zone` | Optional; empty | text | Zone |
| `prerequisites` | Optional; empty | text | Existing objective IDs, separated by commas |

### /gm objective tick

GM: correct or advance objective progress.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `key` | Required | text | Key |
| `amount` | Required | integer | Amount |
| `reason` | Required | text | Reason |

### /gm objective danger

GM: announce a Danger track and its consequence.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Optional; empty | text | Name |
| `consequence` | Optional; empty | text | Consequence |
| `goal` | Default: `3` | integer | Goal |
| `active` | Default: `true` | true/false | Active |

### /gm session start

GM: start one official main or side session.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Name |
| `side` | Default: `false` | true/false | Side |
| `prep_theme` | Optional; empty | text | Required theme for an official side session |
| `participants` | Optional; empty | text | Optional player mentions/IDs; mark these attendees immediately |

### /gm session mark

GM: mark or remove a player’s meaningful participation.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |
| `participated` | Default: `true` | true/false | Participated |

### /gm session end

GM: record the session and award capped Training and Prep.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `summary` | Required | text | Summary |

### /gm session log

Read the latest session records.

No arguments.

### /gm mission start

GM: lock prepared choices and assign held Prep to a main mission.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Name |

### /gm mission end

GM: finish a mission and expire its unused Prep.

No arguments.

### /gm scene

GM: begin a new meaningful scene and refresh Talents and items.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Name |

### /gm config

Creator: configure GM access, timezone, and weekly reset.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `gm_role_id` | Optional; empty | role | Role allowed to use GM commands |
| `timezone` | Default: `America/New_York` | text | Timezone |
| `reset_weekday` | Default: `0` | integer | 0=Monday through 6=Sunday |
| `reset_hour` | Default: `0` | integer | Local hour 0–23 |

Response is private by default.

### /gm approve

GM: approve a submitted hero or reopen their draft.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |
| `approve` | Default: `true` | true/false | Approve |

### /gm unlock

GM: approve or decline a requested Training unlock.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |
| `kind` | Required | `move`, `talent`, `item` | Kind |
| `option` | Required | text | Option |
| `approve` | Default: `true` | true/false | Approve |

### /gm resource

GM: correct a tracked resource with a public reason.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |
| `resource` | Required | `health`, `energy`, `training`, `plus_used`, `talent_used`, `item_used` | Resource |
| `value` | Required | integer | Value |
| `reason` | Required | text | Reason |

### /gm roster

GM: inspect the class roster.

No arguments.

Response is private by default.

### /gm milestone

GM: grant the whole roster one shared stat increase.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `reason` | Required | text | Reason |

### /gm rest

GM: confirm ten safe minutes and restore Health and Energy.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Optional; empty | player | Choose a player |

### /gm assist

GM: wake a Down hero at 1 Health between encounters.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |

### /gm zone add

GM: create a zone with clear or blocked connections.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `name` | Required | text | Name |
| `connect_to` | Optional; empty | text | Existing zone IDs separated by commas |
| `clear` | Default: `true` | true/false | Clear |

### /gm zone link

GM: open or block a connection between two zones.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `first` | Required | text | First |
| `second` | Required | text | Second |
| `clear` | Default: `true` | true/false | Clear |

### /gm zone position

GM: correct a hero or enemy position.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `target` | Required | text | Hero user ID or enemy ID |
| `zone` | Required | text | Zone |
| `reason` | Required | text | Reason |

### /gm battle phase

GM: begin the enemy phase or next round.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `phase` | Required | `enemies`, `next` | Phase |

### /gm battle skip

GM: end an absent hero’s turn without spending optional resources.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `user` | Required | player | Choose a player |
| `reason` | Required | text | Reason |

### /gm battle hazard

GM: resolve a damaging hazard using player defenses.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `targets` | Required | text | Targets |
| `damage` | Required | integer | Damage |
| `description` | Required | text | Description |

### /gm cancel-roll

GM: cancel an invalid staged roll and restore its costs.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `reason` | Required | text | Reason |

### /gm undo

GM: undo the latest saved game change.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `reason` | Required | text | Reason |

### /gm export

GM: download campaign sheets, sessions, and battle state.

No arguments.

Response is private by default.

### /gm faq-add

GM: add or update an answer for this server’s FAQ.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `key` | Required | text | New FAQ ID, such as session-times |
| `question` | Required | text | Player question, up to 150 characters |
| `answer` | Required | text | Your answer, up to 2000 characters |
| `category` | Default: `campaign` | `start`, `characters`, `rolls`, `combat`, `recovery`, `progression`, `sparring`, `bot`, `campaign` | Category |

Response is private by default.

### /gm faq-remove

GM: remove one of this server’s custom FAQ answers.

| Argument | Required/default | Type or choices | Meaning |
|---|---|---|---|
| `key` | Required | text | Campaign FAQ ID to remove |

Response is private by default.

## Values and limits

- Core stat dice are d6, d8, d10, and d12; starting assignment is d10, d8, d8, d6.
- /hero roll randomly assigns those four starting dice once. It saves the assignment before creation, applies it to a draft, and shows that same saved result on repeat. It does not roll random Health or Energy. /hero stats remains available for manual assignment.
- Hero Health is 0–6; Energy is 0–3. Zero Health means Down.
- Custom dice: 1–1,000,000,000 numbered sides; up to 100 dice and 20 expression terms per command.
- /roll defaults to 1d20. Its bonus field is a whole number within ±1 billion and is added once to the total, alongside any expression modifiers.
- Per-roll custom faces use JSON arrays of 1–1000 integers or text labels. Example: `/roll dice:1d[custom] faces:["sun","rain","rain","storm"]`. Repeated faces add weight. Integers may be negative, zero, or positive within ±1 billion; labels have 1–40 characters. Faces are not saved.
- Previously saved named dice remain usable with `/roll dice:1d[name]`. No dice-create/list/remove slash commands are registered.
- Keep-high/low requires one positive numeric dice pool; modifiers and bonus points are added after choosing the kept die. Dice containing any text faces cannot use keep-high/low, subtraction, numeric modifiers, or bonus points. Text results have no numeric total.
- /roll can be used before character creation or while a tracked roll waits. It does not spend resources or apply tracked game effects.
- /hero notes holds up to 20 names with values up to 120 characters. These are manual notes/counters. Leave the value blank to delete a note. The short sheet previews three notes; details:true shows all of them.
- A battle supports up to 20 participants, 25 zones, 25 enemies, and 20 progress objectives. IDs for zones/objectives use up to 32 letters, digits, underscores, or hyphens.
- Enemy Health corrections: 0–10000; damage: 0–20; action count: 1 or 2. Objective/Danger goals: 1–100.
- Weekly reset: weekday 0=Monday through 6=Sunday; local hour 0–23. Use a timezone name such as America/New_York.
- /hero build combines starting choices and prepared loadouts. Established heroes may select only learned and GM-approved options. Omitted fields keep their current choices. item:none removes a prepared item. Changing choices never refreshes spent uses.
- A hero’s first battle move or action starts the turn automatically. Another hero must end their turn before yours starts. /battle end can also pass an unused turn.
- Resource used flags accept 0 for available and 1 for spent. Training corrections accept 0–10000.
- /faq searches written answers, browses topics, or accepts an exact FAQ ID. Replies are private unless share:true is selected. It is available before character creation and while a roll waits.
- GMs can save up to 50 custom FAQs per server with /gm faq-add; using an existing custom ID updates it. Questions are 1–150 characters, answers 1–2000, and IDs are up to 32 characters. /gm faq-remove removes custom answers; core rule IDs are protected.

See the player handbook for the complete rules and the GM guide for setup and examples.
