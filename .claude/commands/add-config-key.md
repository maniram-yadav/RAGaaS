---
description: Add or change a configuration key the sanctioned way (never touches a real .env).
argument-hint: brief description of the setting to add/change
---

The user wants to add or change a configuration setting: `$ARGUMENTS`.

Invoke the `add-config-key` skill to do this. Do not hand-edit `config/system_config.example.json` or
`.env.example` outside of that skill's procedure, and do not, under any circumstance, open or edit a
real `.env` file as part of this — the skill and
[.claude/rules/config-management.md](../rules/config-management.md) explain why.
