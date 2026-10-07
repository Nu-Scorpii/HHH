# Discord message style — version 1.2.0

Normal replies use plain Discord Markdown, matching the supplied reference: an emoji and bold heading, readable values, and a bold total. Discord supplies the avatar, bot name, timestamp, and slash-command attribution using your application's settings.

`/roll dice:1d20`, with an example result of 8:

🎲 **Rigel (Angel) rolled 1d20**

Rolls: `8`

**Total: 8**

`/roll dice:1d20 bonus:3`, with the same example die:

🎲 **Rigel (Angel) rolled 1d20**

Rolls: `8`  
Bonus: `+3`

**Total: 11**

`/roll dice:2d20+2 keep:high bonus:3`, with example dice of 8 and 14:

🎲 **Rigel (Angel) rolled 2d20+2**

Rolls: `8` · `14`  
Kept (highest): `14`  
Modifier: `+2`  
Bonus: `+3`

**Total: 19**

Character cards use bold sections for resources, stats, student details, Quirk, prepared moves, loadout, growth, and trackers. Battle messages put turns and waiting decisions first, then heroes, foes, objectives, and routes. FAQs give each question a bold heading. Help, confirmations, attachments, and private errors use the same heading style.

Long messages continue in additional replies with matching headings. Each reply stays within Discord's 2000-character limit, including a conservative Unicode budget. The live battle panel stays in one message, with urgent decisions first and `/battle status` for full details. Existing panel messages have their old embeds removed when refreshed.

The rolling player's server display name appears in raw roll headings. User-supplied names, labels, and notes are escaped, and mentions are disabled. Private sheets, FAQs, errors, and creator DMs keep their existing visibility.
