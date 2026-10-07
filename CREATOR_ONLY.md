# Creator controls — private document

Keep this file and the complete source package for yourself. Players only need the player guides. The Docker image excludes this document; the private handler itself is part of the running bot.

## Access

The one exception to slash commands is **`!Rigger`**, with that exact capital R. Send it in a **direct message to the bot** from the Discord account whose personal user ID is set as `BOT_OWNER_ID`.

The bot does not respond to other users attempting this command. It does not respond to it in server channels. A GM role, server ownership, or Administrator permission does not grant this access. The handler checks your identity and DM context before parsing anything.

Start with:

```text
!Rigger help
!Rigger server YOUR_SERVER_ID
```

The selected server is saved across restarts. If the bot belongs to exactly one server, selection is optional. With several servers, select one before queueing or inspecting rules.

## Quick examples

```text
!Rigger next PLAYER_ID 8
```

The player's next compatible roll keeps an 8. Replace `PLAYER_ID` with the player's Discord user ID, a mention, or `me`. If their chosen die is a d6, 8 is impossible, so the rule stays queued for a compatible roll.

```text
!Rigger next PLAYER_ID miss 1 attack 30
!Rigger next PLAYER_ID max 2 defense 60
!Rigger next any big 3
!Rigger next PLAYER_ID 7 1 dice
!Rigger next PLAYER_ID "heavy rain" 1 dice
```

These respectively queue one missed attack within 30 minutes, two maximum defense results within an hour, three big results from any player, a raw dice roll with faces set to 7, and a custom text face. Text faces must exist on the relevant custom die.

The general form is:

```text
!Rigger next TARGET OUTCOME [COUNT] [SCOPE] [MINUTES]
```

Optional arguments are positional. To specify a scope, include a count; to specify minutes, include both count and scope. Defaults are **one use**, **any scope**, and **60 minutes**.

| Argument | Accepted values |
|---|---|
| Target | Player user ID, mention, `me`, or `any` |
| Outcome | Exact legal numeric/text face, `min`, `max`, `miss`, `success`, `big` |
| Count | 1–100 matching roll commands |
| Scope | `any`, `dice`, `check`, `attack`, `capture`, `task`, `defense`, `spar`, `power`, `speed`, `wits`, `heart` |
| Minutes | 1–1440; measured from queue creation |

`miss` chooses the lowest available face from 1–3. `success` chooses the lowest available face from 4–7. `big` chooses the lowest available face of 8 or higher. `max` chooses the actual highest face. These are deliberate outcomes rather than probability adjustments. On text dice, use an exact quoted face; generic outcome words work on dice containing only numeric faces.

`check` covers ordinary tracked checks outside battle. `task` covers battle objectives and risky movement. A stat scope applies to tracked rolls using that stat, including sparring. `dice` covers raw `/dice roll` commands.

## What gets changed

- A tracked stat roll changes its kept result. Edge/Pressure companion dice remain legal and consistent with that result. Edge and Pressure still cancel normally.
- A raw dice command sets **every die face in that command** to the requested compatible outcome. Modifiers stay unchanged. Thus forcing 7 on `2d17+1d8-3` produces `7+7+7-3=18`, not a total of 7. Use this distinction when queueing a rule.
- A rule is consumed once per matching roll command, not once per die in a pool.
- Impossible outcomes, unrelated scopes, expired rules, other players, and other servers do not consume a queued rule.
- Specific-player rules take priority over `any` rules; compatible rules otherwise run in queue order.
- A later Plus Ultra choice still sets a tracked result to 8. The override is applied when the initial roll happens, before that choice.

## Inspect and clear

```text
!Rigger status
!Rigger clear 12
!Rigger clear
!Rigger audit
```

Status lists up to 30 queued rules for the selected server. Clear with a number removes that rule; clear alone removes all queued rules for the selected server. Audit shows the last ten applied changes, including natural and final results, in your DM only.

The queue and audit are stored in separate private SQLite tables. They are excluded from player help, slash menus, public messages, and `/gm export`. Public results show ordinary dice output without an override marker. Full host database backups contain these private tables and should stay private. Anyone with source, database, or Railway deployment access can inspect the implementation.

Cancelling or undoing a game action does **not** put a consumed private rule back into the queue: a visible roll has already happened. Queue a new rule if needed. No credentials or DM message contents are intentionally written to application logs.
