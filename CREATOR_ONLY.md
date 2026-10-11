# Creator controls · 3.1.0

**DM the bot from your creator account.** Server messages are ignored. Your account must match `BOT_OWNER_ID`; server owners, administrators, and GM roles cannot bypass this check. No server ID is needed.

| Send this | What it does |
|---|---|
| `!Rigger 15` | Forces the **next final numeric total** to 15 |
| `!Rigger +3` | Adds exactly 3 to the next numeric total |
| `!Rigger -2` | Subtracts exactly 2 from the next numeric total |
| `!Rigger good` | Rolls twice and uses the better whole roll until turned off |
| `!Rigger bad` | Rolls twice and uses the worse whole roll until turned off |
| `!Rigger off` | Clears the active setting |
| `!Rigger status` | Shows the setting and last affected roll privately |
| `!Rigger help` | Shows this short help in your DMs |

**There is only one setting.** A new setting replaces the previous setting, including its target. Nothing stacks. Force and shift apply once; luck stays on until replaced or turned off. With no target, the setting applies to anyone in any server the bot joins. Invalid `/roll` input cannot consume it.

To target a player, add their mention or copied user ID to a setting:

```text
!Rigger 15 123456789012345678
!Rigger +3 @Player
!Rigger good 123456789012345678
```

In DMs, copying the player's user ID is usually easiest. The target is a **person**, not a server. Other players' rolls stay normal and do not consume the setting. To target yourself, add your own user ID.

Force means the total **after** modifiers and bonus points. For example, `!Rigger 15` followed by `/roll dice:1d20 bonus:3` displays a die of 12 and a total of 15. A multi-die roll is adjusted using valid faces whose total matches; it does not set every die to 15. Keep-high/low follows the same rule. Good/bad compares the final total of two complete ordinary rolls, including subtraction and keep-high/low. Numeric custom dice retain their declared faces; repeated faces preserve their weight during ordinary and luck draws.

If an exact force or shift is impossible, the bot returns the ordinary roll, clears the one-use setting, and sends you a private explanation. It never invents an unavailable face or silently picks a nearby total. Example: `[0,5]` cannot produce a total of 3 on one die. A huge custom-face combination can also hit a bounded search limit; the bot fails safely in the same way. Text-containing dice have no numeric total. Good/bad simply skips them and stays enabled.

Two less-common cases:

```text
!Rigger force -4
!Rigger face "Heavy Rain"
```

Use `force` for a negative forced total; a bare `-4` means a shift. `face` forces an exact text label on the next single custom die, with no arithmetic or bonus. It preserves case and spaces, so the label must match a listed face. String labels such as `"7"` are text faces; numeric custom faces use normal total forcing. An incompatible next roll clears that one-use setting and privately explains why it could not apply.

The prefix is case-insensitive. For familiar older syntax, `!Rigger force 15`, `!Rigger shift +3`, and `!Rigger luck good` also work. There are no queues, roll counts, server selectors, or separate lasting/next settings.

Settings survive Railway restarts and version-3 upgrades. Existing 3.0 settings keep working unchanged; pre-version-3 flags are not loaded. Only the current creator's settings are active. Recent duplicate DM/roll deliveries do not rearm or consume them twice. If Discord blocks a private notice, its explanation remains in `!Rigger status`.

## Avatar controls

Put a part before the same simple setting. It applies only to that part of `/avatar`; `/roll` ignores it. You still have **one setting**, and a new one replaces it. Add a user ID at the end as usual to target one player across every server.

```text
!Rigger nation 30
!Rigger bending 100
!Rigger iq +3
!Rigger stats good
!Rigger family 100 123456789012345678
```

| Part | What is controlled | Force range / useful numbers |
|---|---|---|
| `iq` | IQ 1d20 | 1–20 |
| `stats` | The **total** of all six d20s | 6–120; 120 gives six 20s |
| `nation` | Nation 1d100 | 1–25 Fire, 26–50 Water, 51–75 Earth, 76–100 Nomad |
| `tribe` | Water origin 1d3 | 1 Southern, 2 Northern, 3 Swamp |
| `family` | Fire family 1d100 | 1–49 Civilian, 50–79 Military, 80–94 High ranking, 95–100 Royal |
| `control` | Earth village control 1d20 | 1–15 Yes, 16–20 No |
| `bending` | Bending check 1d100 | 1–59 Non-bender, 60–100 Bender |
| `element` | Nomad bender element 1d3 | 1 Fire, 2 Water, 3 Earth |
| `combat` | Non-bender combat 1d100 | 1–20 Sword, 21–40 Bow, 41–60 Fan, 61–80 Fists, 81–100 Pressure point |

`!Rigger avatar nation 30` is an optional longer spelling of `!Rigger nation 30`. Part names ignore case. Force values outside the listed range are rejected immediately without changing your active setting. Shifts may fail if the final value would leave the die's range; the result stays normal and only you receive the explanation.

The changed value determines all later decisions. Forcing a nation into Water Tribes triggers its tribe roll; forcing bending to 100 skips the non-bender combat roll. A non-Nomad bender's element follows their nation automatically; `element` cannot turn them into another element or create an Air bender.

If a one-use conditional part is skipped, it **clears after the targeted character** and tells you privately. For example, `!Rigger tribe 3` followed by a Fire Nation character does not roll an extra d3 or remain armed for a later character. Other players do not consume a targeted setting. A lasting `good`/`bad` part setting stays enabled when its part is skipped.

Luck means higher/lower **numeric roll**, not a judgment about which origin is better. `!Rigger nation good` favors higher nation numbers. `!Rigger stats good` rolls two complete six-die pools and keeps the pool with the higher sum; it does not choose each die independently.

Bare settings also work on `/avatar`: one-use force/shift affects **IQ first**, then clears; bare lasting good/bad applies to every rolled part. Use a named part when you want to change a later decision. Public messages show the final rolls and categories with no private setting or audit details.

Public roll replies contain only the dice result. The prefix is not registered as a slash command and there is no player-facing admin help. Anyone who can read the bot source can inspect its implementation; this is private operation inside Discord, not source-code secrecy. Keep this guide for yourself.
