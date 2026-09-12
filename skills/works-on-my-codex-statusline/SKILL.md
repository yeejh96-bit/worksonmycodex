---
name: works-on-my-codex-statusline
description: Configure the Codex TUI footer to replace the thread name with five-hour and weekly usage limits. Use when a user asks WOMC to show usage limits, change the lower status line, or remove the session/thread name from that footer. Do not use for API billing or workspace spend-limit questions.
---

# WOMC status line

Set the Codex TUI footer to this supported item order:

```toml
status_line = ["model-with-reasoning", "current-dir", "five-hour-limit", "weekly-limit"]
```

This is a personal Codex UI preference stored in the user's Codex `config.toml`, not a project rule. Plugin installation cannot run a post-install script, so perform this configuration only when the user explicitly invokes this skill or otherwise asks for the change.

Resolve `scripts/configure_statusline.py` relative to this `SKILL.md`. Run it without `--apply` first. Report the target path and the exact status-line item change without printing the rest of the configuration, which may contain private MCP or environment settings.

Writing the user-level config changes every Codex project. If the current request did not explicitly authorize that scope, ask for approval immediately before rerunning with `--apply`. If it did, apply directly. The script preserves unrelated text and refuses ambiguous inline tables, duplicate sections or keys, and multiline `status_line` values.

After applying, validate with `codex --strict-config --version`. Tell the user to start a new Codex session; or, in an existing interactive TUI, use `/statusline` to reload or adjust the selection. Do not claim that the limits will appear when the account does not supply that rate-limit window; Codex omits unavailable items.
