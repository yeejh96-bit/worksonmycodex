---
name: works-on-my-codex-statusline
description: Configure the WOMC Codex TUI footer with model and reasoning, permission mode, weekly limit, remaining context, and project folder. Use when a user asks WOMC to show or repair that lower status line. Do not use for API billing or workspace spend-limit questions.
---

# WOMC status line

Set the Codex TUI footer to this supported item order:

```toml
status_line = ["model-with-reasoning", "weekly-limit", "context-remaining", "project-name"]
```

This produces the visible order `model + reasoning -> permission mode -> weekly remaining -> context remaining -> project name`. Codex inserts the permission mode, such as `Full Access`, automatically; it is not a selectable `tui.status_line` item. `weekly-limit` and `context-remaining` are percentages remaining. Do not relabel them as used.

This is a personal Codex UI preference stored in the user's Codex `config.toml`, not a project rule. A trusted WOMC `SessionStart` hook applies the default quietly once and records success in `PLUGIN_DATA`, so later user customization is not overwritten. Because Codex loads configuration before that hook, the first trusted run may need one more new session. If the hook is not trusted or the plugin host does not run hooks, perform this configuration only when the user explicitly invokes this skill or otherwise asks for the change.

Resolve `scripts/configure_statusline.py` relative to this `SKILL.md`. Run it without `--apply` first. Report the target path and the exact status-line item change without printing the rest of the configuration, which may contain private MCP or environment settings.

Writing the user-level config changes every Codex project. If the current request did not explicitly authorize that scope, ask for approval immediately before rerunning with `--apply`. If it did, apply directly. The script preserves unrelated text and refuses ambiguous inline tables, duplicate sections or keys, and multiline `status_line` values.

After applying, validate with `codex --strict-config --version`. Tell the user to start a new Codex session; or, in an existing interactive TUI, use `/statusline` to reload or adjust the selection. Do not claim that the weekly limit will appear when the account does not supply that rate-limit window; Codex omits unavailable items. On very narrow terminals Codex may elide trailing items, so prefer widening the terminal rather than changing the default order.
