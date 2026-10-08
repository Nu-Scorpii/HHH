# Creator controls — 2.0.0

Send these in a **one-to-one DM to the bot** from your `BOT_OWNER_ID` account. They work across every server the bot joins. No server ID or setup command is needed. Capitalization and extra surrounding spaces do not matter.

| Command | What happens |
|---|---|
| `!Rigger 15` | Set the next matching numeric result to 15 |
| `!Rigger force 15` | Same as the shortcut above |
| `!Rigger shift +3` | Add 3 to the next matching numeric result |
| `!Rigger shift -2` | Subtract 2 from the next matching numeric result |
| `!Rigger luck good` | Lasting better luck: roll twice, use the higher result |
| `!Rigger luck bad` | Lasting worse luck: roll twice, use the lower result |
| `!Rigger luck normal` | Turn lasting luck off; keep any next-roll override |
| `!Rigger status` | Show your luck, next override, and last changed result |
| `!Rigger off` | Reset all settings to normal |
| `!Rigger help` | Show this short command list |

There are **two settings**: one lasting luck setting and one next-roll override. A new force or shift **replaces** the previous override; nothing queues. Force/shift is spent on **one entire roll**, even when it contains several dice. Luck lasts until you change it or use `off`. Force takes priority over luck; shift applies after luck.

Leave the player out to affect whoever rolls next in any server. To target one person, put their **user ID or mention after the value**:

```text
!Rigger 8 123456789012345678
!Rigger shift -2 <@123456789012345678>
!Rigger luck bad 123456789012345678
```

That setting follows the same person across servers. Other players' rolls do not spend their targeted override. There is only one luck target and one override target at a time. To return to everyone, omit the target on the next setting. You can also use `me` or `any`.

For `/roll`, force means the **final total, including modifiers and bonus points**. For a tracked check, attack, defense, or spar, it means the **kept result**. Dice, totals, and keep-high/low arithmetic remain legal. Numbers outside the possible range are limited to that range. Sparse numeric custom dice may use a nearby legal total when an exact total is unavailable. Luck makes better/worse results more likely; it does not guarantee success or failure.

Text or mixed text dice and `/hero roll` starting-stat assignment are unaffected and do not spend the override. A result already shown in a waiting roll is not changed retroactively. Invalid commands or dice do not change settings. A failed game transaction restores the setting; duplicate Discord deliveries do not spend it twice.

## Updating from the older controls

Old queues, timers, scope/category options, counts, and rule IDs are disabled. The update starts the simple controls at **normal**, so old rules cannot unexpectedly fire. Your old control records remain in full backups, but are never executed. Existing heroes, battles, waiting buttons, sessions, and FAQs are retained. New luck and overrides persist across restarts.

Only the creator's DM can read or change these settings. GM roles, administrators, players, server channels, and group DMs cannot use them. Player help, FAQs, slash menus, and campaign exports do not include them. Public roll messages use the ordinary presentation without a control marker. People with source, database, or hosting access can inspect the implementation; these controls are private within Discord, not encrypted from source readers. Full database backups contain the settings and audit records. The Docker image excludes this guide, and the bot does not intentionally log DM contents.
