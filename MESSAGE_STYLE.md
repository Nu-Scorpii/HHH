# Simple Discord messages — 2.0.0

The bot uses plain Discord messages: one short bold heading, the useful numbers, and the next step. Routine confirmations use **Done**; no repeated bot branding or internal operation names. Player sheets, help, FAQs, and errors retain their private defaults.

## Raw dice

For `/roll dice:1d20 bonus:3`:

🎲 **Rigel (Angel) · 1d20**

Rolls: `8`  
Bonus: `+3`  
**Total: 11**

Each die remains visible. Multiple pools show their pool labels, modifiers appear separately, and keep-high/low shows the kept die. Text faces have no invented numeric total.

## Starting stats

🎲 **Starting stats**

**Power:** `d10`  
**Speed:** `d8`  
**Wits:** `d8`  
**Heart:** `d6`  
Health: **6** · Energy: **3**

Saved for you. /hero create will use these stats automatically.

## Tracked rolls

🎲 **Frostline · attack**

`d10` · Edge · `3` · `8`  
**8 · Big success**

> Freeze the villain's escape route.

Keep this roll, or use Plus Ultra (−2 Health, once per session).

Buttons: **Keep** and **Plus Ultra · −2 HP**. Their persistent IDs stay compatible with saved waiting rolls. A default method is omitted when the player already described the action in chat.

## Character cards and battles

The default sheet shows Health, Energy, Plus Ultra, four stats, Quirk boundaries, prepared moves, Talent/item use, Training, Prep, and three note previews. Long descriptions are shortened. **`/hero sheet details:true`** shows every field and full move rules; `/hero submit` always uses that full card for GM review.

Battle boards show phase, active hero, action/movement availability, Health, enemies, objectives, and waiting decisions. Players start a turn with their first action or move and finish with `/battle end`. Large boards retain a full `/battle status` readout.

All text fits Discord's message limit through safe splitting. User names, custom faces, Quirk text, and notes are escaped; mentions are disabled. Existing embed panels switch to the new message style on their next refresh. Private controls never add a public badge, footer, or alternate style.
