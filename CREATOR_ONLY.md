# Creator controls — version 1.3.0

Send **`!Rigger`** with that exact capital R in a **one-to-one DM to the bot**, from the account configured as `BOT_OWNER_ID`. Start with `!Rigger help`. Other users, GM roles, administrators, server channels, and group DMs receive no reply or access.

**Every new setting applies across all servers the bot is in, including servers it joins later. No server ID or server-selection command is needed.** Campaign sheets and battles still belong to their own servers; only the creator controls are universal.

## The simple commands

| DM command | Effect | Default duration |
|---|---|---|
| `!Rigger luck good` | Make numeric rolls luckier | Until turned off |
| `!Rigger luck bad` | Make numeric rolls unluckier | Until turned off |
| `!Rigger luck normal` | Remove the default luck bias | Immediate |
| `!Rigger force 15` | Force the next compatible result to 15 | One roll within 60 minutes |
| `!Rigger force min` / `max` | Force the smallest/largest possible result | One roll within 60 minutes |
| `!Rigger shift +3` | Secretly raise the next result by 3 | One roll within 60 minutes |
| `!Rigger shift -2` | Secretly lower the next result by 2 | One roll within 60 minutes |
| `!Rigger shift miss` / `success` / `big` | Choose the next possible result category | One roll within 60 minutes |
| `!Rigger shift up` / `down` | Move one available category up/down | One roll within 60 minutes |
| `!Rigger status` | View active controls | Private reply |
| `!Rigger clear` | Remove all active controls | Immediate |
| `!Rigger clear 12` | Remove rule #12 from status | Immediate |
| `!Rigger audit` | View the latest ten applied changes | Private reply |

Luck changes probabilities without guaranteeing a number: `good` keeps the higher of two complete numeric roll candidates; `bad` keeps the lower. `luck +2` or `-2` uses three candidates; `+3` or `-3` uses four. The bot posts only the selected ordinary roll, preserving its dice count, faces, Edge/Pressure mode, and arithmetic. Text and mixed text/number dice do not consume luck settings.

## Pick a player, number of uses, or roll type

Add any optional arguments after the value, in any order:

```text
!Rigger force 8 <@PLAYER_ID>
!Rigger shift -2 PLAYER_ID uses:3 scope:attack
!Rigger luck bad PLAYER_ID scope:defense minutes:30
!Rigger force 15 uses:always scope:roll
!Rigger luck good uses:2
```

Replace `PLAYER_ID` with the player's personal Discord user ID, or use a real mention. Omit the target to affect anyone. `me`, `any`, `all`, and `*` also work. Targets follow the same person across servers; there is one shared use budget, rather than one budget per server.

| Optional argument | Accepted values |
|---|---|
| Player | Bare user ID/mention or `target:ID`; `player:ID` is an alias |
| `uses:` | 1–100 matching roll commands, or `always` / `forever`; `count:` is an alias |
| `scope:` | `any`, `dice`, `check`, `attack`, `capture`, `task`, `defense`, `spar`, `power`, `speed`, `wits`, `heart`; `roll` means `dice`, `all` means `any` |
| `minutes:` | 1–1440 minutes, measured from creation |

Finite-use rules default to a 60-minute expiry. Lasting rules have no expiry unless you add `minutes:`. Luck defaults to lasting; force and shift default to one use. Expired rules and incompatible rolls do not use up a count.

A specific player takes priority over everyone. For luck, a specific scope also takes priority over `any`. `!Rigger luck normal PLAYER_ID` creates a neutral player setting that masks the global bias; add `uses:1` for a temporary exception. `luck normal` without a player or scope removes only the default bias. Use `clear` to reset everything, including player/scoped settings.

Among compatible force/shift controls, specific-player rules win, finite rules run before lasting rules, then queue order applies. One exact force bypasses luck without consuming its budget. Otherwise luck happens first, then one compatible shift/category control. Avoid several overlapping lasting controls; `status` and `clear RULE_ID` let you manage them.

## Numbers, bonuses, and legal results

**Force means the kept stat result or the final numeric `/roll` total.** For example, `!Rigger force 15` followed by `/roll dice:2d20 bonus:3` gives legal d20 faces adding to 12 and a visible total of 15. It does not set both dice to 15. Expression modifiers and the visible bonus remain unchanged and are included in the target total.

**Shift applies once per roll command.** With natural faces 5 and 5 and a +3 bonus, `shift +2` changes the final total from 13 to 15. It does not add 2 to each die. Edge/Pressure companion faces remain possible and consistent with the kept result. Shifts clamp to the roll's possible range. Sparse custom dice can leave gaps, so the bot makes a best effort toward the requested shift using legal faces; the actual change can be smaller, larger, or zero.

The categories are **miss 1–3**, **success 4–7**, **big 8+**. On raw numeric dice they use the final total, including modifiers and bonus. `up`/`down` skips unavailable categories and stays at the current result when no higher/lower category is possible. A d6 cannot naturally become a big result. An impossible exact force or category remains queued for a compatible roll.

For text dice, use an existing quoted face:

```text
!Rigger force "heavy rain"
```

`force face:7` explicitly sets every compatible face to 7, preserving the old per-face behavior. Text faces must exist on all dice in the matching command. Generic numeric force, shifts, and luck require dice whose possible faces are entirely numeric.

The custom-total solver has a bounded search so large sparse pools cannot freeze the bot. An exact request may remain queued if the search budget is exhausted, even when a complicated combination exists. Numbered dice up to one billion sides are handled as intervals, without enumerating their faces. These limits never create nonexistent faces or inconsistent totals.

A later Plus Ultra choice still sets the tracked result to 8 and costs the usual Health. Rigging acts on the initial roll. Cancelling or undoing a game action does not restore a consumed rule after the visible roll; queue a new one if needed. Failed transactions and duplicate interaction retries do not spend a rule twice.

## Existing settings and older commands

The update automatically adds the new private mode field and changes your old server-specific queues to universal queues. Their IDs, remaining uses, expiry, audit history, and old per-face meaning are preserved. No manual database edit or server-ID setup is needed. Existing campaigns, sheets, battles, and pending rolls are retained.

The old syntax still works:

```text
!Rigger next TARGET FACE [COUNT] [SCOPE] [MINUTES]
```

Its defaults remain one use, any scope, and 60 minutes. It forces each raw die face before modifiers/bonus. For example, old `next any 7` on `2d17+1d8-3` gives 18. Prefer `force 15` when you want a final total. The old `server` command only explains that selection is no longer needed; it does not restrict new settings.

## Privacy and persistence

The bot sends confirmations and audits only in your DM. Public dice replies contain ordinary faces and totals with no control marker. Controls are absent from slash menus, player help, built-in FAQs, and `/gm export`. Status lists up to 30 active controls, with a limit of 100 active controls; audit shows the actual server and player for each applied change.

Queues and audit records persist in separate SQLite tables on the attached Railway volume. Full host backups contain them and preserve the new modes, lasting luck, and counts; older full backups migrate automatically at startup. Keep this guide and backups for yourself. Source, database, and Railway access expose the implementation; this is hidden in player-facing Discord output, rather than encrypted from host/source readers. The Docker image excludes this private guide, while its runtime includes the handler. Credentials and DM contents are not intentionally logged.
